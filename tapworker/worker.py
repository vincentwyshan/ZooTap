#coding=utf8
"""
1. Process control
2. Report process status
3. Save log
4. Log file query API
"""

import os
import socket
import subprocess
import multiprocessing

import psutil


LISTEN_PORT = int(os.environ.get('TAPWORKER_LISPORT', 10105))


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
    # ip_address, listen_port, node_name, sys_name, release, version,
    # machine, cpu_count, memory_total, old_ip_address, old_node_name,
    # directory, software_requirements)
    ip_address = socket.gethostbyname(socket.gethostname())
    uname = os.uname()
    node_name = uname[1]
    sys_name = uname


def main():
    register()
