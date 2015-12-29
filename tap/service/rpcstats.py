#coding=utf8

from __future__ import division

import time
import copy
import datetime
import socket
import warnings
import threading
from functools import wraps

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
from thrift.transport.TTransport import TTransportException
from thrift.Thrift import TApplicationException

import transaction

from tap.servicedef import TapService
from tap.scripts import init_session_from_cmd
from tap.models import (
    DBSession,
    TapApi,
    TapApiStats,
    TapApiErrors,
)


STATS_ELAPSE = {}
# API-ID: {}

STATS_EXC = {}
# (API-ID, exc_trace): {}

STATS_ELAPSE_CLIENT = {}
# (API-ID, CLIENT-ID): {}

STATS_EXC_CLIENT = {}
# (API-ID, CLIENT-ID, exc_trace): {}


class Handler(object):
    def ping(self):
        print 'ping'

    def report(self, params):
        """
        report api access information
        :param params-api_id:
        :param params-client_id: optional
        :param params-elapse:
        :param params-exc_type: optional
        :param params-exc_message: optional
        :param params-exc_trace: optional
        :param params-exc_context: optional, json
        """
        # 访问量和耗时统计(按 api_id)
        api_id = params['api_id']
        if api_id not in STATS_ELAPSE:
            STATS_ELAPSE[api_id] = dict(
                elapse_max=0, elapse_min=0, elapse_avg=0, occurrence_total=0,
                elapse_sum=0, exception_total=0
            )
        elapse = STATS_ELAPSE[api_id]
        elapse_now = float(params['elapse'])
        elapse['elapse_sum'] += elapse_now
        elapse['occurrence_total'] += 1
        if 'exc_trace' in params:
            elapse['exception_total'] += 1
        if elapse_now > elapse['elapse_max']:
            elapse['elapse_max'] = elapse_now
        elif (elapse['elapse_min'] == 0
              or elapse_now < elapse['elapse_min']):
            elapse['elapse_min'] = elapse_now

        elapse['elapse_avg'] = elapse['elapse_sum'] / elapse['occurrence_total']

        # 访问量和耗时统计(按 client_id)
        client_id = params.get('client_id', None)
        if client_id:
            key = (api_id, client_id)
            if key not in STATS_ELAPSE:
                STATS_ELAPSE_CLIENT[key] = dict(
                    elapse_max=0, elapse_min=0, elapse_avg=0,
                    occurrence_total=0, elapse_sum=0, exception_total=0
                )
            elapse = STATS_ELAPSE_CLIENT[key]
            elapse['elapse_sum'] += elapse_now
            elapse['occurrence_total'] += 1
            if 'exc_trace' in params:
                elapse['exception_total'] += 1
            if elapse_now > elapse['elapse_max']:
                elapse['elapse_max'] = elapse_now
            elif (elapse_now < elapse['elapse_min']
                  or elapse['elapse_min'] == 0):
                elapse['elapse_min'] = elapse_now

            elapse_avg = elapse['elapse_sum'] / elapse['occurrence_total']
            elapse['elapse_avg'] = elapse_avg

        print 'ELAPSE:', len(STATS_ELAPSE), len(STATS_ELAPSE_CLIENT)
        if 'exc_type' not in params:
            return

        # 出错统计
        exc_type = params['exc_type']
        exc_trace = params['exc_trace']
        exc_message = params['exc_message']
        exc_context = params['exc_context']
        key = (api_id, exc_trace)
        if key not in STATS_EXC:
            STATS_EXC[key] = dict(
                exc_type=exc_type,
                exc_message=exc_message,
                exc_context=exc_context,
                occurrence_total=0,
                occurrence_first=datetime.datetime.now(),
                occurrence_last=None
            )
        STATS_EXC[key]['occurrence_total'] += 1
        STATS_EXC[key]['occurrence_last'] = datetime.datetime.now()

        # 出错统计(按客户)
        if client_id:
            key = (api_id, client_id, exc_trace)
            if key not in STATS_EXC:
                STATS_EXC[key] = dict(
                    exc_type=exc_type,
                    exc_message=exc_message,
                    exc_context=exc_context,
                    occurrence_total=0,
                    occurrence_first=datetime.datetime.now(),
                    occurrence_last=None
                )
            STATS_EXC[key]['occurrence_total'] += 1
            STATS_EXC[key]['occurrence_last'] = datetime.datetime.now()


def flush_log(occurrence_time):
    global STATS_ELAPSE, STATS_ELAPSE_CLIENT, STATS_EXC, STATS_EXC_CLIENT
    # 更新访问量和耗时统计
    # print 'client:', len(STATS_ELAPSE_CLIENT)
    all_stats = [(key[0], key[1], elapse) for key, elapse in
                 STATS_ELAPSE_CLIENT.items()]
    STATS_ELAPSE_CLIENT = {}
    # print 'NO client:', len(STATS_ELAPSE)
    all_stats.extend([(api_id, -1, elapse) for api_id, elapse in
                      STATS_ELAPSE.items()])
    STATS_ELAPSE = {}
    print occurrence_time, 'ELAPSE:', len(STATS_ELAPSE), \
        len(STATS_ELAPSE_CLIENT)
    print occurrence_time, 'Stats elapse:', len(all_stats)
    for api_id, client_id, elapse in all_stats:
        with transaction.manager:
            api = DBSession.query(TapApi).get(api_id)
            if not api:
                warnings.warn("API:%s is not exist." % api_id)
                continue

            q = DBSession.query(TapApiStats)\
                .filter_by(api_id=api_id, occurrence_time=occurrence_time,
                           client_id=client_id)
            stats = q.first()
            if not stats:
                stats = TapApiStats(api_id=api_id, project_id=api.project_id,
                                    occurrence_time=occurrence_time,
                                    client_id=client_id)
                DBSession.add(stats)
                DBSession.flush()

            stats = DBSession.query(TapApiStats).with_lockmode('update')\
                .filter(TapApiStats.id==stats.id).first()
            stats.occurrence_time = occurrence_time
            stats.occurrence_total += elapse['occurrence_total']
            stats.exception_total += elapse['exception_total']
            if stats.elapse_max < elapse['elapse_max']:
                stats.elapse_max = elapse['elapse_max']
            if stats.elapse_min < elapse['elapse_min']:
                stats.elapse_min = elapse['elapse_min']
            stats.elapse_sum += elapse['elapse_sum']
            # print stats.occurrence_total, elapse
            stats.elapse_avg = stats.elapse_sum / stats.occurrence_total

    # 更新 错误统计
    all_exc = [(key[0], key[1], key[2], exc) for key, exc in
               STATS_EXC_CLIENT.items()]
    STATS_EXC_CLIENT = {}
    all_exc.extend([(key[0], -1, key[1], exc) for key, exc in
                    STATS_EXC.items()])
    STATS_EXC = {}
    # print 'Stats exceptions:', len(all_exc)
    for api_id, client_id, exc_trace, exc in all_exc:
        hash_id = str(hash(exc_trace))
        with transaction.manager:
            api = DBSession.query(TapApi).get(api_id)
            if not api:
                warnings.warn("API:%s is not exist." % api_id)
                continue

            q = DBSession.query(TapApiErrors)\
                .filter_by(api_id=api_id, client_id=client_id, hash_id=hash_id)
            stats = q.first()
            if not stats:
                stats = TapApiErrors(api_id=api_id, client_id=client_id,
                                     project_id=api.project_id, hash_id=hash_id,
                                     occurrence_total=0,
                                     occurrence_time=occurrence_time,
                                     occurrence_first=exc['occurrence_first'])
                DBSession.add(stats)
                DBSession.flush()

            stats = DBSession.query(TapApiErrors).with_lockmode('update')\
                .filter(TapApiErrors.id==stats.id).first()
            stats.occurrence_time = occurrence_time
            # stats.occurrence_time = exc['occurrence_time']
            stats.occurrence_total += exc['occurrence_total']
            stats.exc_type = exc['exc_type']
            stats.exc_message = exc['exc_message']
            stats.exc_trace = exc_trace
            stats.exc_context = exc['exc_context']
            if exc['occurrence_first'] < stats.occurrence_first:
                stats.occurrence_first = exc['occurrence_first']
            if (not stats.occurrence_last
                or exc['occurrence_last'] > stats.occurrence_last):
                stats.occurrence_last = exc['occurrence_last']


def interval_vals(ivalue):
    assert ivalue in ['1M', '5M', '10M', '30M', '1H']

    _actpoint = []
    if ivalue == '1M':
        _actpoint = [(i, 00) for i in range(60)]
    elif ivalue == '5M':
        _actpoint = [
            (0, 00), (5, 00),
            (10, 00), (15, 00),
            (20, 00), (25, 00),
            (30, 00), (35, 00),
            (40, 00), (45, 00),
            (50, 00), (55, 00),
        ]
    elif ivalue == '10M':
        _actpoint = [
            (0, 00),
            (10, 00),
            (20, 00),
            (30, 00),
            (40, 00),
            (50, 00),
        ]
    elif ivalue == '30M':
        _actpoint = [
            (30, 00), (00, 00)
        ]
    elif ivalue == '1H':
        _actpoint = [
            (59, 59)
        ]

    oneday = []
    for i in range(24):
        for j in range(len(_actpoint)):
            point = _actpoint[j]
            oneday.append(
                (i, point[0], point[1])
            )
    oneday.sort()
    return oneday


def interval_flush(ivalue):
    while 1:
        try:
            _interval_flush(ivalue)
        except:
            import traceback
            traceback.print_exc()
            from raven import Client
            sentry = Client('http://80bb9d1abcf94d048ca29aa8b9a236d1:0a0bb7d150424a81ba3ca04935e9a7ff@sentry.iqnode.cn/6')
            sentry.captureException()


def _interval_flush(ivalue):
    oneday = interval_vals(ivalue)

    _oneday = copy.deepcopy(oneday)
    time_awake = None
    while True:
        try:
            if time_awake:
                flush_log(datetime.datetime(time_awake.year,
                                            time_awake.month, time_awake.day,
                                            time_awake.hour, time_awake.minute))
        except:
            import traceback
            traceback.print_exc()
            from raven import Client
            sentry = Client('http://80bb9d1abcf94d048ca29aa8b9a236d1:0a0bb7d150424a81ba3ca04935e9a7ff@sentry.iqnode.cn/6')
            sentry.captureException()
        finally:
            time.sleep(1)

        # 根据 interval value 确定 sleep 时间
        try:
            now = datetime.datetime.now()
            now_datetime = (now.hour, now.minute, now.second)
            interval = None
            if _oneday:
                time_point = _oneday.pop(0)
                while _oneday:
                    if now_datetime > time_point:
                        time_point = _oneday.pop(0)
                        continue
                    time_awake = datetime.datetime(now.year, now.month, now.day,
                                                   time_point[0], time_point[1],
                                                   time_point[2])
                    interval = (time_awake - now).seconds
                    break
            if interval is None:
                nextday = now + datetime.timedelta(days=1)
                _oneday = copy.deepcopy(oneday)
                time_point = _oneday.pop(0)
                time_awake = datetime.datetime(nextday.year, nextday.month,
                                               nextday.day, time_point[0],
                                               time_point[1], time_point[2])
                interval = (time_awake - now).seconds
        except:
            import traceback
            traceback.print_exc()
            from raven import Client
            sentry = Client('http://80bb9d1abcf94d048ca29aa8b9a236d1:0a0bb7d150424a81ba3ca04935e9a7ff@sentry.iqnode.cn/6')
            sentry.captureException()
        print 'Today:', now, len(_oneday), ivalue, interval
        time.sleep(interval)


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


PORT = 10101


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
        self.client = TapService.Client(protocol)

        self.transport.open()

    @client_ensure
    def report(self, params):
        self.client.report(params)

    def close(self):
        self.transport.close()


def run_server():
    processor = TapService.Processor(Handler())
    transport = TSocket.TServerSocket(port=PORT)
    tfactory = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()

    #server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)

    # You could do one of these for a multithreaded server
    server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
    #server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)

    print 'Starting the server...'
    server.serve()
    print 'Starting done.'


clients = {}


def get_client(host='127.0.0.1', force_new=False):
    now = time.time()
    if host not in clients or clients[host][1] > now or force_new:
        client = Client(host)
        expire = now + 60*10
        clients[host] = (client, expire)
    return clients[host][0]


def main():
    init_session_from_cmd()

    backend = threading.Thread(target=interval_flush, args=('1M',))
    backend.daemon = True
    backend.start()

    run_server()

