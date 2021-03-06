#!/usr/bin/python
#coding:utf-8

import config
import msgpack
import logging
from redis import Redis
from redis import ConnectionPool
from utils.fn import create_obj

logger = logging.getLogger(__name__)

redis_pool = ConnectionPool(
    host = config.REDIS_HOST, \
    port = config.REDIS_PORT, \
    db = config.REDIS_DB, \
    password = config.REDIS_PASSWORD, \
    max_connections = config.REDIS_POOL_SIZE, \
)

rds = Redis(connection_pool = redis_pool)

local_cache = {}

def cache_obj(prefix, attrs):
    def wrap(f):
        def _(site, id, *args, **kwargs):
            params = {'sid': site.id, 'id': id}
            params.update(kwargs)
            cache_key = prefix.format(**params)
            obj = rds.get(cache_key)
            if obj is not None:
                logger.info('get obj from cache')
                if not obj:
                    return obj
                return create_obj(obj)
            else:
                logger.info('obj cache miss')
                obj = f(site, id, *args, **kwargs)
                value = ''
                if obj:
                    value = msgpack.dumps([(attr, getattr(obj, attr, None)) for attr in attrs], default=str)
                rds.set(cache_key, value)
                return obj
        return _
    return wrap

def cache_page(count_prefix, page_prefix, attrs):
    def wrap(f):
        def _(site, total, page, num, *args, **kwargs):
            params = {'sid': site.id, 'page': page, 'num': num}
            params.update(kwargs)
            page_key = page_prefix.format(**params)
            count_key = count_prefix.format(**params)
            count = rds.get(count_key)
            if count and int(count) == int(total):
                logger.info('get page from cache')
                result = rds.lrange(page_key, 0 ,-1)
                return (create_obj(r) for r in result)
            else:
                logger.info('page cache miss')
                rds.delete(page_key)
                data = f(site, total, page, num, *args, **kwargs)
                def iterator():
                    result = []
                    for item in data:
                        result.append(
                            msgpack.dumps(
                                [(key, getattr(item, key, None)) for key in attrs], \
                                default=str)
                        )
                        yield item
                    if result:
                        rds.rpush(page_key, *result)
                rds.set(count_key, total)
                return iterator()
        return _
    return wrap

