# coding=utf8

import time
import datetime
import urllib
import math
import socket
import tempfile
import shutil
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.security import remember, forget
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
import simplejson as json

import transaction
import xlrd
from sqlalchemy import func, or_

from tap.security import valid_password
from tap.service.common import dict2api, api2dict
from tap.service.common import TapEncoder, measure
from tap.service.common import conn_get, stmt_split
from tap.service.common import show_tables, Paginator
from tap.service.api import Program
from tap.service import exceptions
from tap.service.tcaptcha import gen_captcha, validate
from tap.management.uicontrol import (
    gen_breadcrumbs, gen_project_names,  gen_active
)
from tap.models import (
    DBSession,
    TapUser,
    TapDBConn,
    TapProject,
    TapApi,
    TapApiClient,
    TapApiAuth,
    TapApiAccessKey,
    TapApiRelease,
    TapApiStats,
    TapApiErrors,
    TapUserPermission,
    TapPermission,
    Task,
    TapApiClientCustomAuth,
    CaptchaCode,
)

# 发布时取消注释
# @view_config(context=Exception)
# def exception_view(context, request):
#     if isinstance(context, exceptions.UserNotAvailable):
#         # 用户失效，退出登录
#         headers = forget(request)
#         return HTTPFound(location='/', headers=headers)
#
#     response = Response('Internal Server Error')
#     response.status = 500
#     return response

@forbidden_view_config()
def forbidden(request):
    if not request.userid:
        path = request.path
        path = urllib.quote_plus(path)
        url = '/management/login?next=%s' % path
        return HTTPFound(location=url)
    else:
        return render_to_response('templates/forbidden.html', locals(),
                                  request=request)


@view_config(route_name="login")
def login(request):
    next_url = request.params.get('next')
    user_name = ""
    user_pwd = ""
    err_msg = ""
    if "form.submitted" in request.params:
        user_name = request.params.get('username')
        user_pwd = request.params.get('password')
        captcha_id = request.params.get('captcha_id')
        captcha_code = request.params.get('captcha_code')
        with transaction.manager:
            if not captcha_id or not captcha_code:
                err_msg = u'验证失败'
            elif not validate(captcha_id, captcha_code):
                err_msg = u'验证失败'
            user = DBSession.query(TapUser).filter_by(name=user_name).first()
            if not user:
                err_msg = u'用户不存在'
            elif user and not valid_password(user, user_pwd):
                err_msg = u'密码错误'

            if not err_msg:
                headers = remember(request, user.id, max_age=86400)
                return HTTPFound(location=next_url, headers=headers)

    captcha_id = gen_captcha()
    return render_to_response('templates/login.html', locals(), request=request)


@view_config(route_name="logout")
def logout(request):
    headers = forget(request)
    return HTTPFound(location='/', headers=headers)


def common_vars(request):
    top_breadcrumbs = gen_breadcrumbs(request)
    project_names = gen_project_names(request)
    result = dict(
        top_breadcrumbs=top_breadcrumbs,
        project_names=project_names
    )
    result.update(gen_active(request))
    return result


class Management(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name='home', permission="view")
    def home(self):
        with transaction.manager:
            projects = DBSession.query(TapProject)\
                .order_by(TapProject.id.desc())
            context = dict(pagename=u' Tap', projects=projects)
            context.update(common_vars(self.request))
            return render_to_response('templates/home.html', context,
                                      request=self.request)

    @view_config(route_name='docs', permission="view")
    def docs(self):
        context = common_vars(self.request)
        context['pagename'] = u' Tap - 文档'
        return render_to_response('templates/docs.html', context,
                                  request=self.request)

    @view_config(route_name='apps', permission="view")
    def apps(self):
        context = common_vars(self.request)
        context['pagename'] = u' Tap - Applications'
        return render_to_response('templates/applications.html', context,
                                  request=self.request)

    @view_config(route_name='apps_mobilehosting', permission="view")
    def apps_hosting(self):
        context = common_vars(self.request)
        context['pagename'] = u' Tap - Applications'
        return render_to_response('templates/applications_mobileapp.html',
                                  context, request=self.request)


    @view_config(route_name="user_list", permission="view")
    def user_list(self):
        with transaction.manager:
            users = DBSession.query(TapUser)
            context = dict(pagename=u"权限管理", users=users)
            context.update(common_vars(self.request))
            return render_to_response("templates/user_list.html",
                                      context, request=self.request)

    @view_config(route_name="user_edit", permission="edit")
    def user_edit(self):
        with transaction.manager:
            user_id = self.request.matchdict['user_id']
            user = DBSession.query(TapUser).get(user_id)
            user_permissions = DBSession.query(TapUserPermission).filter_by(
                user_id=user.id)
            user_permissions = dict(
                [(p.permission_id, p) for p in user_permissions])
            permissions = DBSession.query(TapPermission).order_by(
                TapPermission.id.asc())
            context = dict(pagename=u"权限管理",
                           user_permissions=user_permissions,
                           permissions=permissions, user=user)
            context.update(common_vars(self.request))
            return render_to_response("templates/user_edit.html",
                                      context, request=self.request)

    @view_config(route_name="database", permission="view")
    def database(self):
        with transaction.manager:
            conns = DBSession.query(TapDBConn).order_by(TapDBConn.id.desc())
            context = dict(conns=conns, pagename=u"数据库")
            context.update(common_vars(self.request))
            return render_to_response('templates/database.html', context,
                                      request=self.request)

    @view_config(route_name="database_view", permission="view")
    def database_view(self):
        with transaction.manager:
            dbconn_id = self.request.matchdict['dbconn_id']
            dbconn = DBSession.query(TapDBConn).get(dbconn_id)

            conn = conn_get(dbconn.dbtype, dbconn.connstring, dbconn.options)
            cursor = conn.cursor()

            context = dict(dbconn=dbconn, pagename=u"%s - 数据库" % dbconn.name,
                           tablelist=show_tables(dbconn.dbtype, cursor))

            context.update(common_vars(self.request))
            return render_to_response("templates/database_view.html",
                                      context, request=self.request)

    @view_config(route_name="database_execute", permission="view")
    def database_execute(self):
        with transaction.manager:
            source = self.request.params['source']
            dbconn_id = self.request.matchdict['dbconn_id']
            dbconn = DBSession.query(TapDBConn).get(dbconn_id)
            conn = conn_get(dbconn.dbtype, dbconn.connstring, dbconn.options)
            cursor = conn.cursor()

            try:
                with measure() as time_used:
                    if dbconn.dbtype in ('MYSQL', 'ORACLE', 'PGSQL'):
                        if dbconn.dbtype in ('MYSQL', 'PGSQL'):
                            assert 'limit' in source.lower(), 'need LIMIT control'
                        elif dbconn.dbtype in ('ORACLE'):
                            assert 'rownum' in source.lower(), \
                                'need rownum control'
                        stmts = stmt_split(source)
                        for stmt in stmts:
                            cursor.execute(stmt)
                    elif dbconn.dbtype == 'MSSQL':
                        assert 'top' in source.lower(), 'need TOP result ' \
                                                        'control'
                        cursor.execute(source)

                result = list([list(r) for r in cursor.fetchall()])
                for row in result:
                    for i in range(len(row)):
                        val = row[i]
                        if isinstance(val, str):
                            try:
                                row[i] = val.decode('utf-8')
                            except UnicodeDecodeError:
                                row[i] = val.decode('gb18030', 'ignore')

                cols = [c[0] for c in cursor.description]
                result.insert(0, cols)
                result = dict(
                    datatable=result,
                    elapse=time_used()
                )
                result_json = json.dumps(result, cls=TapEncoder)
                context = dict(result=result, result_json=result_json)

                return render_to_response("templates/database_execute.html",
                                          context, request=self.request)
            except Exception, e:
                import traceback
                msg = str(e)
                trace = traceback.format_exc()
                return Response(('<div class="alert alert-danger">%s</div><pre '
                                 'style="border-radius:0px">%s</pre>')
                                % (msg, trace))

    @view_config(route_name="project", permission="view")
    def project(self):
        with transaction.manager:
            projects = DBSession.query(TapProject).order_by(TapProject.id.desc())
            context = dict(projects=projects, pagename=u'项目')
            context.update(common_vars(self.request))
            return render_to_response('templates/project.html', context,
                                      request=self.request)

    @view_config(route_name="project_detail", permission="view")
    def project_detail(self):
        with transaction.manager:
            project_id = self.request.matchdict['project_id']
            project = DBSession.query(TapProject).get(project_id)

            #load
            username = project.user_create.name
            del username

            page = int(self.request.params.get('page', 1))
            sort_field = self.request.params.get('sort-field', '')
            sort_direction = self.request.params.get('sort-direction', '')
            q = self.request.params.get('q', '')

            apis = DBSession.query(TapApi)\
                .filter(TapApi.project_id==project_id)
            if q:
                apis = apis.filter(or_(TapApi.cnname.like(u'%'+q+u'%'),
                                       TapApi.name.like(u'%'+q+u'%')))
            total = apis.count()
            if sort_field and sort_direction:
                _field = sort_field.replace('api-', '').strip()
                apis = eval('apis.order_by(TapApi.%s.%s())' %
                            (_field, sort_direction))
            else:
                apis = apis.order_by(TapApi.id.desc())

            paginator = Paginator(page, total=total, paras={'q': q,
                'sort-field': sort_field, 'sort-direction': sort_direction})
            apis = apis.offset((page-1)*paginator.num_per_page)
            apis = apis.limit(paginator.num_per_page)

            # load relation objects
            spark_data = {}
            spark_time = {}
            et = datetime.datetime.now() - datetime.timedelta(minutes=5)
            end_time = datetime.datetime(et.year, et.month, et.day, et.hour,
                                         et.minute)
            start_time = end_time - datetime.timedelta(minutes=35)
            for api in apis:
                user_create = api.user_create
                query = DBSession.query(TapApiStats)\
                    .filter(TapApiStats.api_id==api.id,
                            TapApiStats.client_id==-1,
                            TapApiStats.occurrence_time<=end_time,
                            TapApiStats.occurrence_time>start_time)\
                    .order_by(TapApiStats.occurrence_time.desc())
                query = query.limit(35)
                timeseries = [(_q.occurrence_time, _q.occurrence_total)
                              for _q in query]
                if not timeseries or timeseries[-1][0] != end_time:
                    timeseries.append((end_time, 0))
                timeseries = ChartsGen.fix_timeseries(
                    timeseries, 35, interval=datetime.timedelta(minutes=1))
                spark_data[api.id] = ','.join([str(t[1]) for t in timeseries])
                _spark_time = [t[0].strftime('%Y-%m-%d %H:%M')
                              for t in timeseries]
                spark_time[api.id] = ','.join(_spark_time)

            context = dict(project=project, pagename=project.cnname,
                           apis=apis, paginator=paginator, q=q,
                           spark_data=spark_data, spark_time=spark_time,
                           sort_field=sort_field, sort_direction=sort_direction)
            context.update(common_vars(self.request))
            return render_to_response('templates/project_detail.html',
                                      context, request=self.request)

    @view_config(route_name="api_config", permission="view")
    def api_config(self):
        api_id = self.request.matchdict['api_id']
        with transaction.manager:
            api = DBSession.query(TapApi).get(api_id)

            # load relation objects
            load = [p for p in api.paras]
            del load
            load = api.source
            del load
            load = api.project
            del load

            dbconn = [conn.id for conn in api.get_dbconn()]
            dbconn_secondary = [conn.id for conn in api.get_dbconn_secondary()]
            conns = DBSession.query(TapDBConn).order_by(TapDBConn.id.desc())
            conns = dict([(db.id, db) for db in conns])

            # _conns = dict([(db.id, db) for db in conns])
            # conns = OrderedDict()
            # for conn_id in dbconn:
            #     conns[conn_id] = _conns[conn_id]
            # for conn_id, conn in _conns.items():
            #     if conn_id not in conns:
            #         conns[conn_id] = conn

            # conns_secondary = OrderedDict()
            # for conn_id in dbconn_secondary:
            #     conns_secondary[conn_id] = _conns[conn_id]
            # for conn_id, conn in _conns.items():
            #     if conn_id not in conns_secondary:
            #         conns_secondary[conn_id] = conn

            context = dict(pagename=u"%s - 配置" % api.name, conns=conns,
                           api=api, active_config=True, dbconn=dbconn,
                           dbconn_secondary=dbconn_secondary)
            context.update(common_vars(self.request))
            return render_to_response("templates/api_config.html", context,
                                      request=self.request)

    @view_config(route_name="api_stats", permission="view")
    def api_stats(self):
        api_id = self.request.matchdict['api_id']
        client_id = self.request.params.get('client-id')
        with transaction.manager:
            api = DBSession.query(TapApi).get(api_id)

            auth_clients = DBSession.query(TapApiAuth).filter_by(api_id=api.id)
            clients = []
            for auth in auth_clients:
                clients.append(dict(
                    id=auth.auth_client.id,
                    name=auth.auth_client.name
                ))

            error_list = DBSession.query(TapApiErrors).filter_by(api_id=api_id)
            category = 'API'
            if client_id:
                error_list = error_list.filter_by(client_id=client_id)
                category = 'API-CLIENT'
                client_id = int(client_id)
            else:
                error_list = error_list.filter_by(client_id=-1)
            total = error_list.count()
            error_list = error_list.order_by(TapApiErrors.occurrence_time.desc())

            page = int(self.request.params.get('page', 1))
            paginator = Paginator(page, total, num_per_page=10, paras={
                'client-id': client_id})

            error_list = error_list.offset((page - 1) * 10).limit(10)

            context = dict(pagename=u"%s - 统计" % api.name, api=api,
                           active_stats=True, clients=clients,
                           category=category, paginator=paginator,
                           error_list=error_list, client_id=client_id)
            context.update(common_vars(self.request))
            return render_to_response("templates/api_stats.html", context,
                                      request=self.request)

    @view_config(route_name="api_cachemanage", permission="view")
    def api_cachemanage(self):
        api_id = self.request.matchdict['api_id']
        selected = self.request.params.get('selected', None)
        if selected:
            selected = int(selected)
        with transaction.manager:
            api = DBSession.query(TapApi).get(api_id)

            releases = DBSession.query(TapApiRelease).filter_by(api_id=api.id)\
                                .order_by(TapApiRelease.version.desc())
            releases = list(releases)

            for release in releases:
                if release.version == selected:
                    selected = release
            if selected is None and releases:
                selected = releases[0]
            # TODO handle no releases
            api_selected = None
            if selected:
                api_selected = dict2api(json.loads(selected.content))

            context = dict(pagename=u"%s - 线上管理" % api.name, api=api,
                           active_cachemanage=True, releases=releases,
                           selected=selected, api_selected=api_selected,
                           math=math)
            context.update(common_vars(self.request))
            return render_to_response("templates/api_cachemanage.html",
                                      context, request=self.request)

    @view_config(route_name="api_release", permission="view")
    def api_release(self):
        api_id = self.request.matchdict['api_id']
        with transaction.manager:
            api = DBSession.query(TapApi).get(api_id)

            # load relation objects
            load = api.paras
            del load
            load = api.dbconn
            del load

            releases = DBSession.query(TapApiRelease.id).filter_by(
                api_id=api_id)
            total = releases.count()
            releases = DBSession.query(TapApiRelease).filter_by(
                api_id=api_id).order_by(TapApiRelease.created.desc())
            page = int(self.request.params.get('page', 1))
            paginator = Paginator(page, total)
            releases = releases.offset((page-1)*paginator.num_per_page)
            releases = releases.limit(paginator.num_per_page)

            release_db = {}  # release_id: [(db_name,db_id)]
            release_content = {}
            for release in releases:
                content = json.loads(release.content)
                content = dict2api(content)
                release_content[release.id] = content
                release_db[release.id] = OrderedDict([(db.name, db.id) for db in
                                          content.dbconn])
                load = release.user_release
                del load

            current_version = max([v.version for v in api.releases] or [0]) + 1

            context = dict(pagename=u"%s - 发布" % api.name, api=api,
                           active_release=True, current_version=current_version,
                           releases=releases, paginator=paginator,
                           release_db=release_db, release_content=release_content)
            context.update(common_vars(self.request))
            return render_to_response("templates/api_release.html", context,
                                      request=self.request)

    @view_config(route_name="api_release_version", permission="view")
    def api_release_version(self):
        release_id = self.request.matchdict['release_id']
        with transaction.manager:
            release = DBSession.query(TapApiRelease).get(release_id)
            release = json.loads(release.content)
            release = dict2api(release)

            context = dict(pagename=u"", api=release)
            context.update(common_vars(self.request))
            return render_to_response("templates/api/api_release_version.html",
                                      context, request=self.request)

    @view_config(route_name="client_home", permission="view")
    def client_home(self):
        with transaction.manager:
            clients = DBSession.query(TapApiClient)

            context = dict(pagename=u"客户端管理", clients=clients)
            context.update(common_vars(self.request))
            return render_to_response("templates/client_home.html", context,
                                      request=self.request)

    @view_config(route_name="client_detail", permission="view")
    def client_detail(self):
        client_id = int(self.request.matchdict['client_id'])
        with transaction.manager:
            client = DBSession.query(TapApiClient).get(client_id)
            if not client.custom_auth:
                custom_auth = TapApiClientCustomAuth(client_id=client.id)
                DBSession.add(custom_auth)

        with transaction.manager:
            client = DBSession.query(TapApiClient).get(client_id)

            # eagle load
            custom_auth = client.custom_auth
            for para in custom_auth.paras:
                del para
            del custom_auth

            auth_list = DBSession.query(TapApiAuth).filter_by(
                client_id=client_id)
            project_apis = {}
            for auth in auth_list:
                if auth.api.project.id not in project_apis:
                    project_apis[auth.api.project.id] = []
                project_apis[auth.api.project.id].append(auth.api)

            for project_id, apis in project_apis.items():
                group = []
                groups = [group]
                project_apis[project_id] = groups
                for api in apis:
                    group.append(api)
                    if len(group) == 3:
                        group = []
                        groups.append(group)

            context = dict(pagename=u"%s - 客户端" % client.name,
                           project_apis=project_apis, client=client)
            context.update(common_vars(self.request))
            context.update(self.auth_detail())

            return render_to_response("templates/client_detail.html",
                                      context, request=self.request)

    @view_config(route_name="auth_home", permission="view")
    def auth_home(self):
        with transaction.manager:
            api_id = self.request.matchdict['api_id']
            api = DBSession.query(TapApi).get(api_id)
            auth_list = api.auth_clients
            # load
            for auth in auth_list:
                auth.user_auth
                auth.auth_client

            clients = DBSession.query(TapApiClient)

            context = dict(pagename=u"%s - 授权" % api.name,
                           auth_list=auth_list, api=api, active_auth=True,
                           clients=clients)
            context.update(common_vars(self.request))
            return render_to_response("templates/auth_home.html", context,
                                      request=self.request)

    # @view_config(route_name="client_accesskeys", permission="view")
    def auth_detail(self):
        page = int(self.request.params.get('page', 1))
        with transaction.manager:
            client_id = int(self.request.matchdict['client_id'])

            access_keys = DBSession.query(TapApiAccessKey).filter_by(
                client_id=client_id
            )

            total = access_keys.count()
            paginator = Paginator(page, total=total, num_per_page=15)
            access_keys = access_keys.offset((page-1)*15)
            access_keys = access_keys.limit(15)
            client = DBSession.query(TapApiClient).get(client_id)

            context = dict(
                pagename=u"%s: Accesskeys" % (client.name,),
                access_keys=access_keys,
                paginator=paginator, datetime=datetime, active_auth=True
            )
            # context.update(common_vars(self.request))
            # return render_to_response("templates/client_accesskeys.html",
            #                           context, request=self.request)
            return context

    @view_config(route_name="api_test", permission="view")
    def api_test(self):
        params = dict(self.request.params)

        api_id = params['id']
        api = DBSession.query(TapApi).get(int(api_id))
        from_cfgpage = False # 从api_config 页面提交
        if 'dbconn_secondary' in params and 'source_type' in params:
            from_cfgpage = True
            dbconn_idlist = params['dbconn']
            dbconn = []
            for _id in dbconn_idlist.split(','):
                if not _id:
                    continue
                conn = DBSession.query(TapDBConn).get(_id)
                dbconn.append(dict(
                    id=conn.id, name=conn.name, dbtype=conn.dbtype,
                    connstring=conn.connstring, options=conn.options
                ))
            dbconn_secondary = []
            for _id in params['dbconn_secondary'].split(','):
                if not _id:
                    continue
                conn = DBSession.query(TapDBConn).get(_id)
                dbconn_secondary.append(dict(
                    id=conn.id, name=conn.name, dbtype=conn.dbtype,
                    connstring=conn.connstring, options=conn.options
                ))
            config = dict(
                id=api_id, name=params.get('name'), cnname=params.get('cnname'),
                description=params.get('description'), cache_time=0,
                writable=bool(int(params.get('writable'))), auth_type='OPEN',
                project_id=api.project_id, paras=[],
                project=dict(
                    name=api.project.name
                ),
                dbconn=dbconn,
                dbconn_ratio=params.get('dbconn_ratio'),
                dbconn_secondary=dbconn_secondary,
                source=dict(
                    id=-1, source=params['source'],
                    source_type=params['source_type']
                )
            )
            paras = {}
            for k, v in params.items():
                splits = k.split('-')
                if not k.startswith('para') and not len(splits) == 3:
                    continue
                name, _id = splits[1], splits[2]
                if not _id.isdigit():
                    continue
                if _id not in paras:
                    paras[_id] = {}
                paras[_id][name] = v
            for para in paras.values():
                config['paras'].append(dict(
                    name=para[u'name'], val_type=para[u'val_type'],
                    default=para[u'default'], absent_type=para[u'absent_type']
                ))
            config = dict2api(config)
        else:
            config = api2dict(api)
            config = dict2api(config)

        config.cache_time = 0
        config.auth_type = 'OPEN'

        paras = {}
        for para in config.paras:
            if para.name in params and from_cfgpage == False:
                paras[para.name] = params[para.name]
            else:
                paras[para.name] = para.default

        try:
            result = Program(config, None).run(paras)
            result_json = json.dumps(result, cls=TapEncoder)

            context = dict(result=result, config=config, paras=paras,
                           result_json=result_json)

            return render_to_response("templates/api_test.html", context,
                                      request=self.request)
        except Exception, e:
            import traceback
            msg = str(e)
            trace = traceback.format_exc()
            return Response(('<div class="alert alert-danger">%s</div><pre '
                             'style="border-radius:0px">%s</pre>')
                            % (msg, trace))


class ChartsGen(object):
    def __init__(self, request):
        self.request = request

    def chart_time(self, category):
        max_points = 360
        query = None
        if category == 'PROJECT':
            project_id = int(self.request.params['project-id'])
            query = DBSession.query(
                TapApiStats.occurrence_time,
                func.avg(TapApiStats.elapse_max).label('elapse_max'),
                func.avg(TapApiStats.elapse_avg).label('elapse_avg'),
                func.avg(TapApiStats.elapse_min).label('elapse_min')
            ).filter(TapApiStats.project_id==project_id,
                     TapApiStats.client_id==-1)\
                .group_by(TapApiStats.occurrence_time)\
                .order_by(TapApiStats.occurrence_time.desc())
            query = query.limit(max_points)
        elif category == 'API':
            api_id = int(self.request.params['api-id'])
            query = DBSession.query(
                TapApiStats.occurrence_time,
                func.avg(TapApiStats.elapse_max).label('elapse_max'),
                func.avg(TapApiStats.elapse_avg).label('elapse_avg'),
                func.avg(TapApiStats.elapse_min).label('elapse_min')
            ).filter(TapApiStats.api_id==api_id, TapApiStats.client_id==-1)\
                .group_by(TapApiStats.occurrence_time)\
                .order_by(TapApiStats.occurrence_time.desc())
            query = query.limit(max_points)
        elif category == 'API-CLIENT':
            api_id = int(self.request.params['api-id'])
            client_id = int(self.request.params['client-id'])
            query = DBSession.query(
                TapApiStats.occurrence_time,
                func.avg(TapApiStats.elapse_max).label('elapse_max'),
                func.avg(TapApiStats.elapse_avg).label('elapse_avg'),
                func.avg(TapApiStats.elapse_min).label('elapse_min')
            ).filter_by(api_id=api_id, client_id=client_id)\
                .group_by(TapApiStats.occurrence_time)\
                .order_by(TapApiStats.occurrence_time.desc())

        avg_data = []
        serie_avg = dict(name='AVG', data=avg_data, color='#7cb5ec')
        max_data = []
        serie_max = dict(name='MAX', data=max_data, color='#d7a59d')
        min_data = []
        serie_min = dict(name='MIN', data=min_data, color='#69aa46')
        series = [serie_avg, serie_max, serie_min]
        for stat in query:
            occurrence_time = time.mktime(stat.occurrence_time.timetuple())
            occurrence_time += (8 * 3600)
            occurrence_time = int(occurrence_time * 1000)
            avg_data.append((occurrence_time, stat.elapse_avg))
            max_data.append((occurrence_time, stat.elapse_max))
            min_data.append((occurrence_time, stat.elapse_min))
        avg_data = self.fix_timeseries(avg_data, max_points=max_points)
        serie_avg['data'] = avg_data
        max_data = self.fix_timeseries(max_data, max_points=max_points)
        serie_max['data'] = max_data
        min_data = self.fix_timeseries(min_data, max_points=max_points)
        serie_min['data'] = min_data
        return series

    def chart_visit(self, category):
        max_points = 360
        query = None
        if category == 'PROJECT':
            project_id = int(self.request.params['project-id'])
            query = DBSession.query(
                TapApiStats.occurrence_time,
                func.sum(TapApiStats.exception_total).label('exception_total'),
                func.sum(TapApiStats.occurrence_total).label('occurrence_total')
            ).filter_by(project_id=project_id, client_id=-1)\
                .group_by(TapApiStats.occurrence_time)\
                .order_by(TapApiStats.occurrence_time.desc())
            query = query.limit(max_points)
        elif category == 'API':
            api_id = int(self.request.params['api-id'])
            query = DBSession.query(
                TapApiStats.occurrence_time,
                func.sum(TapApiStats.exception_total).label('exception_total'),
                func.sum(TapApiStats.occurrence_total).label('occurrence_total')
            ).filter_by(api_id=api_id, client_id=-1)\
                .group_by(TapApiStats.occurrence_time)\
                .order_by(TapApiStats.occurrence_time.desc())
            query = query.limit(max_points)
        elif category == 'API-CLIENT':
            api_id = int(self.request.params['api-id'])
            client_id = int(self.request.params['client-id'])
            query = DBSession.query(
                TapApiStats.occurrence_time,
                func.sum(TapApiStats.exception_total).label('exception_total'),
                func.sum(TapApiStats.occurrence_total).label('occurrence_total')
            ).filter_by(api_id=api_id, client_id=client_id)\
                .group_by(TapApiStats.occurrence_time)\
                .order_by(TapApiStats.occurrence_time.desc())
            query = query.limit(max_points)

        visit_data = []
        visit = dict(name=u'访问量', data=visit_data, color='#7cb5ec')
        error_data = []
        error = dict(name=u'错误量', data=error_data, color='#d7a59d')
        for stat in query:
            occurrence_time = time.mktime(stat.occurrence_time.timetuple())
            occurrence_time += (8 * 3600)
            occurrence_time = int(occurrence_time * 1000)
            visit_data.append((occurrence_time, stat.occurrence_total))
            error_data.append((occurrence_time, stat.exception_total))
        visit_data = self.fix_timeseries(visit_data, max_points=max_points)
        visit['data'] = visit_data
        error_data = self.fix_timeseries(error_data, max_points=max_points)
        error['data'] = error_data
        return [visit, error]

    @classmethod
    def fix_timeseries(cls, timeseries, max_points=120, interval=None):
        """

        :param timeseries: [(timestamp, value)]
        :return:
        """
        if len(timeseries) < 1:
            return

        timeseries.sort(key=lambda x: x[0])

        if interval is None:
            intervals = [(timeseries[i][0] - timeseries[i-1][0]) for i in
                         range(1, len(timeseries))]
            interval = min(intervals)

        # first data point is latest, fill point by interval
        temp = {}
        for timestamp, value in timeseries:
            temp[timestamp] = value
        latest_time = timeseries[-1][0]
        result = []
        for i in range(max_points):
            timestamp = latest_time - (interval * i)
            value = temp.get(timestamp, 0)
            result.append((timestamp, value))
        result.reverse()
        return result

        # fix_data = []
        # using_points = []
        # for i in range(len(timeseries)-1, 0, -1):
        #     point_current = timeseries[i]
        #     using_points.append(point_current)
        #     point_prev = timeseries[i-1]
        #     while (point_current[0] - point_prev[0]) > interval:
        #         point_current = (point_current[0] - interval, 0)
        #         fix_data.append(point_current)
        #         if len(fix_data) == (max_points-len(using_points)):
        #             break
        #     if len(fix_data) == (max_points-len(using_points)):
        #         break
        #
        # if not fix_data:
        #     return
        # using_points.extend(fix_data)
        # using_points.sort(key=lambda x: x[0])
        # del timeseries[:]
        # timeseries.extend(using_points)
        # if len(timeseries) > max_points:
        #     timeseries = timeseries[-max_points:]

    @view_config(route_name="charts")
    def charts(self):
        """
        :param category: [PROJECT/API/API-CLIENT/CLIENT]
        :param type: [TIME/VISIT]
        :return:
        """
        category = self.request.params['category']
        ctype = self.request.params['type']
        height = self.request.params.get('height', 250)

        template = None
        if ctype == 'TIME':
            template = 'templates/charts_line.html'
            result = self.chart_time(category)
        elif ctype == 'VISIT':
            template = 'templates/charts_visit.html'
            result = self.chart_visit(category)

        result = json.dumps(result)
        context = dict(series=result, category=category, ctype=ctype,
                       height=height)
        return render_to_response(template, context,
                                  request=self.request)


class WidgetExcel(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name="upload_excel")
    def upload_view(self):
        template = "templates/database_xlsupload.html"
        dbconn_id = self.request.params['dbconn_id']

        context = common_vars(self.request)
        context.update(dict(
            pagename="Excel Upload", dbconn_id=dbconn_id
        ))
        return render_to_response(template, context, request=self.request)

    @view_config(route_name="upload_rcv")
    def upload_rcv(self):
        """
        上传数据表内容
        :param
        :return:
        """
        dbconn_id = self.request.params['dbconn_id']

        file_name = self.request.POST['excel'].filename
        excel_file = self.request.POST['excel'].file
        from tap.scripts.tasks import upload_excel

        # save task
        with transaction.manager:
            task = Task(
                task_type='EXCEL', task_name=file_name,
                attachment=excel_file.read(),
                message="excel file uploaded.",
                parameters=json.dumps(dict(dbconn_id=dbconn_id))
            )
            DBSession.add(task)
            DBSession.flush()
            result = dict(id=task.id, status=200, message="")
            try:
                upload_excel.delay(task.id)
            except socket.error:
                result['status'] = 500
                result['message'] = 'backend worker not start.'
            response = Response(json.dumps(result))
            response.content_type = "application/json"
            return response

    @view_config(route_name="upload_progress")
    def upload_progress(self):
        task_id = self.request.params['task_id']
        with transaction.manager:
            task = DBSession.query(Task).get(task_id)
            result = dict(id=task.id, status=task.status, message=task.message)
            response = Response(json.dumps(result))
            response.content_type = "application/json"
            return response
