#coding=utf8
__author__ = 'Vincent.Wen'

import os
import sys
import datetime


def _cs(obj, encoding='utf8'):
    """
    convert any object to string object.
    main purpose: convert unicode to string
    """
    if isinstance(obj, unicode):
        return obj.encode(encoding)
    elif isinstance(obj, str):
        return obj
    else:
        return str(obj)


def _print(*args):
    """
    print with datetime
    """
    if not args:
        return
    encoding = 'utf8' if os.name == 'posix' else 'gbk'
    args = [_cs(a, encoding) for a in args]
    # f_back = None
    # try:
    #    raise Exception
    # except:
    #    f_back = sys.exc_traceback.tb_frame.f_back
    # f_name = f_back.f_code.co_name
    # filename = os.path.basename(f_back.f_code.co_filename)
    # m_name = os.path.splitext(filename)[0]
    # prefix = ('[%s.%s]'%(m_name, f_name)).ljust(20, ' ')
    if os.name == 'nt':
        for i in range(len(args)):
            v = args [i]
            if isinstance(v, str):
                args[i] = v #v.decode('utf8').encode('gbk')
            elif isinstance(v, unicode):
                args[i] = v.encode('gbk')
    # print '[%s]'%str(datetime.datetime.now()), prefix, ' '.join(args)
    print '[%s]' % str(datetime.datetime.now()), ' '.join(args)


def _print_err(*args):
    if not args:
        return
    encoding = 'utf8' if os.name == 'posix' else 'gbk'
    args = [_cs(a, encoding) for a in args]
    f_back = None
    try:
        raise Exception
    except:
        f_back = sys.exc_traceback.tb_frame.f_back
    f_name = f_back.f_code.co_name
    filename = os.path.basename(f_back.f_code.co_filename)
    m_name = os.path.splitext(filename)[0]
    prefix = ('[%s.%s]'%(m_name, f_name)).ljust(20, ' ')
    print bcolors.FAIL+'[%s]'%str(datetime.datetime.now()), prefix, ' '.join(args) + bcolors.ENDC


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


