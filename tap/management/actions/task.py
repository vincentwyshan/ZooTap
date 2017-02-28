#coding=utf8

import re
import uuid

from pyramid.view import view_config
from pyramid.response import Response
import transaction
import simplejson as json

from tap.security.auth import encrypt_password
from tap.security.permission import perm_check
from tap.service.cache import cache_get, cache_delete
from tap.service.api import Program
from tap.service.common import (
    conn_get, api2dict, TapEncoder, dbconn_ratio_parse, dict2api
)



class TaskActions(object):
    def __init__(self, request):
        self.request = request

    @perm_check
    @view_config(route_name='task_action', permission="edit")
    def route(self):
        result = dict(success=0, message=u"没有任何操作可执行!")
        action = self.request.params.get('action')

        return Response(json.dumps(result, cls=TapEncoder),
                        content_type='application/json')


