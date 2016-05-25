#coding=utf8
"""
Standard attribute in response:
    sys_timestamp:  unix_timestamp [int]
    sys_elapse:     [int]
    sys_error:      [string]
    sys_status:     same with http status code, [int]
"""

__author__ = 'Vincent@Home'

import os
import re
import sys
import time
import decimal
import datetime
import types
import random
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from dateutil import parser
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPNotFound
import simplejson as json

try:
    import cx_Oracle
except ImportError:
    pass
try:
    import pyodbc
except ImportError:
    pass

from tap.service.common import conn_get
from tap.service.common import stmt_split
from tap.service.common import measure
from tap.service.common import dict2api
from tap.service.common import CadaEncoder
from tap.service.common import cu
from tap.service.common import dbconn_ratio_parse
from tap.service.interpreter import ParaHandler, CFNInterpreter
from tap.service.cache import cache_fn, cache_fn1
from tap.service.auth import valid_key
from tap.service.exceptions import *
from tap.service.rpcstats import get_client
from tap.models import (
    DBSession,
    TapProject,
    TapApi,
    TapApiRelease,
)


SOURCES_CONTAINER = {}


@view_config(route_name='api_run')
@view_config(route_name='api_run_v')
def main(request):
    """
    :param request:
    :return:
    """
    project_name = request.matchdict['project_name']
    api_name = request.matchdict['api_name']
    version = request.matchdict.get('version')

    version, config = load_config(project_name, api_name, version)
    config = dict2api(config)

    # run program
    try:
        result = Program(config, version).run(dict(request.params))
    except ApiAuthFail:
        result = dict(sys_status=403, sys_error="Auth Fail")
    jresult = json.dumps(result, cls=CadaEncoder)
    if 'jsonpCallback' in request.params:
        jsonp = request.params['jsonpCallback']
        jresult = jsonp + '(%s)' % jresult
    response = Response(jresult,
                        headerlist=[('Access-Control-Allow-origin', '*',)])
    response.content_type = "application/json"
    response.status = result['sys_status']
    return response


@cache_fn1(int(os.environ.get('TAP_API_RELOAD', 1800)))
def load_config(project_name, api_name, version):
    if version:
        version = int(version)
        release = DBSession.query(TapApiRelease).filter_by(
            project_name=project_name,
            api_name=api_name, version=version
        ).first()
    else:
        project = DBSession.query(TapProject).filter_by(
            name=project_name).first()
        if not project:
            raise HTTPNotFound
        api = DBSession.query(TapApi).filter_by(project_id=project.id,
                                                name=api_name).first()
        if not api:
            raise HTTPNotFound
        release = DBSession.query(TapApiRelease)\
            .filter_by(api_id=api.id)\
            .order_by(TapApiRelease.version.desc())\
            .limit(1).first()
    if not release:
        raise HTTPNotFound
    config = json.loads(release.content)
    return release.version, config


def val_universal(val, dbtype):
    if isinstance(val, str):
        return cu(val)
    elif not val:
        return val
    elif isinstance(val, (long, decimal.Decimal, float, datetime.date,
                          unicode)):
        return val

    if dbtype == 'ORACLE':
        if isinstance(val, cx_Oracle.LOB):
            val = val.read()
            return cu(val)
    return val


class Program(object):
    def __init__(self, config, ver_num):
        """
        :param config: api config
        :param ver_num: api version number
        :return:
        """
        self.config = config
        self.ver_num = ver_num

        self._cursor = None
        self._dbtype = None
        self._cursors = {}
        self._cursor_secondary = None
        self._conn = None

        self.rpc_client = None

        # 临时变量
        self._dbconn_ratio_result = None
        self._dbchoose = [None]

    def cursor_secondary(self, db_cfg):
        """
        load balance from secondary database
        :param db_cfg:
        :return: dbconn config instance
        """
        if not self.config.dbconn_ratio:
            return db_cfg
        if not self._dbconn_ratio_result:
            self._dbconn_ratio_result = \
                dbconn_ratio_parse(self.config.dbconn_ratio)
            for db_choice in self._dbconn_ratio_result.values():
                start = 0
                for db, ratio in db_choice.items():
                    db_choice[db] = [start + 1, start + ratio]
                    start = start + ratio

        # 生成 1 - 100 的随机数
        choice = random.randint(1, 100)
        db_choice = self._dbconn_ratio_result[db_cfg.name]
        db_choose = None
        for db, ratio in db_choice.items():
            if ratio[0] <= choice <= ratio[1]:
                db_choose = db
                break

        for conn in self.config.dbconn:
            if conn.name == db_choose:
                return conn

        for conn in self.config.dbconn_secondary:
            if conn.name == db_choose:
                return conn

        raise Exception("can't choose secondary database.")

    def cursor(self):
        if not self._cursor:
            # 无数据库配置，返回None
            if not self.config.dbconn:
                return self._cursor
            cfg = self.config
            conn_cfg = self.cursor_secondary(cfg.dbconn[0])
            self._dbchoose[0] = conn_cfg.name
            self._conn = conn_get(conn_cfg.dbtype,
                                  conn_cfg.connstring,
                                  conn_cfg.options)
            self._cursor = self._conn.cursor()
            self._dbtype = conn_cfg.dbtype
        return self._cursor

    def cursor_list(self):
        """

        :return: 实际返回 name: cursor 的dictionary
        """
        if not self.config.dbconn or len(self.config.dbconn) <= 1:
            return self._cursors
        if not self._cursors:
            self._cursors[self.config.dbconn[0].name] = \
                (self._dbtype, self.cursor())
            for _conn in self.config.dbconn[1:]:
                name = _conn.name
                _conn = self.cursor_secondary(_conn)
                cursor = conn_get(
                    _conn.dbtype,
                    _conn.connstring,
                    _conn.options
                ).cursor()
                self._dbchoose.append(_conn.name)
                self._cursors[name] = (_conn.dbtype, cursor)
        return self._cursors

    def cursor_by_name(self, db_name):
        if db_name is None:
            return self._dbtype, self.cursor()
        return self.cursor_list()[db_name]

    def _has_write(self, statement):
        statement = statement.strip().lower()
        if (statement.startswith('update') or statement.startswith('insert')
                or statement.startswith('create')
                or statement.startswith('delete')):
            return True
        return False

    def _source_prepare_repl(self, source, paras):
        """
        handling replace variable binding, @@name
        :param source:
        :param paras:
        :return:
        """
        for name, value in paras.items():
            reg_name = ur'([^\w])@@%s\b' % name
            source = re.sub(reg_name, u' %s ' % unicode(value), source)
        return source

    def _source_prepare(self, source, paras, dbtype):
        """
        处理代码中: 值绑定，参数绑定
        :param source:
        :param paras:
        :param dbtype:
        :return:
        """
        if dbtype == 'MSSQL':
            return self._source_prepare_pyodbc(source, paras, dbtype)

        # reg_name = ur'([^\w])@([\w+])\b'
        # if dbtype in ('MYSQL', 'PGSQL'):
        #     source = re.sub(reg_name, ur'\1%(\2)s', source)
        # elif dbtype == 'ORACLE':
        #     source = re.sub(reg_name, ur'\1:\2', source)
        # # TODO 怎么处理paras
        # return source, paras

        use_paras = []
        for name in paras.keys():
            reg_name = ur'([^\w])@%s\b' % name
            _source = source
            if dbtype in ('MYSQL', 'PGSQL'):
                source = re.sub(reg_name, ur'\1%%(%s)s' % name, source)
            elif dbtype == 'ORACLE':
                source = re.sub(reg_name, ur'\1:%s' % name, source)
            # check is source changed
            if _source != source:
                use_paras.append(name)
        paras = dict((k.encode('utf8'), paras[k]) for k in use_paras)
        return source, paras

    def _source_prepare_pyodbc(self, source, paras, dbtype):
        # pyodbc 不能执行 name binding
        para_position = {}
        positions = []
        for name in paras.keys():
            # 找出参数名在代码中出现的所有位置
            matches = re.finditer(
                ur'@%s\b' % name,
                source)
            index = [m.start() for m in matches]
            positions.extend(index)
            for idx in index:
                para_position[idx] = name

        for name in paras.keys():
            reg_name = ur'([^\w])@%s\b' % name
            source = re.sub(reg_name, ur'\1?', source)

        positions.sort()
        paras = [paras[para_position[i]] for i in positions]
        return source, tuple(paras)

    def run(self, paras):
        stats = dict(api_id=str(self.config.id),
                     project_id=str(self.config.project_id),
                     client_id='')
        with measure() as time_used:
            try:
                if self.config.auth_type == 'AUTH':
                    access_allow, client_id = valid_key(
                        paras.get('access_key'), self.config)
                    stats['client_id'] = str(client_id or '')
                    if not access_allow:
                        raise ApiAuthFail

                func = self.run_stmts
                if self.config.source.source_type == 'PYTHON':
                    func = self.run_python
                paras = ParaHandler.prepare(paras, self.config.paras)
                result = cache_fn(self.config, self.ver_num, func, paras)
                result['sys_status'] = 200
            except BaseException as e:
                import traceback
                trace = traceback.format_exc()
                self.report_stats_exc(stats, str(e), trace)
                result = dict(
                    sys_elapse=[],
                    table=[],
                    sys_error=cu('[%s]: %s' % (type(e).__name__, str(e))),
                    sys_status=500
                )
                if e.__class__ == ApiAuthFail:
                    result['sys_status'] = 403
            try:
                self.cursor().execute("commit")
            except:
                pass

        time_used = time_used()
        stats['elapse'] = str(time_used)
        self.report_stats(stats)

        if isinstance(result, dict):
            elapse = result['sys_elapse']
            elapse.append(['TOTAL', time_used])
            result['sys_timestamp_current'] = time.time()

        # 测试 dbconn choice 用
        # result['sys_dbchoose'] = self._dbchoose
        return result

    def run_python(self, paras):
        """
        Run python scripts
        :param paras:
        :return: dict
        """
        elapse = []
        result = OrderedDict(
            sys_elapse=elapse
        )
        container = {}
        with measure() as time_total:
            variables = {}
            for k, v in paras.items():
                if k in ('main', '__builtins__'):
                    continue
                variables[k] = v
            source = self.config.source.source.encode('utf8')
            source = source.replace('\r', '')
            source = ('#coding=utf8\r\n%s' % source)
            hash_source = hash(source)

            if hash_source in SOURCES_CONTAINER:
                container = SOURCES_CONTAINER[hash_source]
            else:
                exec source in container
                SOURCES_CONTAINER[hash_source] = container

            container.update(variables)

            # 赋予 数据库连接
            container['g_cursor'] = self.cursor()
            cursors = self.cursor_list()
            # g_cursor_{dbname}
            for name, _cursor in cursors.items():
                container['g_cursor_%s' % str(name)] = _cursor

            container['g_result'] = result
        elapse.append(['COMPILE', time_total()])

        with measure() as time_total:
            data = container['main']()
            if data:
                result['table'] = [[val_universal(v, None) for v in row]
                                   for row in data]
            else:
                result['table'] = []
        elapse.append(['EXECUTION', time_total()])

        result['sys_timestamp_exec'] = time.time()

        return result

    def run_stmts(self, paras):
        """
        Run SQL statements
        :param paras:
        :return:
        """
        elapse = []  # num, elapse
        db_result = None

        result = OrderedDict()
        with measure() as time_total:
            cursor = self.cursor()

            # prepare
            source = self.config.source.source
            charset, source = self.source_charset(source)
            if len(self.config.dbconn) == 0:
                raise Exception("请先设置数据库")
            writable = self.config.writable

            # if dbtype == 'MSSQL':
            #     stmts = [source.strip()]
            # else:
            #     stmts = stmt_split(source)
            # source = self._source_prepare_repl(source, paras)
            stmts = stmt_split(source)

            _last_cursor = None
            for i in range(len(stmts)):
                stmt = stmts[i]
                with measure() as time_used:
                    _last_cursor = self.run_stmt(stmt, paras, writable,
                                               charset, result, elapse)[2]
                elapse.append(['ST.%s' % i, time_used()])

            if _last_cursor:
                # 使用最后一个 cursor 获取最终数据
                db_result = self.bind_result(_last_cursor, 'table', self._dbchoose,
                                             elapse)
        elapse.append(['EXECUTION', time_total()])

        result['table'] = db_result
        result['sys_elapse'] = elapse
        result['sys_timestamp_exec'] = time.time()

        return result

    def bind_result(self, cursor, name, dbtype, elapse):
        result = []
        if cursor.description:
            with measure() as time_cu:
                rows = cursor.fetchall()
                if rows:
                    rows = [[val_universal(v, dbtype) for v in row]
                            for row in rows]
            elapse.append(['UNIVERSAL_CHR-%s' % name, time_cu()])
            cols = [col[0] for col in cursor.description]
            result.append(cols)
            result.extend(rows)
        return result

    def run_stmt(self, stmt, paras, writable, charset, result, elapse):
        stmt = stmt.strip(u';')

        code_info = CFNInterpreter.parse_one(stmt)

        if self.run_stmt_case(code_info, paras) is not True:
            return stmt, paras, None

        # writable check
        if not writable and self._has_write(stmt):
            raise TapNotAllowWrite

        # db 选择
        dbtype, cursor = self.cursor_by_name(code_info.db_name)

        # 处理百分号问题
        if dbtype in ('MYSQL', 'PGSQL'):
            stmt = code_info.script.replace(u'%', u'%%')
        else:
            stmt = code_info.script

        stmt = self._source_prepare_repl(stmt, paras)
        stmt, para = self._source_prepare(stmt, paras, dbtype)

        if charset:
            stmt = stmt.encode(charset)

        if para:
            cursor.execute(stmt, para)
        else:
            cursor.execute(stmt)

        # export variables
        self.run_stmt_export(code_info, paras, cursor)

        # bind result
        if code_info.bind:
            assert code_info.bind != 'table', "Don't bind data to `table`"
            data = self.bind_result(cursor, code_info.bind, dbtype, elapse)
            result[code_info.bind] = data

        return stmt, paras, cursor

    def run_stmt_case(self, code_info, paras):
        """
        cfn_case 检查, 仅接受值检查
        :return:
        """
        if not code_info.case_statement:
            return True

        case_statement = code_info.case_statement
        for para_name in paras.keys():
            case_statement = re.sub(ur'\b%s\b' % para_name, "paras['%s']" %
                                    para_name, case_statement)
        result = eval(case_statement)
        print case_statement, result
        return result

    def run_stmt_export(self, code_info, paras, cursor):
        """
        cfn_export, 导出变量
        :param code_info:
        :param paras:
        :return:
        """
        if not code_info.export:
            return

        if not cursor.description:
            script = code_info.script
            script = (script.encode('utf8') if isinstance(script, unicode)
                      else script)
            raise Exception("cfn_export failed: %s" % script)
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
        if not row:
            script = code_info.script
            script = (script.encode('utf8') if isinstance(script, unicode)
                      else script)
            raise Exception("cfn_export failed: %s" % script)
        row = dict(zip(cols, row))
        for name in code_info.export:
            if name not in row:
                raise Exception("cfn_export failed: not found field %s" % name)
            paras[name] = row[name]

    def report_stats_exc(self, stats, exc_message, exc_trace):
        exc_type, exc_value, tb = sys.exc_info()
        context = None
        if tb is not None:
            prev = tb
            curr = tb.tb_next
            while curr is not None:
                prev = curr
                curr = curr.tb_next
            context = prev.tb_frame.f_locals
            context['paras'] = tb.tb_frame.f_locals['paras']
            for k, v in context.items():
                if not isinstance(v, (str, unicode, long, decimal.Decimal,
                                      datetime.date, types.NoneType)):
                    v = repr(v)
                    if len(v) > 3000:
                        v = v[:3000]
                    context[k] = v
        context = json.dumps(context, cls=CadaEncoder)
        stats['exc_type'] = str(exc_type)
        stats['exc_message'] = exc_message
        stats['exc_trace'] = exc_trace
        stats['exc_context'] = str(context)

    def report_stats(self, stats):
        try:
            # 防止 oneway 模式 silient down, 约有 10% 的几率发起一个 ping 命令
            if not self.rpc_client:
                self.rpc_client = get_client()
            if random.random() > 0.1:
                self.rpc_client.ping()
            self.rpc_client.report(stats)
        except:
            import traceback
            traceback.print_exc()

    def source_charset(self, source):
        charset = re.findall(ur'\#\!charset\=(\w+)', source)
        if len(charset) == 1:
            charset = charset[0]
            return charset, re.sub(ur'\#\!charset\=(\w+)', '', source)
        return None, source
