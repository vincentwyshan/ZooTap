#coding=utf8

import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from tap.security import encrypt_password
from tap.models import (
    DBSession,
    Base,
    TapUser,
    TapProject,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    with transaction.manager:
        password = encrypt_password("capitalvue")
        user = DBSession.query(TapUser).filter_by(name=u'cada').first()
        if not user:
            user = TapUser(name=u'cada', password=password, is_admin=True)
            DBSession.add(user)
            DBSession.flush()
        project = DBSession.query(TapProject).filter_by(name=u'PROJECT0').first()
        if not project:
            project = TapProject(name=u'PROJECT0', cnname=u"测试",
                                 description=u"测试项目", uid_create=user.id)
            DBSession.add(project)
