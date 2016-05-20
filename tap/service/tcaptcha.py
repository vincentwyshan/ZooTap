#coding=utf8
__author__ = 'Vincent'

import os
import random
import datetime
import transaction

import simplejson as json
from pyramid.response import Response
from pyramid.httpexceptions import HTTPNotFound
from pyramid.view import view_config
from captcha.image import ImageCaptcha

from tap.models import DBSession, CaptchaCode


chars = map(chr, range(65, 91) + range(97, 123))
# remove the confusion characters
chars.remove('I')
chars.remove('i')
chars.remove('L')
chars.remove('l')
chars.remove('o')
chars.remove('O')
abs_path = os.path.abspath(os.path.dirname(__file__))
ttf_path = os.path.join(abs_path, 'OpenSans-Light.ttf')


def gen_captcha():
    with transaction.manager:
        code = random.sample(chars, 5)
        captcha = CaptchaCode()
        captcha.code = unicode(''.join(code))
        DBSession.add(captcha)
        DBSession.flush()
        assert captcha.id is not None
        return captcha.id


@view_config(route_name='captcha_request')
def request_captcha(request):
    result = dict(result=str(gen_captcha()))
    return Response(json.dumps(result))


@view_config(route_name='captcha_image')
def request_img(request):
    captcha_id = request.params['id']
    if not captcha_id:
        return HTTPNotFound('Not Found Resource')
    with transaction.manager:
        captcha = DBSession.query(CaptchaCode).get(captcha_id)
        if not captcha:
            return HTTPNotFound('Not Found Resource')

        image = ImageCaptcha(fonts=[ttf_path], font_sizes=(48, 49, 50), width=130)
        image_data = image.generate(captcha.code)
        response = Response(image_data.read())
        response.content_type = "image/jpeg"
        return response


def validate(captcha_id, code):
    with transaction.manager:
        captcha = DBSession.query(CaptchaCode).get(captcha_id)
        if not captcha:
            return False
        # 大约有 1% 的概率，执行清除一天前的旧数据任务
        if random.random() < 0.01:
            today = datetime.date.today()
            today = datetime.datetime(today.year, today.month, today.day)
            DBSession.query(CaptchaCode).filter(
                CaptchaCode.created<today).delete()
        return captcha.code.lower() == code.lower()


@view_config(route_name='captcha_validate')
def request_validate(request):
    captcha_id = request.params['id']
    code = request.params['code']
    result = validate(captcha_id, code)
    result = dict(result=int(result))
    return Response(json.dumps(result))
