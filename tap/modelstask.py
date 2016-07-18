#coding=utf8


import datetime

from sqlalchemy.orm import relationship, backref, deferred
from sqlalchemy import (
    Column, Index, Integer, BigInteger, Unicode, UnicodeText, Boolean,
    ForeignKey, Enum, DateTime, LargeBinary, Float, Table, Sequence
)

from tap.models import Base
from tap.models import (
    TapUser
)


ENUM_OS_TYPE = Enum('ANY', 'LINUX', 'MAC', 'WINDOWS', name="t_os_type",
                    convert_unicode=True)
ENUM_PYTHON_VER = Enum('ANY', 'LE2.5', '2.5', '2.6', '2.7', '3.0',
                       name="t_python_ver", convert_unicode=True)
ENUM_JAVA_VER = Enum('ANY', name="t_java_ver", convert_unicode=True)
ENUM_DOTNET_VER = Enum('ANY', name="t_dotnet_ver", convert_unicode=True)
ENUM_PERL_VER = Enum('ANY', name="t_perl_ver", convert_unicode=True)
ENUM_NODE_VER = Enum('ANY', name="t_node_ver", convert_unicode=True)
ENUM_PHP_VER = Enum('ANY', name="t_php_ver", convert_unicode=True)

ENUM_SCRIPT_TYPE = Enum('SHELL', 'SQL', 'PYTHON', name="t_script_type",
                        convert_unicode=True)


class TapTask(Base):
    __tablename__ = 'tap_task'
    id = Column(Integer, Sequence('seq_ttask_id'), primary_key=True)
    name = Column(Unicode(60), nullable=False)
    cron = Column(Unicode(20))  # cron expression

    variables = Column(Integer)  # environment variables, json format

    description = Column(UnicodeText)
    dependencies = Column(UnicodeText)  # shell scripts to install dependencies

    need_memory = Column(Integer)  # memory size need in MB

    # ENUM TYPE can be multiple, split by comma
    require_os = Column(Unicode(64), default='LINUX')
    require_python = Column(Unicode(64), default=None)
    require_java = Column(Unicode(64), default=None)
    require_dotnet = Column(Unicode(64), default=None)
    require_php = Column(Unicode(64), default=None)
    require_node = Column(Unicode(64), default=None)

    project_id = Column(Integer, ForeignKey('tap_taskproject.id'))
    project = relationship('TapTaskProject', backref="tasks")

    uid_create = Column(Integer, ForeignKey('tap_user.id'), nullable=False)
    user_create = relationship(TapUser, backref='tasks_created', )
    uid_modify = Column(Integer, ForeignKey('tap_user.id'), nullable=False)
    user_modify = relationship(TapUser, backref='tasks_modified')

    alert_emails = Column(UnicodeText)  # email list, split by comma

    host_id = Column(Integer, ForeignKey("tap_taskhost.id"), nullable=True)
    host = relationship('TapTaskHost', backref="tasks")

    disable = Column(Boolean, default=False)

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_p_id_name', TapTask.project_id, TapTask.name, unique=True)
Index('tap_task_disable', TapTask.disable)


class TapTaskProject(Base):
    __tablename__ = 'tap_taskproject'
    id = Column(Integer, Sequence('seq_ttproject_id'), primary_key=True)
    name = Column(Unicode(30), nullable=False)
    description = Column(UnicodeText)
    uid_create = Column(Integer, ForeignKey('tap_user.id'), nullable=False)
    user_create = relationship(TapUser, backref='projects_created')
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)


class TapTaskRunnable(Base):
    __tablename__ = 'tap_taskrunnable'
    id = Column(Integer, Sequence('seq_ttrunnable_id'), primary_key=True)

    # executable_id = Column(Integer, ForeignKey('tap_taskexecutable.id'))
    # executable = relationship('TapTaskExecutable',
    #                           backref=backref('runnable', uselist=False))

    task_id = Column(Integer, ForeignKey('tap_task.id'))
    task = relationship(TapTask, backref=backref('runnables', uselist=True))

    # call executable $executable_name
    script = Column(UnicodeText)
    script_type = Column(ENUM_SCRIPT_TYPE, default='SHELL')

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_r_task_id', TapTaskRunnable.task_id)
Index('tap_task_r_execute_id', TapTaskRunnable.executable_id, unique=True)


class TapTaskExecutable(Base):
    __tablename__ = 'tap_taskexecutable'
    id = Column(Integer, Sequence('seq_ttexecutable_id'), primary_key=True)
    name = Column(Unicode(50), nullable=False)
    md5 = Column(UnicodeText)
    binary = deferred(Column(LargeBinary))

    task_id = Column(Integer, ForeignKey('tap_task.id'))
    task = relationship(TapTask, backref=backref('executables', uselist=True))

    uid_create = Column(Integer, ForeignKey('tap_user.id'), nullable=False)
    user_create = relationship(TapUser, backref='projects_created')

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_executable_md5', TapTaskExecutable.md5, unique=True)


class TapTaskHistory(Base):
    __tablename__ = 'tap_taskhistory'
    id = Column(Integer, Sequence('seq_tthistory_id'), primary_key=True)
    task_id = Column(Integer, ForeignKey('tap_task.id'))
    task = relationship(TapTask, backref=backref('runnables', uselist=True))
    content = Column(LargeBinary)  # store as utf-8 string in json format
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_history_taskid', TapTaskHistory.task_id)


class TapTaskStats(Base):
    __tablename__ = 'tap_taskstats'
    id = Column(Integer, Sequence('seq_tthistory_id'), primary_key=True)
    task_id = Column(Integer, ForeignKey('tap_task.id'))
    task = relationship(TapTask, backref=backref('runnables', uselist=False))

    stats_avg = Column(Float)
    stats_max = Column(Float)
    stats_min = Column(Float)
    stats_total = Column(BigInteger)
    stats_total_fail = Column(BigInteger)

    last_executed_time = Column(DateTime)
    last_executed_result = Column(
        Enum('SUCCESS', 'FAIL', name="r_result_type", convert_unicode=True),
        default='SUCCESS'
    )
    last_executed_error = Column(UnicodeText)

    status = Column(
        Enum('RUNNING', 'SLEEP', name="r_result_type", convert_unicode=True),
        default='SLEEP'
    )
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_stats_taskid', TapTaskStats.task_id, unique=True)


class TapTaskHost(Base):
    __tablename__ = 'tap_taskhost'
    id = Column(Integer, Sequence('seq_tthost_id'), primary_key=True)

    ip_address = Column(Unicode(64))
    listen_port = Column(Integer)
    sys_name = Column(Unicode(20))
    node_name = Column(Unicode(60))
    release = Column(Unicode(25))
    version = Column(Unicode(255))
    machine = Column(Unicode(20))
    cpu_count = Column(Integer)     # with psutil library
    memory_total = Column(Integer)  # bytes

    # environment support
    os_type = Column(ENUM_OS_TYPE, default='LINUX')
    ver_python = Column(ENUM_PYTHON_VER, default=None)
    ver_java = Column(ENUM_JAVA_VER, default=None)
    ver_dotnet = Column(ENUM_DOTNET_VER, default=None)
    ver_php = Column(ENUM_PHP_VER, default=None)
    ver_node = Column(ENUM_NODE_VER, default=None)

    # environment variables
    directory = Column(Unicode(256))

    # load stats
    load_average = Column(Float)
    disk_remain = Column(Integer)   # bytes
    percent_cpu = Column(Float)
    percent_memory = Column(Float)
    network_sent = Column(Integer)  # bytes
    network_recv = Column(Integer)  # bytes

    report_time = Column(DateTime)  # host last active time

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
# ip_address+node_name are unique, but it can be changed later
# every worker client should hold a ip_address+node_name+TapTaskHost.id in
# local storage, it can recovery from the information in storage when reconnect
Index('tap_task_host', TapTaskHost.ip_address, TapTaskHost.node_name,
      unique=True)
Index('tap_task_host_rtime', TapTaskHost.report_time)


class TapTaskHostHistory(Base):
    __tablename__ = 'tap_taskhost_history'
    id = Column(Integer, Sequence('seq_tthost_history_id'), primary_key=True)
    host_id = Column(Integer, ForeignKey('tap_task_host.id'))
    host = relationship(TapTaskHost, backref=backref('histories'))

    load_average = Column(Float)
    disk_remain = Column(Integer)
    percent_cpu = Column(Float)
    percent_memory = Column(Float)
    network_sent = Column(Integer)
    network_recv = Column(Integer)

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
Index('tap_task_hosthistory', TapTaskHostHistory.host_id,
      TapTaskHostHistory.created)


class TapTaskJobAssignment(Base):
    __tablename__ = 'tap_task_jobassignments'
    id = Column(Integer, Sequence('seq_ttjob_assign_id'), primary_key=True)

    task_id = Column(Integer, ForeignKey('tap_task.id'))
    task = relationship(TapTask, backref=backref('jobs'))

    host_id = Column(Integer, ForeignKey('tap_task_host.id'))
    host = relationship(TapTaskHost, backref=backref('histories'))

    is_failed = Column(Boolean, default=None, nullable=True)
    log_path = Column(UnicodeText, nullable=False)  # VNC path or path on host

    time_start = Column(DateTime, nullable=False)  # scheduled start time
    time_start1 = Column(DateTime, nullable=True)  # real start time
    time_end = Column(DateTime, nullable=True)

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_jobassign_tid', TapTaskJobAssignment.task_id, unique=True)
Index('tap_task_jobhost_time', TapTaskJobAssignment.host_id,
      TapTaskJobAssignment.time_start)


class TapTaskJobHistory(Base):
    __tablename__ = 'tap_task_jobhistory'
    id = Column(Integer, Sequence('seq_ttjob_history_id'), primary_key=True)

    task_id = Column(Integer, ForeignKey('tap_task.id'))
    task = relationship(TapTask, backref=backref('jobs'))

    host_id = Column(Integer, ForeignKey('tap_task_host.id'))
    host = relationship(TapTaskHost, backref=backref('histories'))

    is_failed = Column(Boolean, default=None, nullable=True)
    log_path = Column(UnicodeText, nullable=False)  # VNC path or path on host

    time_start = Column(DateTime, nullable=False)  # scheduled start time
    time_start1 = Column(DateTime, nullable=True)  # real start time
    time_end = Column(DateTime, nullable=True)

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_jobhis_tid', TapTaskJobHistory.task_id)


class TapTaskStatus(Base):
    """
    Store status by key-value
    """
    __tablename__ = 'tap_task_status'
    id = Column(Integer, Sequence('seq_tt_status_id'), primary_key=True)

    key = Column(Unicode(128))
    value = Column(UnicodeText)
    expire = DateTime(DateTime)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_status_key', TapTaskStatus.key, unique=True)



