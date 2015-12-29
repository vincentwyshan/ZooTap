#coding=utf8

import datetime
import os
from hashlib import sha256
from hmac import HMAC

from pyramid.security import Allow, Everyone, Authenticated
from pyramid.security import unauthenticated_userid, authenticated_userid
from pyramid.security import Allow, Deny

import transaction

from tap.service import exceptions
from tap.models import (
    DBSession,
    TapUser,
    TapPermission,
    TapUserPermission,
    TapProject,
    TapApi,
)


def groupfinder(user_id, request):
    if user_id:
        user = bind_user(request, user_id)
        if user:
            return [user.name]
        raise exceptions.UserNotAvailable
    return [Everyone]


class AuthControl(object):
    def __init__(self, request):
        self.request = request

    def route(self):
        """
        根据URL提供相应的权限查询
        :return:
        """
        need_permission = None
        if (self.request.path.startswith('/management/')
            and not self.request.path.startswith('/management/action')):
            need_permission = self.pages_permission(self.request.path)

        elif self.request.path.startswith('/management/action'):
            return [(Allow, Everyone, 'view'), (Allow, Everyone, 'edit'),
                    (Allow, Everyone, 'delete'), (Allow, Everyone, 'add')]
        elif self.request.path == '/':
            need_permission = 'SYS_INDEX:view'
        else:
            raise Exception("No permission route")
        user_perm = self.get_userperm(need_permission)
        result = []
        if user_perm:
            if user_perm.a_view:
                result.append((Allow, self.request.user.name, 'view'))
            if user_perm.a_add:
                result.append((Allow, self.request.user.name, 'add'))
            if user_perm.a_delete:
                result.append((Allow, self.request.user.name, 'delete'))
            if user_perm.a_edit:
                result.append((Allow, self.request.user.name, 'edit'))
        else:
            return [(Deny, Everyone, 'view'), (Deny, Everyone, 'edit'),
                    (Deny, Everyone, 'delete'), (Deny, Everyone, 'add')]
        return result

    def get_userperm(self, perm_name):
        need_permission, action = perm_name.split(':')
        permission = DBSession.query(TapPermission).filter_by(
            name=need_permission).first()
        user_perm = DBSession.query(TapUserPermission).filter_by(
            user_id=self.request.user.id, permission_id=permission.id).first()
        return user_perm

    def project_name(self, project_id):
        project = DBSession.query(TapProject).get(project_id)
        return project.name

    def api_name(self, api_id):
        api = DBSession.query(TapApi).get(api_id)
        return '%s.%s' % (api.project.name, api.name)

    def pages_permission(self, path):
        # Permission:
        result = None
        matchdict = self.request.matchdict
        params = self.request.params
        if path == '/management/database':
            result = 'SYS_DATABASE:view'
        elif path.startswith('/management/client'):
            result = 'SYS_CLIENT:view'
        elif path == '/management/user':
            result = 'SYS_USER:view'
        elif path.startswith('/management/user/edit/'):
            result = 'SYS_USER:edit'
        elif path == '/management/project':
            result = 'SYS_PROJECT:view'
        elif path.startswith('/management/project/'):
            result = '%s:view' % self.project_name(matchdict['project_id'])
        elif path.startswith('/management/api/'):
            result = '%s:view' % self.api_name(matchdict['api_id'])
        elif path.startswith('/management/api-test'):
            result = '%s:view' % self.api_name(params['id'])
        return result

    @property
    def __acl__(self):
        if not self.request.userid:
            return [(Deny, Everyone, 'view'),
                    (Deny, Everyone, 'edit'),
                    (Deny, Everyone, 'delete'),
                    ]
        if self.request.user.is_admin:
            return [(Allow, self.request.user.name, 'view'),
                    (Allow, self.request.user.name, 'edit'),
                    (Allow, self.request.user.name, 'delete'),
                    (Allow, self.request.user.name, 'access'),
                    ]
        return self.route()


class TmpContainer(object):
    @classmethod
    def load(cls, values):
        result = TmpContainer()
        for k, v in values.items():
            setattr(result, k, v)
        return result


def get_user(request):
    if not hasattr(request, 'inst_user'):
        user_id = authenticated_userid(request)
        if not user_id:
            user = unauthenticated_userid(request)
            request.inst_user = user
        else:
            bind_user(request, user_id)
    return request.inst_user


def get_user_id(request):
    user_id = authenticated_userid(request)
    return user_id


def bind_user(request, user_id):
    if hasattr(request, 'inst_user'):
        return request.inst_user

    if user_id is not None:
        with transaction.manager:
            user = DBSession.query(TapUser).get(user_id)
            if not user:
                return None
            user = [(k, getattr(user, k)) for k in user.__table__.columns.keys()]
            user = dict(user)
            user = TmpContainer.load(user)
        request.inst_user = user
    return request.inst_user


def encrypt_password(password, salt=None):
    """Hash password on the fly."""
    if salt is None:
        salt = os.urandom(8) # 64 bits.

    assert 8 == len(salt)
    assert isinstance(salt, str)

    if isinstance(password, unicode):
        password = password.encode('UTF-8')

    assert isinstance(password, str)

    result = password
    for i in xrange(10):
        result = HMAC(result, salt, sha256).digest()

    return salt + result


def valid_password(user, password):
    salt = user.password[:8]
    return encrypt_password(password, salt) == user.password
