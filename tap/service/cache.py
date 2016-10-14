#coding=utf8
__author__ = 'Vincent.Wen'


import time
import cPickle

from dogpile.cache.api import NoValue
from pyramid_dogpile_cache import get_region

from tap.service.common import conn_get
from tap.service.interpreter import ParaHandler


tap_cache = get_region('tap')


def get_val(key, expire):
    data = tap_cache.get(key, expiration_time=expire)

    if isinstance(data, NoValue):
        return None

    return data


def set_val(key, value):
    return tap_cache.set(key, value)


def _persistence_db(dbtype, connstring, options):
    # 只支持 MongoDB
    try:
        key = (dbtype, connstring, options)
        if key in _persistence_db_cache:
            return _persistence_db_cache[key]
        client = conn_get(dbtype, connstring, options)
        db = client.tap
        collection = db.persistance_cache
        _persistence_db_cache[key] = collection
        return collection
    except:
        pass
_persistence_db_cache = {}


def cache_key(config, version, *args, **kwargs):
    # 生成key
    key = "val.%(project_name)s.%(api_name)s.%(version)s.%(paras)s"
    project_name = config.project.name.encode('utf8')
    api_name = config.name.encode('utf8')
    paras = list(args)
    paras.extend([(k, v) for k, v in kwargs.items()])
    paras = str(hash(repr(paras))).replace('-', '_')
    key = key % (dict(project_name=project_name, api_name=api_name,
                      paras=paras, version=version))
    return key


def cache_delete(config, version, paras):
    # from tap.service.apisuit import Program
    # program = Program(config, version)
    # paras = program._para_prepare(paras, config.paras)
    paras = ParaHandler.prepare(paras, config.paras)
    key = cache_key(config, version, paras)
    tap_cache.delete(key)


def cache_get(config, version, paras):
    # from tap.service.apisuit import Program
    # program = Program(config, version)
    # paras = program._para_prepare(paras, config.paras)
    paras = ParaHandler.prepare(paras, config.paras)
    key = cache_key(config, version, paras)
    data = tap_cache.get(key, expiration_time=config.cache_time,
                         ignore_expiration=False)
    if isinstance(data, NoValue):
        data = None
    return data


def cache_fn(config, version, func, *args, **kwargs):
    if not config.cache_time or not config.cache_time > 0:
        return func(*args, **kwargs)

    key = cache_key(config, version, *args, **kwargs)

    # 持久化缓存
    persistance = None
    now = None
    if config.cache_persistencedb and config.cache_persistencedb.id:
        try:
            persistance = _persistence_db(config.cache_persistencedb.dbtype,
                                          config.cache_persistencedb.connstring,
                                          config.cache_persistencedb.options)
            result = persistance.find_one({'key': key})
            now = time.time()
            if result and result['expire'] < now:
                return cPickle.loads(result['value'])
        except:
            import traceback; traceback.print_exc()

    def creator():
        return func(*args, **kwargs)

    def dont_cache_none(value):
        return value is not None

    result = tap_cache.get_or_create(key, creator,
                                     expiration_time=config.cache_time,
                                     should_cache_fn=dont_cache_none)
    # 持久化缓存
    if persistance and result:
        try:
            expire = now + config.cache_time
            value = {'key': key, 'value': result, 'expire': expire,
                     'timestamp': now}
            persistance.update_one({'key': key}, {'$set': value}, upsert=True)
        except:
            import traceback; traceback.print_exc()
    return result


def cache_fn1(expire):
    """
    cache common function
    :return:
    """
    def rcv_func(func):
        def wraper(*kargs, **kwarg):
            keys = list(kargs)
            keys.extend([(k, v) for k, v in kwarg.items()])
            keys.insert(0, func.__name__)
            key = 'fn.' + str(hash(repr(keys))).replace('-', '_')

            # TODO same cache request mutex
            def creator():
                return func(*kargs, **kwarg)

            def dont_cache_none(value):
                return value is not None

            return tap_cache.get_or_create(key, creator,
                                           expiration_time=expire,
                                           should_cache_fn=dont_cache_none)
        return wraper
    return rcv_func
