#coding=utf8


import datetime

from sqlalchemy.orm import relationship, backref
from sqlalchemy import (
    Column, Index, Integer, BigInteger, Unicode, UnicodeText, Boolean,
    ForeignKey, Enum, DateTime, LargeBinary, Float, Table, Sequence
)

from tap.models import Base
from tap.models import (
    TapUser
)


class TapTask(Base):
    __tablename__ = 'tap_task'
    id = Column(Integer, Sequence('seq_ttask_id'), primary_key=True)
    name = Column(Unicode(60), nullable=False)
    cron = Column(Unicode(20))  # cron expression
    variables = Column(Integer)  # environment variables
    description = Column(UnicodeText)
    dependencies = Column(UnicodeText)  # shell scripts to install dependencies
    os_require = Column(
        Enum('LINUX', 'MAC', 'WINDOWS', name="t_os_type", convert_unicode=True),
        default='LINUX')

    project_id = Column(Integer, ForeignKey('tap_taskproject.id'))
    project = relationship('TapTaskProject', backref="tasks")

    uid_create = Column(Integer, ForeignKey('tap_user.id'), nullable=False)
    user_create = relationship(TapUser, backref='tasks_created', )
    uid_modify = Column(Integer, ForeignKey('tap_user.id'), nullable=False)
    user_modify = relationship(TapUser, backref='tasks_modified')

    alert_emails = Column(UnicodeText)  # email list, split by comma

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_p_id_name', TapTask.project_id, TapTask.name, unique=True)


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

    executable_id = Column(Integer, ForeignKey('tap_taskexecutable.id'))
    executable = relationship('TapTaskExecutable',
                              backref=backref('runnable', uselist=False))

    task_id = Column(Integer, ForeignKey('tap_task.id'))
    task = relationship(TapTask, backref=backref('runnables', uselist=True))

    script = Column(UnicodeText)
    script_type = Column(
        Enum('SHELL', 'SQL', 'PYTHON', name="r_script_type",
             convert_unicode=True),
        default='SHELL')
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
    binary = Column(LargeBinary)

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
    os_type = Column(
        Enum('LINUX', 'MAC', 'WINDOWS', name="t_host_os_type",
             convert_unicode=True), default='LINUX')

    ip_address = Column(Unicode(64))
    sys_name = Column(Unicode(20))
    node_name = Column(Unicode(60))
    release = Column(Unicode(25))
    version = Column(Unicode(255))
    machine = Column(Unicode(20))
    cpu_count = Column(Integer)     # with psutil library
    memory_total = Column(Integer)  # bytes

    load_average = Column(Float)
    disk_remain = Column(Integer)   # bytes
    percent_cpu = Column(Float)
    percent_memory = Column(Float)
    network_sent = Column(Integer)  # bytes
    network_recv = Column(Integer)  # bytes

    report_time = Column(DateTime)  # host active judge

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
# ip_address+node_name are unique, but it can be changed later
# every worker client should hold a ip_address+node_name+TapTaskHost.id in
# local storage, it can recovery from the information in storage when reconnect
Index('tap_task_host', TapTaskHost.ip_address, TapTaskHost.node_name,
      unique=True)


class TapTaskHostHistory(Base):
    __tablename__ = 'tap_taskhost_history'
    id = Column(Integer, Sequence('seq_tthost_history_id'), primary_key=True)
    host_id = Column(Integer, ForeignKey('tap_task_host.id'))
    task = relationship(TapTaskHost, backref=backref('histories'))

    load_average = Column(Float)
    disk_remain = Column(Integer)
    percent_cpu = Column(Float)
    percent_memory = Column(Float)
    network_sent = Column(Integer)
    network_recv = Column(Integer)

    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
Index('tap_task_hosthistory', TapTaskHostHistory.host_id,
      TapTaskHostHistory.created)
