#coding=utf8
"""
1.
"""

import os
import time
import datetime

from optparse import OptionParser

from croniter import croniter
import transaction

from tap.common.character import _print, _print_err
from tap.scripts.dbtools import initdb
from tap.models import DBSession
from tap.modelstask import (
    TapTask,
    TapTaskStatus,
    TapTaskAssignment,
    TapTaskAssignHistory,
    TapTaskHost,
)


# eager job generation interval, in minute
INTERVAL_RUN = int(os.environ.get('TAP_JOBGEN_INTERVAL', 5))


def gen_jobs():
    with transaction.manager:
        now = datetime.datetime.now()

        # get all tasks
        task_list = DBSession.query(TapTask.id).filter_by(disable=False)
        task_list = [t.id for t in task_list]

        # get all jobs, start time greater than now + INTERVAL_RUN minutes
        start_time = now + datetime.timedelta(minutes=INTERVAL_RUN)
        job_list = DBSession.query(TapTaskAssignment.task_id).filter(
            TapTaskAssignment.start_time > start_time)
        job_list = [j.task_id for j in job_list]

        # calculate difference
        # TODO consider TaskHostBind
        no_job_list = set(task_list).difference(job_list)

        # get hosts
        hosts = DBSession.query(TapTaskHost)
        host_choices = list(hosts)

        # gen jobs
        for task_id in no_job_list:
            task = DBSession.query(TapTask).get(task_id)
            cron = croniter(task.cron, now)
            while True:
                start_time = cron.get_next(datetime.datetime)
                if (start_time - now).seconds > (INTERVAL_RUN * 60):
                    break

                create_job(host_choices, hosts, start_time, task, task_id)


def create_job(host_choices, hosts, start_time, task):
    job = DBSession.query(TapTaskAssignment).filter_by(
        task_id=task.id).first()

    # previous job not finished
    if job and not job.is_failed == False:
        return False

    if not job:
        job = TapTaskAssignment()
        history = TapTaskAssignHistory()
        DBSession.add(job)
        DBSession.add(history)
        job.task_id = task.id
        history.task_id = task.id

        # match requirements and host resource(only verify memory)
        if not host_choices:
            host_choices.extend(list(hosts))
        for host in host_choices:
            if verify_host(task, host):
                host_choices.remove(host)
                job.host_id = host.id
                history.host_id = host.id
            log_path = os.path.join(host.directory, task.project.name,
                                    task.name + u'.log')
            job.log_path = log_path
            history.log_path = log_path
            history.time_start = start_time
    else:
        job.is_failed = None

    job.time_start = start_time
    return True


def verify_host(task, host):
    """
    verify if host match the task's requirements and resources(only memory)
    :return: True/False
    """
    # TODO consider TaskHostBind
    if task.require_os:
        require_os = task.require_os.split(',')
        match_os = False
        for os_name in require_os:
            if os_name == host.os_type or os_name == 'ANY':
                match_os = True
                break
        if not match_os:
            return False

    def verify_version(versions, host_version):
        if versions and not host_version:
            return False
        if versions:
            versions = versions.split(',')
            match_version = False
            for version in versions:
                if version == host_version or version == 'ANY':
                    match_version = True
                    break
            if not match_version:
                return False
        return True

    if verify_version(task.require_python, os.ver_python):
        return False
    if verify_version(task.require_java, os.ver_java):
        return False
    if verify_version(task.require_dotnet, os.ver_dotnet):
        return False
    if verify_version(task.require_php, os.ver_php):
        return False
    if verify_version(task.require_node, os.ver_node):
        return False

    # resource check(only memory)
    # need_memory*1.3 < percent_memory * memory_total
    if task.need_memory * (1024*1024) < (host.percent_memory *
                                         host.memory_total):
        return False

    return True


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


def entry_point():
    usage = "usage: %prog production.ini [options]"
    parser = OptionParser(usage=usage)
    # parser.add_option('-i', type="string", dest="interval",
    #                   default="1M",
    #                   help="stats interval: [1M/5M/10M/30M/1H]")
    (options, args) = parser.parse_args()

    # init_session_from_cmd()
    initdb()

    main()

