#coding=utf8

__author__ = 'Vincent@Home'

import time
import uuid
import simplejson as json

import transaction
from pyramid.response import Response
from pyramid.view import view_config

from tap.service.exceptions import *
from tap.service.interpreter import ParaHandler
from tap.models import (
    DBSession,
    TapApiClient,
    TapApiAccessKey
)


def response_err(message, code):
    response = Response(message)
    response.status = code
    return response


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
        # access_key 不应该与 api 挂钩
        client = DBSession.query(TapApiClient).filter_by(token=token).first()
        if not client:
            raise TapAuthFail

        if client.auth_type == 'TOKEN':
            pass
        elif client.auth_type == 'CUSTOM':
            container = {}
            source = client.custom_auth.source.encode('utf8')
            paras = ParaHandler.prepare(request.params,
                                            client.custom_auth.paras)
            variables = {}
            for k, v in paras.items():
                if k in ('main', '__builtins__'):
                    continue
                variables[k] = v
            exec source in container
            container.update(variables)
            check = False
            try:
                check = container['main']()
            except BaseException as error:
                return response_err(str(error), 500)
            if check is not True:
                return response_err('Auth Failed', 403)

        key = str(uuid.uuid4())
        access_key = TapApiAccessKey()
        # access_key.api_id = auth.api_id
        # access_key.auth_id = auth.id
        access_key.client_id = client.id
        access_key.access_key = key
        access_key.access_expire = int(time.time()) + expire
        DBSession.add(access_key)

        result = dict(access_key=key, expire_time=access_key.access_expire)
        response = Response(json.dumps(result),
                            headerlist=[('Access-Control-Allow-origin', '*',)])
        response.content_type = "application/json"
        return response


def valid_key(key, config):
    """
    :param key: access_key
    :return: (bool, client_id)
    """
    if not key:
        return False, None

    if not config.auth_clients:
        return False, None

    with transaction.manager:
        for auth in config.auth_clients:
            access_key = DBSession.query(TapApiAccessKey).filter_by(
                access_key=key, client_id=auth.client_id).first()
            if not access_key:
                # return False, None
                continue

            expire = access_key.access_expire
            if expire >= time.time():
                return True, access_key.client_id
        return False, access_key.client_id
