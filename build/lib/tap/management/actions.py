#coding=utf8

__author__ = 'Vincent@Home'

import re
import uuid

from pyramid.view import view_config
import transaction
import simplejson as json

from tap.security import encrypt_password
from tap.service.common import (
    conn_get, api2dict, CadaEncoder, dbconn_ratio_parse
)
from tap.models import (
    DBSession,
    TapDBConn,
    TapProject,
    TapUser,
    TapUserPermission,
    TapApi,
    TapSource,
    TapParameter,
    TapApiRelease,
    TapApiClient,
    TapApiAuth,
    TapApiErrors,
)


class Action(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name='action', renderer="json", permission="edit")
    def route(self):
        result = dict(success=0, message=u"没有任何操作可执行!")
        action = self.request.params.get('action')

        if 'conntest' == action:
            result = self.conn_test()
        elif 'connsave' == action:
            result = self.conn_save()
        elif 'projectsave' == action:
            result = self.project_save()
        elif 'apisave' == action:
            result = self.api_save()
        elif 'paranew' == action:
            result = self.para_new()
        elif 'paradelete' == action:
            result = self.para_delete()
        elif 'releasesave' == action:
            result = self.release_save()
        elif 'clientsave' == action:
            result = self.client_save()
        elif 'authclientadd' == action:
            result = self.authclient_add()
        elif 'displaytoken' == action:
            result = self.authclient_token()
        elif 'displayerror' == action:
            result = self.error_display()
        elif 'usersave' == action:
            result = self.user_save()

        return result

    def conn_test(self):
        dbtype = self.request.params.get('dbtype')
        connstring = self.request.params.get('connstring')
        options = self.request.params.get('options')
        result = dict(success=0, message="")
        try:
            conn = conn_get(dbtype, connstring, options)
            cursor = conn.cursor()
            if cursor:
                result["success"] = 1
        except BaseException, e:
            result["message"] = str(e)

        return result

    def conn_save(self):
        result = dict(success=0, message="")
        request = self.request
        conn_id = request.params.get('id')
        try:

            with transaction.manager:
                conn = None
                name_valid(request.params.get('name'))
                if conn_id:
                    conn = DBSession.query(TapDBConn).get(conn_id)
                else:
                    conn = TapDBConn()
                    DBSession.add(conn)
                    conn.uid_create = request.userid
                    assert request.params.get('dbtype') not in ('', None), \
                        '数据库类型不能为空'
                    assert request.params.get('connstring') not in ('',  None), \
                        '连接字符串不能为空'
                    conn.name = request.params.get('name').strip()
                    conn.dbtype = request.params.get('dbtype')
                    conn.connstring = request.params.get('connstring')

                obj_setattr(conn, 'name', request)
                obj_setattr(conn, 'dbtype', request)
                obj_setattr(conn, 'connstring', request)
                obj_setattr(conn, 'description', request)
                obj_setattr(conn, 'options', request)
            result["success"] = 1
        except BaseException, e:
            result["message"] = str(e)

        return result

    def project_save(self):
        result = dict(success=0, message="")
        try:
            with transaction.manager:
                project = None
                project_id = self.request.params.get('id')
                if project_id:
                    project = DBSession.query(TapProject).get(project_id)
                else:
                    name_valid(self.request.params.get('name'))
                    assert self.request.params.get('cnname') not in ('', None), "名称不能为空"
                    project = TapProject()
                    DBSession.add(project)
                    project.uid_create = self.request.userid
                    project.uid_owner = self.request.userid
                    project.name = self.request.params.get('name').strip().upper()
                    project.cnname = self.request.params.get('cnname').strip()
                    project.description = self.request.params.get('description')  or ''
                if 'name' in self.request.params:
                    name_valid(self.request.params.get('name'))
                    project.name = self.request.params.get('name').strip().upper()
                obj_setattr(project, 'cnname', self.request)
                obj_setattr(project, 'description', self.request)
            result["success"] = 1
        except BaseException, e:
            result["message"] = str(e)

        return result

    def api_save(self):
        result = dict(success=0, message="")
        request = self.request
        try:
            with transaction.manager:
                api = None
                changed = False
                api_id = self.request.params.get('id')
                if api_id:
                    api = DBSession.query(TapApi).get(api_id)
                else:
                    name_valid(self.request.params.get('name'))
                    assert request.params.get('cnname') not in ('', None),\
                        "名称不能为空"
                    assert request.params.get('project_id') not in ('',  None)
                    api = TapApi()
                    DBSession.add(api)
                    api.uid_create = self.request.userid
                    api.uid_update = self.request.userid
                    api.name = self.request.params.get('name').strip()
                    api.cnname = self.request.params.get('cnname').strip()
                    api.description = request.params.get('description') or ''
                    api.project_id = self.request.params['project_id']
                    source = TapSource()
                    DBSession.add(source)
                    api.source = source
                    changed = True
                changed = obj_setattr(api, 'name', request) or changed
                changed = obj_setattr(api, 'cnname', request) or changed
                changed = obj_setattr(api, 'description', request) or changed
                # changed = obj_setattr(api, 'dbconn_id', request, 'INT') or \
                #           changed
                changed = (obj_setattr(api, 'cache_time', request, 'INT') or
                           changed)
                changed = obj_setattr(api, 'cache_persistencedb_id', request,
                                      'INT') or changed
                if 'writable' in self.request.params:
                    api.writable = int(self.request.params['writable'])

                # update source
                changed = obj_setattr(api.source, 'source', request) or changed
                changed = obj_setattr(api.source, 'source_type',
                                      request) or changed

                # update dbconn
                dbconn = request.params.get('dbconn', '').split(',')
                dbconn = [int(d.strip()) for d in dbconn if d.strip()]
                api_dbconn = [d.id for d in api.dbconn]
                if dbconn != api_dbconn:
                    changed = True
                    api.dbconn_order = ','.join([str(d) for d in dbconn])
                    for dbid in api_dbconn:
                        api.dbconn.remove(
                            DBSession.query(TapDBConn).get(dbid)
                        )
                    for dbid in dbconn:
                        api.dbconn.append(
                            DBSession.query(TapDBConn).get(dbid)
                        )

                # update dbconn_secondary
                dbconn = request.params.get('dbconn_secondary', '').split(',')
                dbconn = [int(d.strip()) for d in dbconn if d.strip()]
                api_dbconn = [d.id for d in api.dbconn_secondary]
                if dbconn != api_dbconn:
                    changed = True
                    api.dbconn_secondary_order = \
                        ','.join([str(d) for d in dbconn])
                    for dbid in api_dbconn:
                        api.dbconn_secondary.remove(
                            DBSession.query(TapDBConn).get(dbid)
                        )
                    for dbid in dbconn:
                        api.dbconn_secondary.append(
                            DBSession.query(TapDBConn).get(dbid)
                        )

                changed = obj_setattr(api, 'dbconn_ratio', request) or changed

                # update paras
                for para in api.paras:
                    changed = para_setattr(para, 'name', request) or changed
                    changed = para_setattr(para, 'val_type', request) or changed
                    changed = para_setattr(para, 'default', request) or changed
                    changed = (para_setattr(para, 'absent_type', request) or
                               changed)

                if changed:
                    api.uid_update = self.request.userid
                    api.status = 'EDIT'
                    self._valid_dbconn(api)
                else:
                    raise Exception("没有任何修改")

            result["success"] = 1
        except BaseException, e:
            import traceback; traceback.print_exc()
            result["message"] = str(e)

        return result

    def _valid_dbconn(self, api):
        # 1. dbconn 和 dbconn_secondary 不能有重合
        dbconn = set([d.id for d in api.dbconn])
        dbconn_secondary = set([d.id for d in api.dbconn_secondary])
        if not dbconn or (not dbconn_secondary and not api.dbconn_ratio):
            return
        assert dbconn != dbconn_secondary, '主数据库和负载均衡数据库不能有重合'

        # 2. dbconn_ratio 负载均衡配置验证
        if dbconn_secondary and not api.dbconn_ratio:
            raise Exception("负载均衡配置缺失!")

        if not dbconn_secondary and api.dbconn_ratio:
            raise Exception("没有设置负载均衡数据库")

        if not dbconn_secondary:
            return

        ratio = dbconn_ratio_parse(api.dbconn_ratio)
        ratio_dbs = []
        for key, config in ratio.items():
            assert key in config.keys(), \
                '没有配置主数据库[%s]的负载比率' % key.encode('utf8')
            ratio_dbs.extend(config.keys())
            assert sum(config.values()) == 100, \
                '[%s]负载比率加总值应当为100' % key.encode("utf8")
        for db in api.dbconn_secondary:
            assert db.name in ratio_dbs, \
                "负载均衡数据库[%s]没有在负载均衡配置中使用" % db.name.encode('utf8')

        primary_names = [db.name for db in api.dbconn]
        for key in ratio.keys():
            assert key in primary_names, \
                "负载均衡配置中有不存在的主数据库[%s]" % key.encode('utf8')

        db_names = [db.name for db in api.dbconn_secondary]
        db_names.extend(primary_names)
        for key in ratio_dbs:
            assert key in db_names,\
                "负载均衡配置中有不存在的数据库[%s]" % key.encode('utf8')

        all_db = dict([(d.name, d) for d in api.dbconn])
        all_db.update([(d.name, d) for d in api.dbconn_secondary])
        for key, config in ratio.items():
            primarydb = set([all_db[key].dbtype])
            secondarydb = set([all_db[dbname].dbtype for dbname in
                               config.keys()])
            assert primarydb == secondarydb, "同一组负载均衡数据库类型应该相同"

    def para_new(self):
        result = dict(success=0, message="")
        request = self.request
        api_id = request.params.get('id')
        try:

            with transaction.manager:
                api_id = int(api_id)
                para = TapParameter(api_id=api_id, name='__None__')
                DBSession.add(para)
                DBSession.flush()
                result["para_id"] = para.id
                result["para_name"] = '__None__'
                result["success"] = 1
        except BaseException, e:
            result["message"] = str(e)
        return result

    def para_delete(self):
        result = dict(success=0, message="")
        request = self.request
        para_id = request.params.get('id')
        try:

            with transaction.manager:
                para_id = int(para_id)
                para = DBSession.query(TapParameter).get(para_id)
                DBSession.delete(para)
                result["success"] = 1
        except BaseException, e:
            result["message"] = str(e)
        return result

    def release_save(self):
        result = dict(success=0, message="")
        request = self.request
        try:

            with transaction.manager:
                api_id = request.params.get('api_id')
                api_id = int(api_id)
                api = DBSession.query(TapApi).get(api_id)

                # auth type, change api
                auth_type = request.params['auth_type']
                if auth_type != api.auth_type:
                    api.auth_type = auth_type

                release = TapApiRelease()
                release.api_id = api.id
                release.project_name = api.project.name
                release.api_name = api.name
                # release.dbconn_id = api.dbconn_id
                release.version = request.params['version']
                release.notes = request.params['notes']
                release.uid_release = request.userid
                release.content = json.dumps(api2dict(api), cls=CadaEncoder)
                DBSession.add(release)
                api.status = 'RELEASE'
                result["success"] = 1
        except BaseException, e:
            import traceback; traceback.print_exc()
            result["message"] = str(e)
        return result

    def client_save(self):
        result = dict(success=0, message="")
        request = self.request
        try:

            with transaction.manager:
                client_id = request.params.get('client_id')
                client = None
                name = self.request.params.get('name')
                if client_id:
                    client = DBSession.query(TapApiClient).get(client_id)
                else:
                    assert name not in ('', None), 'Name cant None'
                    client = TapApiClient(name=name)
                    client.uid_create = self.request.userid
                    client.token = str(uuid.uuid4())
                    DBSession.add(client)

                obj_setattr(client, 'name', self.request)
                obj_setattr(client, 'description', self.request)
                result["success"] = 1
        except BaseException, e:
            import traceback; traceback.print_exc()
            result["message"] = str(e)
        return result

    def authclient_add(self):
        result = dict(success=0, message="")
        try:
            with transaction.manager:
                client_id = self.request.params['id']
                api_id = int(self.request.params['api_id'])
                client = DBSession.query(TapApiClient).get(client_id)
                if DBSession.query(TapApiAuth).filter_by(client_id=client.id,
                                                         api_id=api_id).first():
                    result['message'] = u'重复添加: %s' % client.name
                    return result

                auth = TapApiAuth()
                auth.client_id = client.id
                auth.api_id = api_id
                auth.uid_auth = self.request.userid
                auth.token = client.token
                DBSession.add(auth)
            result['success'] = 1
        except BaseException, e:
            result["message"] = str(e)
        return result

    def authclient_token(self):
        result = dict(success=0, message="")
        with transaction.manager:
            auth_id = int(self.request.params['auth_id'])
            auth = DBSession.query(TapApiAuth).get(auth_id)
            result['token'] = auth.token
            result['success'] = 1
        return result

    def error_display(self):
        result = dict(success=0, message="")
        with transaction.manager:
            error_id = self.request.params['id']
            error = DBSession.query(TapApiErrors).get(error_id)
            if not error:
                result['message'] = u'错误内容不存在'
            result['context'] = json.loads(error.exc_context)
            result['traceback'] = error.exc_trace
            result['success'] = 1
        return result

    def user_save(self):
        result = dict(success=0, message="")
        try:
            with transaction.manager:
                user = None
                user_id = self.request.params.get('id')
                if user_id:
                    user = DBSession.query(TapUser).get(user_id)
                else:
                    name_valid(self.request.params.get('name'))
                    user = TapUser()
                    DBSession.add(user)
                    user.name = self.request.params.get('name').strip().upper()
                    user.description = (self.request.params.get('description')
                                        or '')
                obj_setattr(user, 'full_name', self.request)
                obj_setattr(user, 'description', self.request)
                if 'is_admin' in self.request.params:
                    user.is_admin = int(self.request.params['is_admin'])
                if 'password' in self.request.params:
                    password = self.request.params.get('password').strip()
                    assert len(password) > 6, '密码长度最少为6'
                    user.password = encrypt_password(password.encode('utf8'))
            result["success"] = 1
        except BaseException, e:
            result["message"] = str(e)

        return result



def name_valid(name):
    assert name not in ('', None)
    name = re.sub(ur'\w', '', name)
    assert name == u'', '包含非法字符: %s' % name.encode('utf8')


def obj_setattr(obj, name, request, type='TEXT'):
    if name in request.params:
        val = request.params[name]
        if type == 'TEXT':
            pass
        elif type == 'INT':
            if val:
                val = int(val)
            else:
                val = None
        if getattr(obj, name) != val:
            setattr(obj, name, val)
            return True
    return False


def para_setattr(para, name, request, type="TEXT"):
    attr_name = 'para-%s-%s' % (name, para.id)
    if attr_name in request.params:
        val = request.params[attr_name]
        if type == 'TEXT':
            pass
        elif type == 'INT':
            if val:
                val = int(val)
            else:
                val = None
        if getattr(para, name) != val:
            setattr(para, name, val)
            return True
    return False
