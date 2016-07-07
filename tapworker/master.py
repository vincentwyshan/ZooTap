#coding=utf8

from __future__ import division

import time
import copy
import datetime
import warnings
import threading
from optparse import OptionParser

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

import transaction

from tap.servicedef import TapTaskMaster
from tap.servicedef.ttypes import TapError
# from tap.scripts import init_session_from_cmd
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
                      old_ip_address, old_node_name):
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
        :return:
        """
        with transaction.manager:
            if old_ip_address or old_node_name:
                host = DBSession.query(TapTaskHost).filter_by(
                    ip_address=old_ip_address, node_name=old_node_name).first()

            if not host:
                host = TapTaskHost(
                    ip_address=ip_address, node_name=node_name,
                    sys_name=sys_name, release=release, version=version,
                    machine=machine, cpu_count=cpu_count,
                    memory_total=memory_total, listen_port=listen_port)
                DBSession.add(host)
            else:
                host.ip_address = ip_address
                host.listen_port = listen_port
                host.node_name = node_name
                host.sys_name = sys_name
                host.release = release
                host.version = version
                host.machine = machine
                host.cpu_count = cpu_count
                host.memory_total = memory_total
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

    # map<string, string> job_request(1:i32 host_id) throws (1: TapError error),
    @error_handle
    def job_request(self, host_id):
        """
        Assign a job to a host
        :param host_id:
        :return:
        """
        # generate job
        # check timestamp
        key = 'timestamp.task.loop'
        DBSession.query(TapTaskStatus)
        # assign job

    # void job_start (1:i32 host_id, 2:i32 job_id),
    def job_start(self, host_id, job_id):
        pass

    # void job_done (1:i32 host_id, 2:i32 job_id,
    #                3:bool success, 4:double elapse, 5:string message)
    # }
    def job_done(self, host_id, job_id, success, elapse, message):
        pass



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

