#coding=utf8
"""
Permission check for Actions
"""

import simplejson as json

from pyramid.response import Response

from tap.security.auth import AuthControl


PERM_DICT = dict(
    conntest='SYS_DATABASE:view',
    connsave='SYS_DATABASE:edit',
    conndisplay='SYS_DATABASE:edit',

    # API
    projectsave='SYS_PROJECT:edit',
    apiSave='%(aproject_name)s:edit',
    apiCreate='%(aproject_name)s:add',
    paranew='%(aproject_name)s:edit',
    paradelete='%(aproject_name)s:edit',
    releasesave='%(aproject_name)s:add',
    authclientadd='%(aproject_name)s:add',
    displaytoken='%(aproject_name)s:view',
    displayerror='%(aproject_name)s:view',
    cacheget='%(aproject_name)s:view',
    cachedelete='%(aproject_name)s:delete',
    cachegen='%(aproject_name)s:add',

    # CLIENT
    clientsave='SYS_CLIENT:edit',
    clientparanew='SYS_CLIENT:edit',
    clientparadelete='SYS_CLIENT:delete',
    clientrefreshtoken='SYS_CLIENT:edit',

    # USER
    usersave='SYS_USER:add',
    permissionsave='SYS_USER:edit',
    # Shouldn't auth in this function
    adminsave='PASS',
    passwordchange='SYS_USER:edit',
)


def perm_check_fail(msg=None):
    if not msg:
        msg = u"你无权访问此接口"
    result = json.dumps(dict(status=403, message=msg))
    return Response(result, content_type='application/json')


def perm_check(func):
    def wrapper(*kargs, **kwarg):
        self = kargs[0]

        # super user
        if self.request.user.is_admin:
            return func(*kargs, **kwarg)

        params = self.request.params
        a = AuthControl(self.request)
        action = params['action']
        perm_str = PERM_DICT.get(action)
        if not perm_str:
            return perm_check_fail(u'没有标记接口权限')

        perm = None
        if '%(aproject_name)' in perm_str:
            project_name = None
            if 'project_id' in params:
                project_name = a.api_project_name(params['project_id'])
            elif 'api_id' in params:
                project_name = a.api_project_name_byapi(params['api_id'])
            elif 'auth_id' in params:
                project_name = a.api_project_name_byauth(params['auth_id'])
            perm = perm_str % project_name

        if perm != 'PASS':
            user_perm = a.get_userperm(perm)
            if not user_perm:
                return perm_check_fail()
            if not getattr(user_perm, 'a_%s' % perm.split(':')[1]):
                return perm_check_fail()

        return func(*kargs, **kwarg)
    return wrapper

