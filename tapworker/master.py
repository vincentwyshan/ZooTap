#coding=utf8

from __future__ import division

import os
import datetime
from optparse import OptionParser

import simplejson as json

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from sqlalchemy import desc
import transaction

from tap.servicedef import TapTaskMaster
from tap.servicedef.ttypes import TapError
# from tap.scripts import init_session_from_cmd
from tap.scripts.dbtools import initdb
from tap.models import DBSession
from tap.modelstask import (
    TapTask,
    TapTaskStatus,
    TapTaskAssignment,
    TapTaskAssignHistory,
    TapTaskHost,
    TapTaskHostHistory,
    TapTaskExecutable,
)

PORT = 10102


def error_handle(func):
    def wraper(*kargs, **kwargs):
        try:
            return func(*kargs, **kwargs)
        except BaseException as e:
            import traceback
            message = traceback.format_exc()
            return TapError(err_message=message)
    return wraper


class Handler(object):
    def ping(self):
        pass

    @error_handle
    def host_register(self, ip_address, listen_port, node_name, sys_name,
                      release, version, machine, cpu_count, memory_total,
                      old_ip_address, old_node_name, directory,
                      software_requirements):
        """
        Register a host. Host only can be deleted by manually operation.
        ip_address and node_name are the unique constraint, old_ip_address
        and old_node_name can update a server when its node_name and ip_address
        was changed.
        Using os.uname and psutil to generate information.
        :param ip_address:
        :param node_name:
        :param sys_name:
        :param release:
        :param version:
        :param machine:
        :param cpu_count:
        :param memory_total:
        :param old_ip_address:
        :param old_node_name:
        :param directory: the directory for storing logs and temporary files
        :param software_requirements: see TapTaskHost.ver_*
        :return:
        """
        with transaction.manager:
            if old_ip_address or old_node_name:
                host = DBSession.query(TapTaskHost).filter_by(
                    ip_address=old_ip_address, node_name=old_node_name).first()

            if not host:
                host = TapTaskHost()
                DBSession.add(host)
            host.ip_address = ip_address
            host.listen_port = listen_port
            host.node_name = node_name
            host.sys_name = sys_name
            host.release = release
            host.version = version
            host.machine = machine
            host.cpu_count = cpu_count
            host.memory_total = memory_total
            host.version = version
            host.directory = directory

            # host.software_requirements = software_requirements
            host.os_type = software_requirements['os_type']
            host.ver_python = software_requirements['ver_python']
            host.ver_java = software_requirements['ver_java']
            host.ver_dotnet = software_requirements['ver_dotnet']
            host.ver_php = software_requirements['ver_php']
            host.ver_node = software_requirements['ver_node']

            DBSession.flush()
            return host.id

    @error_handle
    def host_status(self, host_id, load_average, disk_remain, percent_cpu,
                    percent_memory, network_sent, network_recv):
        """
        Update host status
        :param host_id:
        :param load_average:
        :param disk_remain:
        :param percent_cpu:
        :param percent_memory:
        :param network_sent:
        :param network_recv:
        :return:
        """
        with transaction.manager:
            host = DBSession.query(TapTaskHost).get(host_id)
            host.load_average = load_average
            host.disk_remain = disk_remain
            host.percent_cpu = percent_cpu
            host.percent_memory = percent_memory
            host.network_sent = network_sent
            host.network_recv = network_recv

            history = TapTaskHostHistory(
                load_average=load_average, host_id=host_id,
                disk_remain=disk_remain, percent_cpu=percent_cpu,
                percent_memory=percent_memory, network_sent=network_sent,
                network_recv=network_recv
            )
            DBSession.add(history)

    @error_handle
    def job_request(self, host_id):
        """
        Assign a job to a host
        :param host_id:
        :return: {job_id, start_time, task_name, task_variables,
                 task_dependencies, task_scripts, task_executables}
        """
        # query job
        now = datetime.datetime.now()
        with transaction.manager:
            jobs = DBSession.query(TapTaskAssignment) \
                .filter(TapTaskAssignment.host_id == host_id,
                        TapTaskAssignment.time_start > now)

            result = []
            for job in jobs:
                _job = {}
                _job['job_id'] = str(job.id)
                _job['start_time'] = job.start_time.strftime('%Y-%d-%m %H:%M:%S')
                _job['task_name'] = job.task.name.encode("utf8")
                _job['task_variables'] = job.task.variables.encode('utf8')
                _job['task_dependencies'] = job.task.dependencies.encode('utf8')
                task_scripts = [(r.script_type, r.script) for r in
                                job.task.runnables]
                _job['task_scripts'] = json.dumps(task_scripts)
                task_executables = [(e.name, e.md5) for e in
                                    job.task.executables]
                _job['task_executables'] = json.dumps(task_executables)
                result.append(_job)
            return result

    @error_handle
    def job_start(self, host_id, job_id, start_time):
        """
        record job start time
        :param host_id:
        :param job_id:
        :param start_time:
        :return:
        """
        with transaction.manager:
            job = DBSession.query(TapTaskAssignment).get(job_id)
            start_time = datetime.datetime.strptime(
                start_time, '%y-%m%d %H:%M:%s')
            job.time_start1 = start_time
            history = DBSession.query(TapTaskAssignHistory).filter(
                task_id=job.task_id, host_id=host_id
            ).order_by(desc(TapTaskAssignHistory.id)).first()
            history.time_start1 = start_time

    @error_handle
    def job_done(self, host_id, job_id, end_time, success, message):
        """
        Record job end time
        :param host_id:
        :param job_id:
        :param end_time:
        :param success:
        :param elapse:
        :param message:
        :return:
        """
        with transaction.manager:
            job = DBSession.query(TapTaskAssignment).get(job_id)
            end_time = datetime.datetime.strptime(
                end_time, '%y-%m%d %H:%M:%s')
            job.time_end = end_time
            job.is_failed = (not success)
            history = DBSession.query(TapTaskAssignHistory).filter(
                task_id=job.task_id, host_id=host_id
            ).order_by(desc(TapTaskAssignHistory.id)).first()
            history.time_end = end_time
            history.is_failed = (not success)

    @error_handle
    def executable_fetch(self, md5):
        with transaction.manager:
            exectable = DBSession.query(TapTaskExecutable).filter_by(
                md5=md5).first()
            return exectable.binary


def run_server():
    processor = TapTaskMaster.Processor(Handler())
    transport = TSocket.TServerSocket(port=PORT)
    tfactory = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()

    # You could choose one of these for a multiple threaded server
    server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
    #server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)

    print 'Starting the server...'
    server.serve()
    print 'Starting done.'


def main():
    usage = "usage: %prog production.ini [options]"
    parser = OptionParser(usage=usage)
    # parser.add_option('-i', type="string", dest="interval",
    #                   default="1M",
    #                   help="stats interval: [1M/5M/10M/30M/1H]")
    (options, args) = parser.parse_args()

    initdb()

    run_server()

