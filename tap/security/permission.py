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

    projectsave='SYS_PROJECT:edit',

    clientsave='SYS_CLIENT:edit',
    clientparanew='SYS_CLIENT:edit',
    clientparadelete='SYS_CLIENT:delete',
    clientrefreshtoken='SYS_CLIENT:edit',

    usersave='SYS_USER:add',
    permissionsave='SYS_USER:edit',

    # Shouldn't auth in this function
    adminsave='PASS',
    passwordchange='SYS_USER:edit'
)


def perm_check_fail(msg=None):
    if not msg:
        msg = u"你无权访问此接口"
    result = json.dumps(dict(status=403, message=msg))
    return Response(result, content_type='application/json')


def perm_check(func):
    def wraper(*kargs, **kwarg):
        self = kargs[0]
        if self.request.user.is_admin:
            return func(*kargs, **kwarg)
        params = self.request.params
        a = AuthControl(self.request)
        action = params['action']
        perm = None
        if 'conntest' == action:
            perm = 'SYS_DATABASE:view'
        elif 'connsave' == action:
            perm = 'SYS_DATABASE:edit'
        elif 'conndisplay' == action:
            perm = 'SYS_DATABASE:edit'
        elif 'projectsave' == action:
            perm = 'SYS_PROJECT:edit'
        elif 'apisave' == action:
            if 'id' in params:
                perm = '%s:edit' % a.project_name_byapi(params['id'])
            else:
                perm = '%s:add' % a.project_name(params['project_id'])
        elif 'paranew' == action:
            perm = '%s:edit' % a.project_name_byapi(params['id'])
        elif 'paradelete' == action:
            perm = '%s:edit' % a.project_name_byapi(params['api_id'])
        elif 'releasesave' == action:
            perm = '%s:add' % a.project_name_byapi(params['api_id'])
        elif 'clientsave' == action:
            perm = 'SYS_CLIENT:edit'
        elif 'clientparanew' == action:
            perm = 'SYS_CLIENT:edit'
        elif 'clientparadelete' == action:
            perm = 'SYS_CLIENT:delete'
        elif 'clientrefreshtoken' == action:
            perm = 'SYS_CLIENT:edit'
        elif 'authclientadd' == action:
            perm = '%s:add' % a.project_name_byapi(params['api_id'])
        elif 'displaytoken' == action:
            auth = DBSession.query(TapApiAuth).get(params['auth_id'])
            perm = '%s:view' % a.project_name_byapi(auth.api_id)
        elif 'displayerror' == action:
            error = DBSession.query(TapApiErrors).get(params['id'])
            perm = '%s:view' % a.project_name_byapi(error.api_id)
        elif 'usersave' == action:
            perm = 'SYS_USER:add'
        elif 'permissionsave' == action:
            perm = 'SYS_USER:edit'
        elif 'adminsave' == action:
            # Shouldn't auth in this function
            perm = 'PASS'
        elif 'passwordchange' == action:
            perm = 'SYS_USER:edit'
        elif 'cacheget' == action:
            perm = '%s:view' % a.project_name_byapi(params['api_id'])
        elif 'cachedelete' == action:
            perm = '%s:delete' % a.project_name_byapi(params['api_id'])
        elif 'cachegen' == action:
            perm = '%s:add' % a.project_name_byapi(params['api_id'])

        # Task Project
        elif 'TaskProjectCreate' == action:
            perm = 'SYS_TPROJECT:add'
        else:
            return perm_check_fail(u'没有标记接口权限')

        if perm != 'PASS':
            user_perm = a.get_userperm(perm)
            if not user_perm:
                return perm_check_fail()
            if not getattr(user_perm, 'a_%s' % perm.split(':')[1]):
                return perm_check_fail()

        return func(*kargs, **kwarg)
    return wraper

