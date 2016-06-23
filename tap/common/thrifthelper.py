#coding=utf8

import socket
from functools import wraps

from thrift.transport.TTransport import TTransportException
from thrift.Thrift import TApplicationException


def client_ensure(func):
    """
    this wraper make sure initialize a new client when connect thrift server
    failed. wraped thrift Client must have a _newclient function to initialize
    transport connection.
    """
    @wraps(func)
    def wraper(*kargs, **kwarg):
        try:
            return func(*kargs, **kwarg)
        except (TTransportException, TApplicationException, socket.error):
            self = kargs[0]
            self._newclient()
        except BaseException as e:
            # print e
            import traceback
            traceback.print_exc()
            self = kargs[0]
            self._newclient()
    return wraper

