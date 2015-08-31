#coding=utf8

__author__ = 'Vincent@HOME'


import sys

from paste.deploy import loadapp
from pyramid.scripts.common import parse_vars
from pyramid.paster import ( get_appsettings, setup_logging, )
from sqlalchemy import engine_from_config

from tap.models import (DBSession, Base)


def init_session_from_cmd():
    config_uri = sys.argv[1]
    options = parse_vars(sys.argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)


def init_all():
    config_uri = sys.argv[1]
    loadapp("config:%s" % config_uri)
