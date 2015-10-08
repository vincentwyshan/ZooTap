#coding=utf8
"""
Standard attribute in response:
    sys_timestamp:  unix_timestamp [int]
    sys_elapse:     [int]
    sys_error:      [string]
    sys_status: http status code, [int]
"""

__author__ = 'Vincent@Home'

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


@cache_fn1(180)
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
        self._cursors = []
        self._cursor_secondary = None
        self._conn = None

        self.rpc_client = None

        # 临时变量
        self._dbconn_ratio_result = None

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
        for db, ratio in db_choice:
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
            self._conn = conn_get(conn_cfg.dbtype,
                                  conn_cfg.connstring,
                                  conn_cfg.options)
            self._cursor = self._conn.cursor()
        return self._cursor

    def cursor_list(self):
        if not self.config.dbconn or len(self.config.dbconn) <= 1:
            return self._cursors
        if not self._cursors:
            self._cursors = [self.cursor()]
            for _conn in self.config.dbconn[1:]:
                _conn = self.cursor_secondary(_conn)
                self._cursors.append(conn_get(
                    _conn.dbtype,
                    _conn.connstring,
                    _conn.options
                ))

    def _has_write(self, statement):
        statement = statement.strip().lower()
        if (statement.startswith('update') or statement.startswith('insert')
                or statement.startswith('create')
                or statement.startswith('delete')):
            return True
        return False

    def _para_prepare(self, paras, config_paras):
        result = {}
        for para in config_paras:
            if para.absent_type == 'NECESSARY' and para.name not in paras:
                raise TapParameterMissing(para.name.encode('utf8'))
            if para.name not in paras:
                result[para.name] = self._para_value(para.val_type,
                                                     para.default)
            else:
                result[para.name] = self._para_value(para.val_type,
                                                     paras[para.name])
        return result

    def _para_value(self, type_name, value):
        if value == 'NULL':
            return None
        elif value == 'NOW' and type_name == 'DATE':
            return datetime.datetime.now()

        if type_name == 'TEXT':
            return value
        elif type_name == 'INT':
            return int(value)
        elif type_name == 'DECIMAL':
            return decimal.Decimal(value)
        elif type_name == 'DATE':
            return parser.parse(value)
        return value

    def _source_prepare(self, source, paras, dbtype):
        if dbtype == 'MSSQL':
            return self._source_prepare_pyodbc(source, paras, dbtype)
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
        para_position = {}
        positions = []
        for name in paras.keys():
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
        client_id = ''
        stats = dict(api_id=str(self.config.id),
                     project_id=str(self.config.project_id),
                     client_id=client_id)
        with measure() as time_used:
            try:
                if self.config.auth_type == 'AUTH':
                    access_allow, client_id = valid_key(paras.get('access_key'))
                    stats['client_id'] = str(client_id or '')
                    if not access_allow:
                        raise ApiAuthFail

                func = self.run_stmts
                if self.config.source.source_type == 'PYTHON':
                    func = self.run_python
                paras = self._para_prepare(paras, self.config.paras)
                result = cache_fn(self.config, self.ver_num, func, paras)
                result['sys_status'] = 200
            except BaseException, e:
                import traceback
                trace = traceback.format_exc()
                self._report_stats_exc(stats, str(e), trace)
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

            exec source in container
            container.update(variables)
            container['g_cursor'] = self.cursor()
            cursor_list = self.cursor_list()
            for i in range(len(cursor_list)):
                container['g_cursor%s' % i] = cursor_list[i]

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
        db_result = []
        with measure() as time_total:
            cursor = self.cursor()

            # prepare
            source = self.config.source.source
            charset, source = self.source_charset(source)
            dbtype = self.config.dbconn[0].dbtype
            writable = self.config.writable

            if dbtype == 'MSSQL':
                stmts = [source.strip()]
            else:
                stmts = stmt_split(source)

            for i in range(len(stmts)):
                stmt = stmts[i]
                with measure() as time_used:
                    self.run_stmt(cursor, stmt, paras, dbtype, writable, charset)
                elapse.append(['ST.%s' % i, time_used()])

            if cursor.description:
                with measure() as time_cu:
                    rows = [[val_universal(v, dbtype) for v in row]
                            for row in cursor.fetchall()]
                elapse.append(['UNIVERSAL_CHR', time_cu()])
                cols = [col[0] for col in cursor.description]
                db_result.append(cols)
                db_result.extend(rows)
        elapse.append(['EXECUTION', time_total()])

        result = OrderedDict(
            table=db_result,
            sys_elapse=elapse,
            sys_timestamp_exec=time.time()
        )

        return result

    def run_stmt(self, cursor, stmt, paras, dbtype, writable, charset):
        stmt = stmt.strip(u';')

        if dbtype == 'MYSQL':
            stmt = stmt.replace(u'%', u'%%')

        stmt, para = self._source_prepare(stmt, paras, dbtype)

        # writable check
        if not writable and self._has_write(stmt):
            raise TapNotAllowWrite

        if para:
            if charset:
                cursor.execute(stmt.encode(charset), para)
            else:
                cursor.execute(stmt, para)
        else:
            if charset:
                cursor.execute(stmt.encode(charset))
            else:
                cursor.execute(stmt)

        return stmt, para

    def _report_stats_exc(self, stats, exc_message, exc_trace):
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
