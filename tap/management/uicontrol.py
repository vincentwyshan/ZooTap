#coding=utf8

__author__ = 'Vincent@Home'

import re

import transaction

from tap.common.character import _, _t
from tap.models import (
    DBSession,
    TapProject,
    TapApi,
    TapDBConn,
    TapApiClient,
    TapUser,
)


def gen_breadcrumbs(request):
    result = []

    trans_db = _t(request, _(u'数据库'))
    trans_project = _t(request, _(u'项目'))
    trans_client = _t(request, _(u'客户端'))
    trans_userlist = _t(request, _(u'用户列表'))
    trans_index = _t(request, _(u'首页'))

    if request.path.startswith('/management/database'):
        result.append(
            {"url": '/management/database', "class": "active", "text": trans_db}
        )
        if request.matchdict.get('dbconn_id') is not None:
            with transaction.manager:
                dbconn_id = request.matchdict['dbconn_id']
                dbconn = DBSession.query(TapDBConn).get(dbconn_id)
                result.append(
                    {"class": "active", "text": dbconn.name}
                )
    elif request.path == '/management/project':
        result.append(
            {"url": '/management/project', "class": "active", "text": trans_project}
        )
    elif re.match(ur"/management/project/\d+", request.path):
        project_id = re.findall(r'\d+', request.path)[0]
        with transaction.manager:
            project = DBSession.query(TapProject).get(project_id)
            result.append(
                {"url": '/management/project', "class": "", "text": trans_project},
            )
            result.append(
                {"class": "active", "text": project.fullname},
            )
    elif re.match(ur"/management/api/\d+", request.path):
        api_id = re.findall(r'\d+', request.path)[0]
        with transaction.manager:
            api = DBSession.query(TapApi).get(api_id)
            result.append(
                {"url": '/management/project', "class": "", "text": trans_project},
            )
            result.append(
                {"url": '/management/project/%s' % api.project.id,
                 "class": "",  "text": api.project.fullname},
            )
            result.append(
                {"class": "active", "text": api.fullname}
            )
    elif re.match(ur"/management/client", request.path):

        if 'client_id' in request.matchdict:
            with transaction.manager:
                client_id = request.matchdict['client_id']
                client = DBSession.query(TapApiClient).get(client_id)
                result.append(
                    {"url": '/management/client', "text": trans_client}
                )
                result.append(
                    {"class": 'active', "text": client.name}
                )
        else:
            result.append(
                {"url": '/management/client', 'class': "active",
                 "text": trans_client}
            )
    elif re.match(ur"/management/user/", request.path):
        result.append(
            {"url": '/management/user/list', "text": trans_userlist}
        )
        if 'user_id' in request.matchdict:
            with transaction.manager:
                user_id = request.matchdict['user_id']
                user = DBSession.query(TapUser).get(user_id)
                result.append(
                    {"class": 'active', 'text': user.name}
                )
    else:
        result.append(
            {"url": '/', 'class': 'active', "text": trans_index}
        )
    return result


def gen_active(request):
    result = dict()
    if request.path.startswith('/management/database'):
        result['active_database'] = True
    elif request.path.startswith('/management/project'):
        result['active_project'] = True
        try:
            result['current_project_id'] = int(request.matchdict['project_id'])
        except:
            pass
    elif request.path.startswith('/management/api'):
        result['active_project'] = True
        api_id = int(request.matchdict['api_id'])
        with transaction.manager:
            try:
                api = DBSession.query(TapApi).get(api_id)
                result['current_project_id'] = api.project.id
            except:
                pass
    elif request.path == '/':
        result['active_home'] = True
    elif request.path.startswith('/management/client'):
        result['active_client'] = True
    elif request.path.startswith('/management/user'):
        result['active_users'] = True
    elif request.path.startswith('/management/docs'):
        result['active_docs'] = True
    return result


def gen_project_names(request):
    result = []
    with transaction.manager:
        projects = DBSession.query(TapProject).order_by(TapProject.id.desc())
        for project in projects:
            result.append(
                dict(id=project.id, name=project.fullname)
            )
        return result
