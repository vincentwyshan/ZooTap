#coding=utf8

import datetime
import os
from hashlib import sha256
from hmac import HMAC

from pyramid.security import Allow, Everyone, Authenticated
from pyramid.security import unauthenticated_userid, authenticated_userid
from pyramid.security import Allow, Deny

import transaction

from tap.models import (
    DBSession,
    TapUser,
)


def groupfinder(user_id, request):
    if user_id:
        return [bind_user(request, user_id).name]
    return [Everyone]


class AuthControl(object):
    def __init__(self, request):
        self.request = request

    @property
    def __acl__(self):
        if not self.request.userid:
            return [(Deny, Everyone, 'view'),
                    (Deny, Everyone, 'edit'),
                    (Deny, Everyone, 'delete'),
                    ]
        result = [(Allow, self.request.user.name, 'view'),
                  (Allow, self.request.user.name, 'edit'),
                  (Allow, self.request.user.name, 'delete'),
                  ]
        return result


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
                return
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
