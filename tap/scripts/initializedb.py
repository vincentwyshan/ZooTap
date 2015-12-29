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
    TapPermission,
    TapUserPermission,
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

    init_permision()


def init_permision():
    """
    用户管理 (SYS_USER)
    账号管理 (SYS_CLIENT)
    数据库管理(SYS_DATABASE)
    项目管理(SYS_PROJECT)
    检查所有的项目和API，追加项目和API权限
    :return:
    """
    sys_permissions = dict(
        SYS_USER=u'用户管理', SYS_CLIENT=u'客户端管理', SYS_DATABASE=u'数据库管理',
        SYS_PROJECT=u'项目管理', SYS_INDEX=u'首页访问', )

    with transaction.manager:
        for name, desc in sys_permissions.items():
            name = unicode(name)
            add_permission(name, desc)
        projects = DBSession.query(TapProject).order_by(TapProject.id.asc())
        for project in projects:
            add_permission(project.name, u'项目:' + project.name)
            for api in project.apis:
                add_api_permission(project, api)


def add_api_permission(project, api):
    result = []
    result.append(
        add_permission('%s.%s' % (project.name, api.name), u'接口:%s' % api.name)
    )
    result.append(
        add_permission('%s.%s.%s' % (project.name, api.name, 'config'),
                       u'接口配置:%s' % api.name))
    result.append(
        add_permission('%s.%s.%s' % (project.name, api.name, 'release'),
                       u'接口发布:%s' % api.name))
    result.append(
        add_permission('%s.%s.%s' % (project.name, api.name, 'auth'),
                       u'接口授权:%s' % api.name))
    result.append(
        add_permission('%s.%s.%s' % (project.name, api.name, 'stats'),
                       u'接口统计:%s' % api.name))
    result.append(
        add_permission('%s.%s.%s' % (project.name, api.name, 'cache'),
                       u'接口缓存管理:%s' % api.name))
    return result


def add_user_permission(user, permission, view=False, edit=False,
                        add=False, delete=False):
    user_permission = TapUserPermission()
    user_permission.user_id = user.id
    user_permission.permission_id = permission.id
    user_permission.a_view = view
    user_permission.a_edit = edit
    user_permission.a_add = add
    user_permission.a_delete = delete
    DBSession.add(user_permission)


def add_permission(name, desc):
    permission = DBSession.query(TapPermission).filter_by(
        name=name).first()
    if permission:
        return
    permission = TapPermission()
    permission.name = name
    permission.description = desc
    DBSession.add(permission)
    return permission
