#coding=utf8

import time

import transaction

from tap.common.character import _print, _print_err
from tap.scripts.dbtools import initdb
from tap.common.thrifthelper import client_ensure
from tap.models import DBSession
from tap.modelstask import (
    TapTask,
    TapTaskStatus,
    TapTaskJobAssignment,
    TapTaskHost,
    TapTaskHostHistory,
)


def gen_jobs():
    key = 'timestamp.task.loop.'
    with transaction.manager:
        for task in DBSession.query(TapTaskStatus).filter_by(disable=False):
            s


def main():
    while True:
        try:
            gen_jobs()
        except BaseException as e:
            msg = e.message
            import traceback
            message = '%s\n%s' % (msg, traceback.format_exc())
            _print_err(message)
        time.sleep(60)
