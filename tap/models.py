#coding=utf8

import datetime

from sqlalchemy.orm import relationship, backref
from sqlalchemy import (
    Column, Index, Integer, BigInteger, Unicode, UnicodeText, Boolean,
    ForeignKey, Enum, DateTime, LargeBinary, Float, Table, Sequence
)

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()



class TapUser(Base):
    __tablename__ = 'tap_user'
    id = Column(Integer, Sequence('seq_tapuser_id'), primary_key=True)
    name = Column(Unicode(60), nullable=False)
    password = Column(LargeBinary)
    full_name = Column(Unicode(60))
    description = Column(UnicodeText)
    is_admin = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_user_name', TapUser.name, unique=True)


class TapPermission(Base):
    __tablename__ = 'tap_permission'
    id = Column(Integer,Sequence('seq_tappermission_id'),  primary_key=True)
    name = Column(Unicode(60), unique=True, nullable=False)
    description = Column(UnicodeText)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)


class TapUserPermission(Base):
    __tablename__ = 'tap_userpermission'
    id = Column(Integer, Sequence('seq_tapuserpermission_id'), primary_key=True)
    user_id = Column(Integer)
    permission_id = Column(Integer, ForeignKey('tap_permission.id'))
    a_view = Column(Boolean, default=False)
    a_add = Column(Boolean, default=False)
    a_edit = Column(Boolean, default=False)
    a_delete = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_userpermission_uidpid', TapUserPermission.user_id, TapUserPermission.permission_id, unique=True)


class TapDBConn(Base):
    __tablename__ = 'tap_dbconn'
    id = Column(Integer, Sequence('seq_tapdbconn_id'), primary_key=True)
    name = Column(Unicode(60), unique=True, nullable=False)
    dbtype = Column(Enum('ORACLE', 'MSSQL', 'MYSQL', 'PGSQL', name="db_type",
                         convert_unicode=True), nullable=False)
    connstring = Column(UnicodeText)
    description = Column(UnicodeText)
    options = Column(UnicodeText)
    uid_create = Column(Integer, ForeignKey('tap_user.id'))
    user_create = relationship('TapUser', backref='dbconns')
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_dbconn_uid_create', TapDBConn.uid_create)


class TapProject(Base):
    __tablename__ = 'tap_project'
    id = Column(Integer, Sequence('seq_tapproject_id'), primary_key=True)
    name = Column(Unicode(30), nullable=False)
    cnname = Column(Unicode(60))
    description = Column(UnicodeText)
    uid_create = Column(Integer, ForeignKey('tap_user.id'))
    user_create = relationship('TapUser', backref='projects_created', foreign_keys=[uid_create])
    uid_owner = Column(Integer, ForeignKey('tap_user.id'))
    user_owner = relationship('TapUser', backref='projects_owned', foreign_keys=[uid_owner])
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_project_name', TapProject.name, unique=True)
Index('tap_project_uid_create', TapProject.uid_create)
Index('tap_project_uid_owner', TapProject.uid_owner)


api_db = Table('tap_apidb', Base.metadata,
    Column('api_id', Integer, ForeignKey('tap_api.id')),
    Column('dbconn_id', Integer, ForeignKey('tap_dbconn.id')),
    Index('idx_tap_apidb_rel_api_id', 'api_id'),
    Index('idx_tap_apidb_rel_dbconn_id', 'dbconn_id')
)

api_dbsecondary = Table('tap_apidbsecondary', Base.metadata,
    Column('api_id', Integer, ForeignKey('tap_api.id')),
    Column('dbconn_id', Integer, ForeignKey('tap_dbconn.id')),
    Index('idx_tap_apidbsec_api_id', 'api_id'),
    Index('idx_tap_apidbsec_dbconn_id', 'dbconn_id')
)

class TapApi(Base):
    __tablename__ = 'tap_api'
    id = Column(Integer, Sequence('seq_tapapi_id'), primary_key=True)
    name = Column(Unicode(30), Sequence('seq_tapapi_id'), nullable=False)
    cnname = Column(Unicode(60))
    description = Column(UnicodeText)

    dbconn = relationship('TapDBConn', secondary=api_db,
                          backref=backref('apis'))
    dbconn_order = Column(Unicode(300))
    dbconn_secondary = relationship('TapDBConn', secondary=api_dbsecondary,
                                    backref=backref('apis_secondary'))
    dbconn_secondary_order = Column(Unicode(300))
    dbconn_ratio = Column(Unicode(300), default=u'')

    cache_time = Column(Integer, default=0)
    cache_persistencedb_id = Column(Integer, ForeignKey('tap_dbconn.id'))
    cache_persistencedb = relationship('TapDBConn')

    writable = Column(Boolean, default=False)
    auth_type = Column(Enum('OPEN', 'AUTH', name="auth_type",
                            convert_unicode=True), default='OPEN')
    uid_create = Column(Integer, ForeignKey('tap_user.id'))
    user_create = relationship('TapUser', backref='apis_created', foreign_keys=[uid_create])
    uid_update = Column(Integer, ForeignKey('tap_user.id'))
    user_update = relationship('TapUser', backref='apis_updated', foreign_keys=[uid_update])
    project_id = Column(Integer, ForeignKey('tap_project.id'))
    project = relationship('TapProject', backref='apis', foreign_keys=[project_id])
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)

    status = Column(Enum('EDIT', 'RELEASE', name="editstatus_type",
                         convert_unicode=True), default='EDIT')

    def get_dbconn(self):
        if not self.dbconn:
            return []

        order = [int(o) for o in self.dbconn_order.split(',')]
        dbconn = dict([(db.id, db) for db in self.dbconn])
        return [dbconn[o] for o in order]

    def get_dbconn_secondary(self):
        if not self.dbconn_secondary:
            return []

        order = [int(o) for o in self.dbconn_secondary_order.split(',')]
        dbconn = dict([(db.id, db) for db in self.dbconn_secondary])
        return [dbconn[o] for o in order]


Index('tap_api_projectid_name', TapApi.project_id, TapApi.name, unique=True)
Index('tap_api_name', TapApi.name)
Index('tap_uid_create', TapApi.uid_create)
Index('tap_uid_update', TapApi.uid_update)


class TapParameter(Base):
    __tablename__ = 'tap_parameter'
    id = Column(Integer, Sequence('seq_tapparameter_id'), primary_key=True)
    api_id = Column(Integer, ForeignKey('tap_api.id'))
    api = relationship('TapApi', backref='paras')
    name = Column(Unicode(30), nullable=False)
    val_type = Column(Enum('TEXT', 'INT', 'DECIMAL', 'DATE', name="val_type",
                           convert_unicode=True), default=u'TEXT')
    default = Column(UnicodeText, default=u"")
    absent_type = Column(Enum('NECESSARY', 'OPTIONAL', name="absent_type",
                              convert_unicode=True), default=u"NECESSARY")
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_parameter_apiid', TapParameter.api_id)


class TapSource(Base):
    __tablename__ = 'tap_source'
    id = Column(Integer, Sequence('seq_tapsource_id'), primary_key=True)
    api_id = Column(Integer, ForeignKey('tap_api.id'))
    api = relationship('TapApi', backref=backref('source', uselist=False))
    source = Column(UnicodeText, default=u"")
    source_type = Column(Enum('SQL', 'PYTHON', name="source_type",
                              convert_unicode=True), default=u"SQL")
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_source_apiid', TapSource.api_id)


class TapApiConfig(Base):
    __tablename__ = 'tap_apiconfig'
    id = Column(Integer, Sequence('seq_tapapiconfig_id'), primary_key=True)
    api_id = Column(Integer, ForeignKey('tap_api.id'))
    api = relationship('TapApi', backref='config')
    name = Column(Unicode(30), nullable=False)
    value = Column(UnicodeText)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_apiconfig_apiid', TapApiConfig.api_id)


class TapApiRelease(Base):
    __tablename__ = 'tap_apirelease'
    id = Column(Integer, Sequence('seq_tapapirelease_id'), primary_key=True)
    api_id = Column(Integer, ForeignKey('tap_api.id'))
    api = relationship('TapApi', backref='releases')
    project_name = Column(Unicode(30), nullable=False)
    api_name = Column(Unicode(30), nullable=False)
    # dbconn_id = Column(Integer, ForeignKey('tap_dbconn.id'))
    # dbconn = relationship('TapDBConn')
    version = Column(Integer, nullable=False) 
    content = Column(LargeBinary)
    notes = Column(UnicodeText, default=u"")
    uid_release = Column(Integer, ForeignKey('tap_user.id'))
    user_release = relationship('TapUser', backref='releases')
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_apirelease_apiid', TapApiRelease.api_id, TapApiRelease.version, unique=True)
Index('tap_apirelease_userid', TapApiRelease.uid_release)
Index('tap_apirelease_paname_version', TapApiRelease.project_name,
      TapApiRelease.api_name, TapApiRelease.version, unique=True)


class TapApiClient(Base):
    __tablename__ = 'tap_apiclient'
    id = Column(Integer, Sequence('seq_tapapiclient_id'), primary_key=True)
    name = Column(Unicode(30), nullable=False)
    description = Column(UnicodeText, default=u'')
    token = Column(Unicode(38), nullable=False)
    uid_create = Column(Integer, ForeignKey('tap_user.id'))
    user_create = relationship('TapUser', backref='clients')
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_apiclient_name', TapApiClient.name, unique=True)
Index('tap_apiclient_uidcreate', TapApiClient.uid_create)


class TapApiAuth(Base):
    __tablename__ = 'tap_apiauth'
    id = Column(Integer, Sequence('seq_tapapiauth_id'), primary_key=True)
    api_id = Column(Integer, ForeignKey('tap_api.id'))
    api = relationship('TapApi', backref='auth_clients')
    client_id = Column(Integer, ForeignKey('tap_apiclient.id'), nullable=False)
    auth_client = relationship('TapApiClient', backref='auth_list')
    token = Column(Unicode(38), nullable=False)
    uid_auth = Column(Integer, ForeignKey('tap_user.id'))
    user_auth = relationship('TapUser', backref='auth_apis')
    disable = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_apiauth_apiid', TapApiAuth.api_id, TapApiAuth.client_id, unique=True)
Index('tap_apiauth_clientid', TapApiAuth.client_id)
Index('tap_apiauth_uid_auth', TapApiAuth.uid_auth)
Index('tap_apiauth_token', TapApiAuth.token)


class TapApiAccessKey(Base):
    __tablename__ = 'tap_apiauth_key'
    id = Column(BigInteger, Sequence('seq_tapauthkey_id'), primary_key=True)
    api_id = Column(Integer, ForeignKey('tap_api.id'))
    auth_id = Column(Integer, ForeignKey('tap_apiauth.id'), nullable=False)
    client_id = Column(Integer, ForeignKey('tap_apiclient.id'), nullable=False)
    token = relationship('TapApiAuth', backref='access_keys')
    access_key = Column(Unicode(60))
    access_expire = Column(Integer)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_apiauthkey_apiid', TapApiAccessKey.api_id, TapApiAccessKey.client_id)
Index('tap_apiauthkey_tokenid', TapApiAccessKey.auth_id)
Index('tap_apiauthkey_accesskey', TapApiAccessKey.access_key)

class TapApiStats(Base):
    __tablename__ = 'tap_apistats'
    id = Column(BigInteger, Sequence('seq_tapstats_id'), primary_key=True)
    api_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=False)
    client_id = Column(Integer)
    occurrence_time = Column(DateTime, nullable=False)
    occurrence_total = Column(Integer, default=0)  # 访问量
    exception_total = Column(Integer, default=0)  # 错误率
    elapse_max = Column(Float, default=0)
    elapse_min = Column(Float, default=0)
    elapse_avg = Column(Float, default=0)
    elapse_sum = Column(Float, default=0)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_apistats_projectid', TapApiStats.project_id, TapApiStats.client_id, TapApiStats.occurrence_time)
Index('tap_apistats_apiclientid', TapApiStats.api_id, TapApiStats.client_id, TapApiStats.occurrence_time, unique=True)
Index('tap_apistats_clientid', TapApiStats.client_id, TapApiStats.occurrence_time)

class TapApiErrors(Base):
    __tablename__ = 'tap_apierrors'
    id = Column(Integer, Sequence('seq_taperrors_id'), primary_key=True)
    api_id = Column(BigInteger, nullable=False)
    hash_id = Column(Unicode(60))
    project_id = Column(Integer, nullable=False)
    client_id = Column(Integer)
    occurrence_time = Column(DateTime, nullable=False)
    occurrence_total = Column(Integer, default=0)  # 错误发生次数
    exc_type = Column(UnicodeText)
    exc_message = Column(UnicodeText)
    exc_trace = Column(UnicodeText)
    exc_context = Column(LargeBinary)
    occurrence_first = Column(DateTime)  # 错误首次出现
    occurrence_last = Column(DateTime)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)
Index('tap_apierrors_projectid', TapApiErrors.project_id, TapApiErrors.client_id, TapApiErrors.occurrence_time)
Index('tap_apierrors_apiclientid', TapApiErrors.api_id, TapApiErrors.client_id, TapApiErrors.occurrence_time)
Index('tap_apierrors_clientid', TapApiErrors.client_id, TapApiErrors.occurrence_time)
Index('tap_apierrors_uniqueid', TapApiErrors.api_id, TapApiErrors.client_id, TapApiErrors.hash_id, unique=True)
