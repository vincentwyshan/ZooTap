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


class TapTaskExecutable(Base):
    __tablename__ = 'tap_taskexecutable'
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
    task_id = Column(Integer, ForeignKey('tap_task.id'))
    task = relationship(TapTask, backref=backref('runnables', uselist=True))
    content = Column(LargeBinary)  # store as utf-8 string in json format
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now,
                       onupdate=datetime.datetime.now, nullable=False)
Index('tap_task_history_taskid', TapTaskHistory.task_id)


class TapTaskStats(Base):
    pass


class TapTaskStatus(Base):
    pass
