#coding=utf8

from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.security import remember, forget
from pyramid.httpexceptions import HTTPFound, HTTPNotFound

import transaction

from tap.common.character import _
from tap.management.uicontrol import universal_vars
from tap.models import DBSession
from tap.modelstask import (
    TapTaskProject, TapTask
)


class TaskViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name="task_project_index")
    def upload_view(self):
        with transaction.manager:
            projects = DBSession.query(TapTaskProject)\
                .order_by(TapTaskProject.id.desc())
            pagename = self.request.localizer.translate(_(u'Task - Projects'))
            context = dict(pagename=pagename, projects=projects)
            context.update(universal_vars(self.request))
            return render_to_response('tap:templates/task/projectlist.html',
                                      context, request=self.request)

