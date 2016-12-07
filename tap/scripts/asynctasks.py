#!/usr/bin/env python
#coding=utf8
"""
author: Vincent@Home
"""

import os
import sys
import subprocess
import time
import signal
import tempfile
import collections
import datetime

import transaction
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

import xlrd
import simplejson as json
from celery import Celery
from sqlalchemy import engine_from_config

from tap.common.character import _print, _cs
from tap.service.common import conn_get
from tap.models import (
    Base, DBSession, TapAsyncTask, TapDBConn
)


# setup_logging(config_uri)
from tap.server import globalsettings
settings = globalsettings

if settings is None:  # 'celery' in repr(sys.argv):
    config_uri = sys.argv[1]
    if config_uri == '-A':
        config_uri = os.environ['CONFIG_URI']
        # print 'os.environ:', config_uri
    else:
        config_uri = os.path.abspath(config_uri)
        os.environ['CONFIG_URI'] = config_uri

    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)


app = Celery('tap.scripts.tasks', broker='sqla+' + settings['sqlalchemy.url'])


def start_celeryworker():
    process = subprocess.Popen(
        'celery -A tap.scripts.asynctasks worker --loglevel=info',
        shell=True
    )

    def handle_sig(signum, frame):
        process.send_signal(signal.SIGTERM)
        sys.exit(0)
    signal.signal(signal.SIGTERM, handle_sig)
    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGABRT, handle_sig)
    signal.signal(signal.SIGQUIT, handle_sig)
    signal.signal(signal.SIGHUP, handle_sig)

    while True:
        time.sleep(1)


@app.task
def upload_excel(task_id):
    ExcelHandler.log_print(task_id, '')
    try:
        ExcelHandler.upload(task_id)
    except BaseException, e:
        import traceback
        traceback.print_exc()
        ExcelHandler.upload_status(task_id, u'FAIL', unicode(e))


def as_object(val):
    class OBJ:
        pass
    obj = OBJ()
    for attr in dir(val):
        if attr.startswith('_'):
            continue
        setattr(obj, attr, getattr(val, attr))
    return obj


class ExcelHandler(object):
    @classmethod
    def upload(cls, task_id):
        ExcelHandler.upload_status(task_id, u'RUNNING', u'upload start')
        with transaction.manager:
            task = DBSession.query(TapAsyncTask).get(task_id)
            dbconn_id = json.loads(task.parameters)['dbconn_id']
            file_path = tempfile.mkstemp(prefix='tap')[1]
            with open(file_path, 'wb') as save_file:
                save_file.write(task.attachment)

        # open workbook
        workbook = xlrd.open_workbook(file_path)
        sheet_index = workbook.sheet_by_name('INDEX')
        first_col = sheet_index.row_values(0)
        assert (
            'SHEET_NAME' in first_col
            and 'TABLE_NAME' in first_col
            and 'UKEY' in first_col
            and 'HEADER_INDEX' in first_col
        )

        # prepare header
        col_index = collections.namedtuple('INDEX', 'SHEET_NAME,TABLE_NAME,UKEY,'
                                                    'HEADER_INDEX,IGNORE_COLS,'
                                                    'IGNORE_ROWS,DEL_HEADERNAME')
        col = col_index(
            first_col.index('SHEET_NAME'),
            first_col.index('TABLE_NAME'),
            first_col.index('UKEY'),
            int(first_col.index('HEADER_INDEX')),
            first_col.index('IGNORE_COLS') if 'IGNORE_COLS' in first_col else None,
            first_col.index('IGNORE_ROWS') if 'IGNORE_ROWS' in first_col else None,
            first_col.index('DEL_HEADERNAME') if 'DEL_HEADERNAME' in first_col
                                              else None
        )

        # read index sheet
        report = u""
        for i in range(1, sheet_index.nrows):
            config = sheet_index.row_values(i)
            if len(config) < 4:
                continue
            sheet_name = config[col.SHEET_NAME]
            if not sheet_name:
                continue
            config = col_index(
                sheet_name, config[col.TABLE_NAME], config[col.UKEY],
                int(config[col.HEADER_INDEX]) - 1,  # computer index
                '' if col.IGNORE_COLS is None else config[col.IGNORE_COLS],
                '' if col.IGNORE_ROWS is None else config[col.IGNORE_ROWS],
                (None if col.DEL_HEADERNAME is None else
                 config[col.DEL_HEADERNAME].strip())
            )
            config = as_object(config)
            config.IGNORE_ROWS = [r for r in str(config.IGNORE_ROWS).split(',')]
            config.IGNORE_ROWS = [float(r.strip()) for r in config.IGNORE_ROWS
                                  if r.strip()]
            config.IGNORE_ROWS = [int(r) for r in config.IGNORE_ROWS]
            config.IGNORE_ROWS.append(config.HEADER_INDEX + 1)  # human index
            config.IGNORE_COLS = [c for c in str(config.IGNORE_COLS).split(',')]
            config.IGNORE_COLS = [float(c.strip()) for c in config.IGNORE_COLS
                                  if c.strip()]
            config.IGNORE_COLS = [int(c) for c in config.IGNORE_COLS]

            # read excel
            cls.log_print(task_id, "load sheet:", sheet_name, config.TABLE_NAME)
            sheet = workbook.sheet_by_name(sheet_name)
            unique_keys, upsert, delete = cls.load_sheet(sheet, config)
            cls.log_print(task_id, "import data", sheet_name, config.TABLE_NAME)
            if not upsert and not delete:
                report += u"[%s-%s]: insert %s, update %s, delete %s\n" % \
                          (config.TABLE_NAME, sheet_name, 0, 0, 0)
                continue
            cnt_i, cnt_u, cnt_d = cls.import_data(dbconn_id, config, unique_keys,
                                                  upsert, delete)
            report += u"[%s-%s]: insert %s, update %s, delete %s\n" % \
                      (config.TABLE_NAME, sheet_name, cnt_i, cnt_u, cnt_d)
        ExcelHandler.upload_status(task_id, u'DONE', report)

    @classmethod
    def log_print(cls, task_id, *kargs):
        print task_id, ' '.join([_cs(v) for v in kargs])
        with transaction.manager:
            t = DBSession.query(TapAsyncTask).get(task_id)
            t.message = ' '.join([_cs(v) for v in kargs])
            t.message = t.message.decode('utf8')

    @classmethod
    def upload_status(cls, task_id, status, message):
        print task_id, message
        with transaction.manager:
            t = DBSession.query(TapAsyncTask).get(task_id)
            t.status = status
            t.message = message

    @classmethod
    def load_sheet(cls, sheet, config):
        """

        :param sheet:
        :param config:
        :return: unique keys, upsert rows, delete rows
        """
        header = sheet.row_values(config.HEADER_INDEX)
        header = [h.strip() if isinstance(h, (str, unicode)) else None for h in
                  header]
        unique_keys = [k.strip().lower() for k in config.UKEY.split(',')]
        while '' in unique_keys:
            unique_keys.remove('')
        for key in unique_keys:
            assert key in header, "%s should in header columns" % str(key)
        unique_index = [header.index(k) for k in unique_keys]
        unique_index = dict(zip(unique_keys, unique_index))

        # headers
        cols = [h if isinstance(h, (str, unicode)) else None for h in header]
        while None in cols:
            cols.remove(None)
        cols = [c.strip() for c in cols]
        cols = [c for c in cols if c not in config.IGNORE_COLS]
        cols = [c for c in cols if c != config.DEL_HEADERNAME]
        col_index = [header.index(c) for c in cols]
        cols = dict(zip(cols, col_index))
        if not cols:
            return unique_keys, [], []

        del_index = None
        if config.DEL_HEADERNAME:
            for header_name in header:
                if not isinstance(header_name, (str, unicode)):
                    continue
                if header_name.strip() == config.DEL_HEADERNAME:
                    del_index = header.index(header_name)
                    break
            assert del_index is not None

        # assemble data
        upsert = []
        delete = []

        col_length = len(cols)
        for i in range(sheet.nrows):
            if i + 1 in config.IGNORE_ROWS:
                continue
            row = sheet.row(i)
            if len(row) < col_length:
                continue
            row = cls.excel_row(row)
            if del_index is not None \
                    and isinstance(row[del_index], (str, unicode)) \
                    and row[del_index] == 'D':
                val = {}
                for col, idx in unique_index.items():
                    val[col] = row[idx]
                delete.append(val)
            else:
                val = {}
                for col, idx in cols.items():
                    val[col] = row[idx]
                upsert.append(val)
        return unique_keys, upsert, delete

    @classmethod
    def excel_row(cls, row):
        result = []
        tuple_2_date = lambda tup: datetime.date(tup[0], tup[1], tup[2])
        for i in range(len(row)):
            cell = row[i]
            if cell.ctype == xlrd.XL_CELL_DATE:
                result.append(
                    tuple_2_date(xlrd.xldate.xldate_as_tuple(cell.value, 0))
                )
            else:
                result.append(cell.value)
        return result

    @classmethod
    def import_data(cls, dbconn_id, config, unique_keys, upsert, delete):
        """

        :param task:
        :param config:
        :param unique_keys:
        :param upsert:
        :param delete:
        :return: count of (insert, update, delete)
        """
        with transaction.manager:
            dbconn = DBSession.query(TapDBConn).get(dbconn_id)
            conn = conn_get(dbconn.dbtype, dbconn.connstring, dbconn.options)
            cursor = conn.cursor()

            if dbconn.dbtype == 'MYSQL':
                return cls.import_data_mysql(
                    config, cursor, unique_keys, upsert, delete
                )

    @classmethod
    def import_data_mysql(cls, config, cursor, unique_keys, upsert, delete):
        # upsert
        cnt_insert, cnt_update, cnt_delete = 0, 0, 0
        where = " and ".join(["%s=%%(%s)s" % (k, k) for k in unique_keys])
        sql_chk = "select 1 from %s where %s limit 1"
        sql_chk = sql_chk % (config.TABLE_NAME, where)
        sql_insert = "insert into %s (%s) values(%s)"
        cols = upsert[0].keys()
        vals = ",".join(["%%(%s)s" % (k, ) for k in cols])
        sql_cols = ",".join(cols)
        sql_insert = sql_insert % (config.TABLE_NAME, sql_cols, vals)
        sql_update = "update %s set %s where %s"
        sql_update_ = ",".join(["%s=%%(%s)s" % (k, k) for k in cols])
        sql_update = sql_update % (config.TABLE_NAME, sql_update_, where)
        for row in upsert:
            cursor.execute(sql_chk, row)
            result = cursor.fetchone()
            if not result:
                cursor.execute(sql_insert, row)
                cnt_insert += 1
            else:
                cursor.execute(sql_update, row)
                cnt_update += 1

        # delete
        if delete:
            sql = "delete from %s where %s"
            sql = sql % (config.TABLE_NAME, where)
            cnt_delete = cursor.executemany(sql, delete)

        cursor.execute("commit")
        return cnt_insert, cnt_update, cnt_delete

if __name__ == '__main__':
    upload_excel(6)
