# coding=utf8

from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.security import remember, forget
from pyramid.httpexceptions import HTTPFound, HTTPNotFound

import transaction

from tap.common.character import _, _t
from tap.management.uicontrol import universal_vars
from tap.models import DBSession
from tap.modelstask import (
    TapTaskProject, TapTask, TapTaskHost
)


class TaskViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name="task_project_index")
    def project_list(self):
        with transaction.manager:
            projects = DBSession.query(TapTaskProject)\
                .order_by(TapTaskProject.id.desc())
            pagename = _t(self.request, _(u'Task - Project list'))
            context = dict(pagename=pagename, projects=projects)
            context.update(universal_vars(self.request))
            return render_to_response('tap:templates/task/projectlist.html',
                                      context, request=self.request)

    @view_config(route_name="task_project_hosts")
    def host_list(self):
        with transaction.manager:
            hosts = DBSession.query(TapTaskHost).order_by(TapTaskHost.id.desc())
            pagename = _t(self.request, _(u'Task - Host list '))
            context = dict(pagename=pagename, hosts=hosts)
            context.update(universal_vars(self.request))
            return render_to_response("tap:templates/task/hostlist.html",
                                      context, request=self.request)

    @view_config(route_name="task_host_detail")
    def host_detail(self):
        with transaction.manager:
            context = dict(pagename="host")
            context.update(universal_vars(self.request))
            return render_to_response("tap:templates/task/hostdetail.html",
                                      context, request=self.request)

    @view_config(route_name="task_project_detail")
    def project_detail(self):
        with transaction.manager:
            context = dict(pagename="host")
            context.update(universal_vars(self.request))
            return render_to_response("tap:templates/task/projectdetail.html",
                                      context, request=self.request)

