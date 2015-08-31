#coding=utf8
__author__ = 'cada'


import time
import cPickle

from pyramid_dogpile_cache import get_region

from tap.service.common import conn_get


tap_cache = get_region('tap')


def _persistence_db(dbtype, connstring, options):
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


def cache_fn(config, func, *args, **kwargs):
    if not config.cache_time or not config.cache_time > 0:
        return func(*args, **kwargs)

    # 生成key
    key = "val.%(project_name)s.%(api_name)s.%(paras)s"
    project_name = config.project.name.encode('utf8')
    api_name = config.name.encode('utf8')
    paras = list(args)
    paras.extend([(k, v) for k, v in kwargs.items()])
    paras = str(hash(repr(paras))).replace('-', '_')
    key = key % (dict(project_name=project_name, api_name=api_name,
                      paras=paras))

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

