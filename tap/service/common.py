#coding=utf8

__author__ = 'Vincent@Home'

import time
import datetime
import decimal
import urllib
from contextlib import contextmanager
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import simplejson as json


def conn_get(dbtype, connstring, options=None):
    conn = None

    # parse options
    options = options.strip()
    options = options.split('\n')
    options = dict([v.split('=') for v in options if v.strip()])
    # options = {k.strip(): v.strip() for k, v in options.items()}
    options = [(str(k.strip), v.strip) for k, v in options.items()]
    options = dict(options)

    if dbtype == 'MYSQL':
        conns = connstring.split(';')
        conns = [v.split('=') for v in conns]
        conns = dict([(str(k), v) for k, v in conns])
        if 'port' in conns:
            conns['port'] = int(conns['port'])
        import MySQLdb
        conns.update(options)
        conn = MySQLdb.connect(**conns)
    elif dbtype == 'ORACLE':
        import cx_Oracle
        conn = cx_Oracle.connect(connstring, **options)
    elif dbtype == 'PGSQL':
        import psycopg2
        conn = psycopg2.connect(connstring, **options)
    elif dbtype == 'MSSQL':
        import pyodbc
        conn = pyodbc.connect(connstring, **options)
    elif dbtype == 'MONGODB':
        conns = connstring.split(';')
        conns = [v.split('=') for v in conns]
        conns = dict([(str(k), v) for k, v in conns])
        import pymongo
        conn = pymongo.MongoClient(**conns)
    return conn


def dbconn_ratio_parse(dbconn_ratio):
    """dbconn_ratio example:
    PRIMARYDB=PRIMARYDB:20,SECONDARYDB1:40,SECONDARYDB2:40;
    :rtype: {PRIMARYDB.name: {db.name: ratio}}
    """
    if not dbconn_ratio:
        return None
    sections = [s.strip() for s in dbconn_ratio.split(';') if s.strip()]
    result = {}
    for section in sections:
        name, config = section.split('=')
        config = dict([cfg.split(':') for cfg in config.split(',')])
        for k, v in config.items():
            config[k] = int(v)
        result[name] = config
    return result

@contextmanager
def measure():
    start = time.time()
    end = 0
    elapse = lambda: end - start
    yield lambda: elapse()
    end = time.time()


def api2dict(api):
    result = dict(
        id=api.id,
        name=api.name,
        cnname=api.cnname,
        description=api.description,
        cache_time=api.cache_time,
        writable=api.writable,
        auth_type=api.auth_type,
        uid_create=api.uid_create,
        uid_update=api.uid_update,
        project_id=api.project_id,
        created=api.created,
        timestamp=api.timestamp,
        paras=[],
        auth_clients=[],
        project=dict(
            name=api.project.name,
            cnname=api.project.name,
            created=api.project.created,
            timestamp=api.project.timestamp
        ),
        cache_persistencedb=dict(
            id=api.cache_persistencedb and api.cache_persistencedb.id,
            name=api.cache_persistencedb and api.cache_persistencedb.name,
            dbtype=api.cache_persistencedb and api.cache_persistencedb.dbtype,
            connstring=api.cache_persistencedb and api.cache_persistencedb.connstring,
            options=api.cache_persistencedb and api.cache_persistencedb.options,
            uid_create=api.cache_persistencedb and api.cache_persistencedb.uid_create,
            description=api.cache_persistencedb and api.cache_persistencedb.description,
            created=api.cache_persistencedb and api.cache_persistencedb.created,
            timestamp=api.cache_persistencedb and api.cache_persistencedb.timestamp
        ),
        dbconn=[],
        dbconn_secondary=[],
        dbconn_ratio=api.dbconn_ratio,
        source=dict(
            id=api.source.id,
            source=api.source.source,
            source_type=api.source.source_type,
            created=api.source.created,
            timestamp=api.source.timestamp
        )
    )
    conns = api.dbconn
    if hasattr(api, 'get_dbconn'):
        conns = api.get_dbconn()
    for dbconn in conns:
        result['dbconn'].append(dict(
            id=dbconn.id,
            name=dbconn.name,
            dbtype=dbconn.dbtype,
            connstring=dbconn.connstring,
            options=dbconn.options,
            uid_create=dbconn.uid_create,
            description=dbconn.description,
            created=dbconn.created,
            timestamp=dbconn.timestamp
        ))
    conns_secondary = api.dbconn_secondary
    if hasattr(api, 'get_dbconn_secondary'):
        conns_secondary = api.get_dbconn_secondary()
    for conn in conns_secondary:
        result['dbconn_secondary'].append(dict(
            id=conn.id,
            name=conn.name,
            dbtype=conn.dbtype,
            connstring=conn.connstring,
            options=conn.options,
            uid_create=conn.uid_create,
            description=conn.description,
            created=conn.created,
            timestamp=conn.timestamp
        ))
    for para in api.paras:
        result['paras'].append(dict(
            id=para.id,
            name=para.name,
            val_type=para.val_type,
            default=para.default,
            absent_type=para.absent_type,
            created=para.created,
            timestamp=para.created
        ))

    for auth in api.auth_clients:
        # 这里 save 下来的 token 不能使用
        result['auth_clients'].append(dict(
            id=auth.id, client_id=auth.client_id, token=auth.token,
            uid_auth=auth.uid_auth, #disable=auth.disable,
            created=auth.created, timestamp=auth.timestamp
        ))

    return result

    id = Column(Integer, Sequence('seq_tapapiauth_id'), primary_key=True)
    api_id = Column(Integer, ForeignKey('tap_api.id'))
    api = relationship('TapApi', backref='auth_clients')
    client_id = Column(Integer, ForeignKey('tap_apiclient.id'), nullable=False)
    auth_client = relationship('TapApiClient', backref='auth_list')
    token = Column(Unicode(38), nullable=False)
    uid_auth = Column(Integer, ForeignKey('tap_user.id'))
    user_auth = relationship('TapUser', backref='auth_apis')
    disable = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)


def dict2api(api_in_dict):
    class Temp:
        pass

    def dict2obj(_dict):
        result = Temp()
        for _name, _value in _dict.items():
            setattr(result, _name, _value)
        return result

    result = Temp()
    for name, value in api_in_dict.items():
        if isinstance(value, dict):
            attr = dict2obj(value)
            setattr(result, name, attr)
        elif isinstance(value, list):
            attr = []
            for _value in value:
                attr.append(dict2obj(_value))
            setattr(result, name, attr)
        else:
            setattr(result, name, value)

    return result

def cu(val, encoding=None):
    if encoding:
        return val.decode(encoding)
    try:
        val = val.decode('utf-8')
    except UnicodeDecodeError:
        val = val.decode('gb18030', 'ignore')
    return val

class CadaEncoder(json.JSONEncoder):
    def default(self, v):
        if isinstance(v, datetime.date):
            return str(v)
        elif isinstance(v, datetime.datetime):
            return str(v)
        elif isinstance(v, decimal.Decimal):
            return str(v)
        elif v is None:
            return 'null'
        else:
            pass
        return json.JSONEncoder.default(self, v)



class FIFODict(OrderedDict):

    def __init__(self, capacity):
        super(FIFODict, self).__init__()
        self._capacity = capacity

    def __setitem__(self, key, value):
        contains_key = 1 if key in self else 0
        if len(self) - contains_key >= self._capacity:
            last = self.popitem(last=False)
            del last
            # print 'remove:', last
        if contains_key:
            del self[key]
            # print 'set:', (key, value)
        else:
            # print 'add:', (key, value)
            pass
        OrderedDict.__setitem__(self, key, value)


def show_tables(dbtype, cursor):
    if dbtype == 'MYSQL':
        cursor.execute("show table status")
    elif dbtype == 'MSSQL':
        cursor.execute("""
SELECT *
FROM (
    SELECT
        TableName   = t.TABLE_SCHEMA + '.' + t.TABLE_NAME
        ,[RowCount] = SUM(sp.[ROWS])
        ,Megabytes  = (8 * SUM(CASE WHEN sau.TYPE != 1 THEN sau.used_pages WHEN sp.index_id < 2 THEN sau.data_pages ELSE 0 END)) / 1024
    FROM INFORMATION_SCHEMA.TABLES t
    JOIN sys.partitions sp
        ON sp.object_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
    JOIN sys.allocation_units sau
        ON sau.container_id = sp.partition_id
    WHERE TABLE_TYPE = 'BASE TABLE'
    GROUP BY
        t.TABLE_SCHEMA + '.' + t.TABLE_NAME
) A
ORDER BY TableName
        """)
    elif dbtype == 'ORACLE':
        cursor.execute("select * from user_tables")

    cols = [c[0] for c in cursor.description]
    rows = list(cursor.fetchall())
    rows.insert(0, cols)
    return rows


_fifo_stmt = FIFODict(100)
_end_chr = ';'
def stmt_split(string):
    result = _fifo_stmt.get(string)
    if result:
        return [v for v in result]
    result = []
    chars = list(string.strip())
    open_str_s = 2  # single quote string
    open_str_d = 6  # double quote string
    open_brace = 4
    open_comment_s = 8
    open_comment_m = 10
    qs = []  # Quote status
    temp = []
    while chars:
        c = chars.pop(0)
        # Comments handling
        if qs and qs[-1] in (open_comment_s, open_comment_m):
            if qs[-1] == open_comment_s and c=='\n':
                # Close COMMENT_S
                temp.append(c)
                qs.pop()
            elif qs[-1] == open_comment_m and c== '*' and chars[0]=='/':
                # Close COMMENT_M
                qs.pop()
                chars.pop(0)
            else:
                # Using blank replace comments-string
                temp.append(' ')
            continue
        # Not in string
        elif not qs or qs[-1] not in (open_str_s, open_str_d):
            # Single line comments
            if c == '-' and chars[0] == '-':
                qs.append(open_comment_s)
                chars.pop(0)
                temp.append(' ')
                continue
            # Multi-line comments
            elif c == '/' and chars[0] == '*':
                qs.append(open_comment_m)
                chars.pop(0)
                temp.append(' ')
                continue
            else:
                pass

        temp.append(c)
        if len(qs) == 0 and c == _end_chr:
            result.append(''.join(temp))
            temp = []
        # escape
        elif c == '\\':
            c = chars.pop(0)
            # print("escape", c)
            temp.append(c)
        # escape
        elif c == "'" and chars and chars[0] == "'":
            temp.append(chars.pop(0))
        elif not (qs and qs[-1] in (open_str_d, open_str_s)) and c == "'":
            # print('open_str_s')
            qs.append(open_str_s)
        elif not (qs and qs[-1] in (open_str_d, open_str_s)) and c == '"':
            # print('open_str_d')
            qs.append(open_str_d)
        elif not (qs and qs[-1] in (open_str_d, open_str_s)) and c == '{':
            # print('open_brace')
            qs.append(open_brace)
        elif len(qs) > 0:
            if qs[-1] == open_str_s and c == "'":
                # print('CLOSE_STR_S')
                qs.pop()
            elif qs[-1] == open_str_d and c == '"':
                # print('CLOSE_STR_D')
                qs.pop()
            elif qs[-1] == open_brace and c == '}':
                # print('CLOSE_BRACE')
                qs.pop()
                if len(qs) == 0:
                    result.append(''.join(temp))
                    temp = []
            else:
                pass
    result.append(''.join(temp))
    result = [v.strip() for v in result if v.strip()]
    _fifo_stmt[string] = result
    return result[:]


class Paginator(object):
    total = 0
    num_per_page = 30
    current = 0
    offset = 3
    paras = {}
    p_argname = 'page'

    _prevlist = None
    _nextlist = None
    _page_total = None

    def __init__(self, current, total=None, num_per_page=None, p_argname=None,
                 paras=None, offset=None):
        """
        :param current: current page number, start from 1
        :param p_argname: pagination parameter name
        :param paras: other parameters, dictionary
        :param offset: show how many page numbers before and after current page
        """
        if total:
            self.total = total
        if num_per_page:
            self.num_per_page = num_per_page
        if current:
            self.current = current
        if p_argname:
            self.p_argname = p_argname
        if offset:
            self.offset = offset
        if paras:
            self.paras = paras
            for k, v in self.paras.items():
                assert isinstance(k, str)
                if not v:
                    self.paras[k] = ''
                if isinstance(v, unicode):
                    self.paras[k] = v.encode('utf8')

        if self.current > 1:
            self.show_prevbutton = True
        else:
            self.show_prevbutton = False

        if self.current < self.pages:
            self.show_nextbutton = True
        else:
            self.show_nextbutton = False

        if self.prevlist and self.prevlist[0] != 1:
            self.show_firstpage = True
        else:
            self.show_firstpage = False

        if self.nextlist and self.nextlist[-1] < self.pages:
            self.show_lastpage = True
        else:
            self.show_lastpage = False

    @property
    def pages(self):
        """total page number."""
        if self._page_total is not None:
            return self._page_total
        self._page_total = (self.total / self.num_per_page)
        if self.total % self.num_per_page != 0:
            self._page_total += 1
        return self._page_total

    @property
    def prevlist(self):
        """start number is 1"""
        if self._prevlist is not None:
            return self._prevlist

        self._prevlist = []
        _prev = self.current
        while len(self._prevlist) < self.offset:
            _prev -= 1
            if _prev < 1:
                break
            self._prevlist.insert(0, _prev)
        return self._prevlist

    @property
    def nextlist(self):
        """start number is 1"""
        if self._nextlist is not None:
            return self._nextlist

        self._nextlist = []
        _next = self.current
        while len(self._nextlist) < self.offset:
            _next += 1
            if _next > self.pages:
                break
            self._nextlist.append(_next)
        return self._nextlist

    def param(self, page, kwarg={}):
        """
        encode url parameters with given `page` number.
        """
        paras = {}
        paras.update(self.paras)
        paras.update(kwarg)
        paras[self.p_argname] = page
        paras = urllib.urlencode(paras)
        return paras
