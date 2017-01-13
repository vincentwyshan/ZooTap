#coding=utf8

from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from tap.models import (
    DBSession,
    Base,
)


globalsettings = None
AUTH_FACTORY = "tap.security.auth.AuthControl"

ROUTES = [
    ('home', '/', AUTH_FACTORY),
    ('language', '/management/language', AUTH_FACTORY),
    ('login', '/management/login'),
    ('logout', '/management/logout'),
    ('database', '/management/database', AUTH_FACTORY),
    ('database_view', '/management/database/{dbconn_id}', AUTH_FACTORY),
    ('database_execute', '/management/database/{dbconn_id}/execute', AUTH_FACTORY),
    ('api_action', '/management/action', AUTH_FACTORY),
    ('task_action', '/management/task-action', AUTH_FACTORY),
    ('project', '/management/project', AUTH_FACTORY),
    ('project_detail', '/management/project/{project_id}', AUTH_FACTORY),
    ('api_config', '/management/api/{api_id}', AUTH_FACTORY),
    ('api_release', '/management/api/{api_id}/release', AUTH_FACTORY),
    ('api_release_version', '/management/api/{api_id}/release/{release_id}', AUTH_FACTORY),

    ('api_stats', '/management/api/{api_id}/stats', AUTH_FACTORY),
    ("api_cachemanage", "/management/api/{api_id}/cachemanage", AUTH_FACTORY),
    ('api_test', '/management/api-test', AUTH_FACTORY),
    ("client_home", "/management/client", AUTH_FACTORY),
    ("client_detail", "/management/client/{client_id}", AUTH_FACTORY),

    # ("client_accesskeys",
    #                  "/management/client/{client_id}/access-keys",
    #                  AUTH_FACTORY),

    ("auth_home", "/management/api/{api_id}/auth", AUTH_FACTORY),
    ("user_list", "/management/user/list", AUTH_FACTORY),
    ("user_edit", "/management/user/edit/{user_id}", AUTH_FACTORY),
    ("charts", "/management/charts"),

    # TODO 未设置权限 Upload excel
    ("upload_excel", "/management/tools/upload-excel"),
    ("upload_rcv", "/management/tools/upload-file"),
    ("upload_progress", "/management/tools/upload-progress"),

    # Tasks
    ("task_project_index", "/management/task"),
    ("task_project_hosts", "/management/task/host"),
    ("task_host_detail", "/management/task/host/{host_id}"),
    ("task_project_detail", "/management/task/{project_id}"),
]


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    global globalsettings
    globalsettings = settings

    engine = engine_from_config(settings, 'sqlalchemy.', pool_recycle=1800)
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    from tap.security.auth import groupfinder, get_user, get_user_id
    from tap.common.character import _t

    # Attach shortcut property
    config.add_request_method(get_user, 'user', reify=True)
    config.add_request_method(get_user_id, 'userid', reify=True)
    config.add_request_method(_t, '_')

    # Template
    config.include('pyramid_mako')
    config.add_mako_renderer('.html')

    # Security policies
    authn_policy = AuthTktAuthenticationPolicy(
        settings['tap.secret'], callback=groupfinder, hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    add_route(config)
    add_srv_route(config)

    config.scan()
    return config.make_wsgi_app()


def add_route(config):
    config.add_translation_dirs("tap:locale")

    # config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('static', 'static', cache_max_age=0)

    def _add_route(cfg):
        if len(cfg) == 2:
            config.add_route(*cfg)
        elif len(cfg) == 3:
            config.add_route(*cfg[:2], factory=cfg[2])
        else:
            raise NotImplemented

    for cfg in ROUTES:
        _add_route(cfg)


def add_srv_route(config):
    config.add_route('authorize', '/api/authorize')
    config.add_route('api_run', '/api/{project_name}/{api_name}')
    config.add_route('api_run_v', '/api/{project_name}/{api_name}/v{version}')
    config.add_route('captcha_request', '/captcha/request')
    config.add_route('captcha_image', '/captcha/image')
    config.add_route('captcha_validate', '/captcha/validate')


def main_service(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    add_srv_route(config)

    config.scan()
    return config.make_wsgi_app()


