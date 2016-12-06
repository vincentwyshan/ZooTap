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


class Breadcrumbs(object):
    def __init__(self, request):
        self.request = request
        self.trans_db = _t(request, _(u'数据库'))
        self.trans_project = _t(request, _(u'项目'))
        self.trans_client = _t(request, _(u'客户端'))
        self.trans_userlist = _t(request, _(u'用户列表'))
        self.trans_index = _t(request, _(u'首页'))

    def database(self):
        if not self.request.path.startswith('/management/database'):
            return

        result = [(
            {"url": '/management/database', "class": "active",
             "text": self.trans_db}
        )]
        if self.request.matchdict.get('dbconn_id') is not None:
            with transaction.manager:
                dbconn_id = self.request.matchdict['dbconn_id']
                dbconn = DBSession.query(TapDBConn).get(dbconn_id)
                result.append(
                    {"class": "active", "text": dbconn.name}
                )
        return result

    def project_list(self):
        if self.request.path != '/management/project':
            return
        return [(
            {"url": '/management/project', "class": "active",
             "text": self.trans_project}
        )]

    def project_detail(self):
        if not re.match(ur"/management/project/\d+", self.request.path):
            return

        project_id = re.findall(r'\d+', self.request.path)[0]
        result = []
        with transaction.manager:
            project = DBSession.query(TapProject).get(project_id)
            result.append(
                {"url": '/management/project', "class": "",
                 "text": self.trans_project},
            )
            result.append(
                {"class": "active", "text": project.fullname},
            )
        return result

    def api(self):
        if not re.match(ur"/management/api/\d+", self.request.path):
            return

        api_id = re.findall(r'\d+', self.request.path)[0]
        result = []
        with transaction.manager:
            api = DBSession.query(TapApi).get(api_id)
            self.result.append(
                {"url": '/management/project', "class": "",
                 "text": self.trans_project},
            )
            self.result.append(
                {"url": '/management/project/%s' % api.project.id,
                 "class": "",  "text": api.project.fullname},
            )
            self.result.append(
                {"class": "active", "text": api.fullname}
            )
        return result

    def client(self):
        if not re.match(ur"/management/client", self.request.path):
            return

        result = []
        if 'client_id' in self.request.matchdict:
            with transaction.manager:
                client_id = self.request.matchdict['client_id']
                client = DBSession.query(TapApiClient).get(client_id)
                result.append(
                    {"url": '/management/client', "text": self.trans_client}
                )
                result.append(
                    {"class": 'active', "text": client.name}
                )
        else:
            result.append(
                {"url": '/management/client', 'class': "active",
                 "text": self.trans_client}
            )
        return result

    def user(self):
        if not re.match(ur"/management/user/", self.request.path):
            return
        result = [(
            {"url": '/management/user/list', "text": self.trans_userlist}
        )]
        if 'user_id' in self.request.matchdict:
            with transaction.manager:
                user_id = self.request.matchdict['user_id']
                user = DBSession.query(TapUser).get(user_id)
                result.append(
                    {"class": 'active', 'text': user.name}
                )
        return result

    def task_project(self):
        if not re.match(ur"/management/task", self.request.path):
            return
        return [
            {"class": "active", "text": self.trans_project}
        ]

    def result(self):
        data = (
            self.database() or self.project_list() or
            self.project_detail() or self.api() or self.client() or
            self.user()
        )
        if not data:
            data = [{"url": '/', 'class': 'active', "text": self.trans_project}]
        return data


def gen_breadcrumbs(request):
    return Breadcrumbs(request).result()


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


def universal_vars(request):
    top_breadcrumbs = gen_breadcrumbs(request)
    project_names = gen_project_names(request)
    result = dict(
        top_breadcrumbs=top_breadcrumbs,
        project_names=project_names
    )
    result.update(gen_active(request))
    return result

