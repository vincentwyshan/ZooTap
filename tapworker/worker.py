#coding=utf8
"""
Task worker do following things:
    1. Register host, update status every 1 minutes
    2. In charge of running jobs
    3. Get jobs and schedule jobs
    4. 1 host can only run 1 worker
    5. Process control, save process log
    6. API for querying log files
"""

import os
import re
import sys
import socket
import json
import time
import subprocess
import multiprocessing

import psutil
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from tap.common.thrifthelper import client_ensure
from tap.servicedef import TapTaskMaster


LISTEN_PORT = int(os.environ.get('TAPWORKER_LISPORT', 10105))
LOCAL_DIRECTORY = os.environ.get('TAPWORKER_DIRECTORY', '/tmp/tap')

if not os.path.exists(LOCAL_DIRECTORY):
    os.makedirs(LOCAL_DIRECTORY)


PORT = 10103


class Client(object):
    def __init__(self, host):
        self.host = host
        self.client = None
        self.transport = None
        self._newclient()

    @client_ensure
    def ping(self):
        self.client.ping()

    def _newclient(self):
        transport = TSocket.TSocket(self.host, PORT)
        # transport.setTimeout(1000*60*2)
        # 超时最多两秒
        transport.setTimeout(1000*2)
        self.transport = TTransport.TBufferedTransport(transport)

        # Wrap in a protocol
        protocol = TBinaryProtocol.TBinaryProtocol(transport)

        # Create a client to use the protocol encoder
        self.client = TapTaskMaster.Client(protocol)

        self.transport.open()

    @client_ensure
    def host_register(self, ip_address, listen_port, node_name, sys_name,
                      release, version, machine, cpu_count, memory_total,
                      old_ip_address, old_node_name, directory,
                      software_requirements):
        return self.client.host_register(
            ip_address, listen_port, node_name, sys_name, release, version,
            machine, cpu_count, memory_total, old_ip_address, old_node_name,
            directory, software_requirements)

    @client_ensure
    def host_status(self, host_id, load_average, disk_remain, percent_cpu,
                    percent_memory, network_sent, network_recv):
        return self.client.host_status(
            host_id, load_average, disk_remain, percent_cpu, percent_memory,
            network_sent, network_recv
        )

    @client_ensure
    def job_request(self, host_id):
        return self.client.job_request(
            host_id
        )

    @client_ensure
    def job_start(self, host_id, job_id, start_time):
        return self.client.job_start(
            host_id, job_id, start_time
        )

    @client_ensure
    def job_done(self, host_id, job_id, end_time, success, message):
        return self.client.job_done(
            host_id, job_id, end_time, success, message
        )

    @client_ensure
    def executable_fetch(self, md5):
        return self.client.executable_fetch(
            md5
        )

    def close(self):
        self.transport.close()


def get_client():
    host = os.environ.get('TAPWORKER_MASTERIP')
    return Client(host)


def start_process():
    """
    Start a task
    :return:
    """
    pass


def persistence_program():
    """
    Download program from master, save it local
    :return:
    """
    pass


def forever_loop():
    """

    :return:
    """


def register():
    """
    Register host
    :return:
    """
    old_ip_address, old_node_name, ip_address = get_save_ip()
    uname = os.uname()
    node_name = uname[1]
    sys_name = uname[0]
    release = uname[2]
    version = uname[3]
    machine = uname[4]
    cpu_count = psutil.cpu_count()
    memory_total = psutil.virtual_memory().total

    software_requirements = {}
    if sys.platform.find('darwin') >= 0:
        software_requirements['os_type'] = 'MAC'
    elif sys.platform.find('win32') >= 0:
        software_requirements['os_type'] = 'MAC'
    elif sys.platform.find('linux') >= 0:
        software_requirements['os_type'] = 'LINUX'

    software_requirements['ver_python'] = get_ver_python()
    software_requirements['ver_php'] = get_ver_php()
    software_requirements['ver_java'] = get_ver_java()
    software_requirements['ver_dotnet'] = get_ver_dotnet()
    software_requirements['ver_node'] = get_ver_node()
    get_client().host_register(
        ip_address, LISTEN_PORT, node_name, sys_name, release, version,
        machine, cpu_count, memory_total, old_ip_address, old_node_name,
        LOCAL_DIRECTORY, software_requirements)


def get_ver_python():
    process = subprocess.Popen('python -V', stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True)
    result = process.communicate()[1]
    # 'LE2.5', '2.5', '2.6', '2.7', '3.0',
    if re.search(r'\b3\.', result):
        return 'GE3.0'
    elif re.search(r'\b2.7', result):
        return '2.7'
    elif re.search(r'\b2.6', result):
        return '2.6'
    elif re.search(r'\b2.5', result):
        return '2.5'
    elif not result:
        return None
    else:
        return 'LE2.5'


def get_ver_php():
    process = subprocess.Popen('php --version', stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True)
    result = process.communicate()[0]
    if re.search(r'\d\.\d', result) and re.search(r'php', result, re.IGNORECASE):
        return re.search(r'php ([\d\.]*)', result, re.IGNORECASE).groups(0)
    else:
        return None


def get_ver_java():
    process = subprocess.Popen('java -version', stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True)
    result = process.communicate()[1]
    if re.search(r'java version', result, re.IGNORECASE) and \
            re.search(r'"([\d\.\_]*)"', result):
        return re.search(r'"([\d\.\_]*)"', result).groups(0)
    else:
        return None


def get_ver_node():
    process = subprocess.Popen('node -v', stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True)
    result = process.communicate()[0]
    if re.search(r'v([\d\.])', result):
        return re.search(r'v([\d\.])', result).groups(0)
    else:
        return None


def get_save_ip():
    ip_address = socket.gethostbyname(socket.gethostname())
    path = os.path.join(LOCAL_DIRECTORY, 'ip_and_node')
    if os.path.exists(path):
        data = json.load(open(path, 'r'))
        old_ip_address = data['ip_address']
        old_node_name = data['node_name']
    data = dict(ip_address=ip_address, node_name=os.uname()[1])
    json.dump(data, open(path, 'w'))
    return old_ip_address, old_node_name, ip_address


def get_ver_dotnet():
    return None


def update_status():
    # (self, host_id, load_average, disk_remain, percent_cpu,
    #                 percent_memory, network_sent, network_recv):
    pass


def forever_status():
    """
    update status
    :return:
    """
    while True:
        update_status()
        time.sleep(60)


def main():
    """

    :return:
    """
    # register host
    register()

    while True:
        pass
        # 1. update status every 1 minutes
        # 2. execute jobs
        # 3. get jobs and schedule jobs
