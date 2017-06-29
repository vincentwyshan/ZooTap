# coding=utf8
"""
Data dump/import
    format: pickle
    size: max_size shouldn't exceed memory size
    
Warning:
    dump/import for the purpose of always changing API configuration in dev environment, 
    prod environment keep syncing with dev environment. If make any modification in prod
    environment, the dump/import process may not work.
"""

import os
import sys
import json
import time
import cPickle
import datetime
from optparse import OptionParser

import transaction
from sqlalchemy import engine_from_config
from dateutil import parser

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )


from tap.service.common import dict2api, api2dict, TapEncoder
from tap.models import (
    DBSession,
    Base,
    TapDBConn,
    TapApiRelease
)

import tap.models as m
# In the order of model dependency
DATAMODELS = [m.TapUser, m.TapPermission, m.TapUserPermission, m.TapDBConn,
              m.TapProject, m.TapApi, m.api_db, m.api_dbsecondary,
              m.TapParameter, m.TapSource, m.TapApiConfig, m.TapApiRelease,
              m.TapApiClient, m.TapApiAuth, m.TapApiAccessKey, ]
# m.TapApiStats, m.TapApiErrors]


def get_model(table_name):
    for md in DATAMODELS:
        if hasattr(md, '__table__'):
            md = md.__table__
        if md.name == table_name:
            return md
    return None


def initdb():
    config_uri = sys.argv[1]
    # options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)


def tap_dump():
    usage = "usage: %prog production.ini [options]"
    _parser = OptionParser(usage=usage)
    _parser.add_option('-p', type="string", dest="path",
                       default="/tmp/tapdump.pkl",
                       help="dump file path, default: /tmp/tapdump.pkl")
    (options, args) = _parser.parse_args()
    initdb()

    _dump(options.path)
    print 'Dump done:', options.path


def _dump(path):
    """
    :return: [[table_name, column_names, data_instances...]...]
    """
    data = []
    with transaction.manager:
        for md in DATAMODELS:
            table_data = []
            data.append(table_data)
            if hasattr(md, '__table__'):
                md = md.__table__
            columns = md.columns.keys()
            table_data.append(md.name)
            table_data.append(columns)
            for row in DBSession.query(md):
                instance = {}
                for c in columns:
                    instance[c] = getattr(row, c)
                table_data.append(instance)
    f = open(path, 'wb')
    cPickle.dump(data, f)
    f.close()


def tap_import():
    usage = "usage: %prog production.ini [options]"
    _parser = OptionParser(usage=usage)
    _parser.add_option('-p', type="string", dest="path",
                       default="/tmp/tapdump.pkl",
                       help="import file path, default: /tmp/tapdump.pkl")
    (options, args) = _parser.parse_args()
    initdb()

    path = options.path

    # Backup first
    path_bak = os.path.join(os.path.dirname(path), "backup-%s" % time.time())
    _dump(path_bak)

    with transaction.manager:
        _import(path)
    print 'Import done:', options.path


def _import(path):
    f = open(path, 'rb')
    data = cPickle.load(f)
    # TODO oracle sequence 没有同步 可能导致重复出现违反唯一索引错误
    # TODO 如果已经定义了业务唯一键的 model, 修改为按照业务唯一键确定唯一性
    for table_data in data:
        md = get_model(table_data[0])
        columns = table_data[1]
        for row in table_data[2:]:
            # Unique check
            chk_cols = ["id"]
            if 'id' not in columns:
                chk_cols = columns

            exists = DBSession.query(md)
            for c in chk_cols:
                exists = eval("exists.filter_by(%s=row[c])" % c)
            exists = exists.first()
            if exists and md.name == 'tap_dbconn':
                continue

            # Start import
            if hasattr(md, '__table__'):
                md = md.__table__

            if not exists:
                insert = md.insert().values(row)
                DBSession.bind.execute(insert)
            else:
                _id = None
                for k, v in row.items():
                    if k.lower() == 'id':
                        _id = row.pop(k)
                update = md.update().values(row)
                for col in chk_cols:
                    if col.lower() == 'id':
                        update = update.where(getattr(md.c, col)==_id)
                    else:
                        update = update.where(getattr(md.c, col)==row[col])
                DBSession.bind.execute(update)


def check_dbconn():
    """
    check dbconn updated status when WSGI app start
    :return:
    """
    initdb()
    connections = DBSession.query(TapDBConn)
    connections = [(conn.id, conn) for conn in connections]
    connections = dict(connections)

    releases = DBSession.query(TapApiRelease.id)
    releases = [r.id for r in releases]
    for release_id in releases:
        with transaction.manager:
            release = DBSession.query(TapApiRelease).get(release_id)
            config = json.loads(release.content)
            config = dict2api(config)
            need_update = False
            for conn in config.dbconn:
                timestamp = parser.parse(conn.timestamp)
                assert isinstance(timestamp, datetime.datetime)
                if timestamp < connections[conn.id].timestamp:
                    need_update = True
                    break
            for conn in config.dbconn_secondary:
                timestamp = parser.parse(conn.timestamp)
                assert isinstance(timestamp, datetime.datetime)
                if timestamp < connections[conn.id].timestamp:
                    need_update = True
                    break
            if need_update:
                print 'DB connection update:', config.name
                dbconn = config.dbconn
                config.dbconn = [connections[conn.id] for conn in dbconn]
                dbconn_secondary = config.dbconn_secondary
                config.dbconn_secondary = [connections[c.id] for c in dbconn_secondary]
                config = api2dict(config)
                release.content = json.dumps(config, cls=TapEncoder)
