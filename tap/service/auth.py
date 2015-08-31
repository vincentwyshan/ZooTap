#coding=utf8

__author__ = 'Vincent@Home'

import time
import uuid
import simplejson as json

import transaction
from pyramid.response import Response
from pyramid.view import view_config

from tap.service.exceptions import *
from tap.models import (
    DBSession,
    TapApiAuth,
    TapApiAccessKey
)


@view_config(route_name="authorize")
def require_key(request):
    """
    :param request: token[token string], expire[expire time int]
    :return: access_key, expire_time
    """
    token = request.params['token']
    expire = int(request.params.get('expire', 600))
    if expire < 600:
        expire = 600
    with transaction.manager:
        auth = DBSession.query(TapApiAuth).filter_by(token=token).first()
        if not auth:
            raise TapAuthFail

        key = str(uuid.uuid4())
        access_key = TapApiAccessKey()
        access_key.api_id = auth.api_id
        access_key.auth_id = auth.id
        access_key.client_id = auth.client_id
        access_key.access_key = key
        access_key.access_expire = int(time.time()) + expire
        DBSession.add(access_key)

        result = dict(access_key=key, expire_time=access_key.access_expire)
        return Response(json.dumps(result))


def valid_key(key):
    """
    :param key: access_key
    :return: (bool, client_id)
    """
    if not key:
        return False, None

    with transaction.manager:
        access_key = DBSession.query(TapApiAccessKey).filter_by(
            access_key=key).first()
        if not access_key:
            return False, None

        expire = access_key.access_expire
        if expire >= time.time():
            return True, access_key.client_id
        return False, access_key.client_id
