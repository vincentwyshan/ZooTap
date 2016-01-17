#!/usr/bin/env python
#coding=utf8
__author__ = 'Vincent@Home'


HOSTS = [
    '192.168.1.4:1717',
    '192.168.1.5:1717',
    '192.168.1.6:1717',
]

import os
import json
import datetime
import subprocess


def stats():
    data = [
        ['HOST', 'TOTAL_REQ', 'AVG', 'RSS', 'TX', 'LAST_SPAWN']
    ]
    for host in HOSTS:
        process = subprocess.Popen("uwsgi --connect-and-read %s" % host,
                                   shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout = process.communicate()[1]
        result = None
        try:
            result = json.loads(stdout)
        except:
            pass

        if not result:
            data.append([host, None])
            continue
        data.append(
            [host,
             sum([w['requests'] for w in result['workers']]),
             int(round(sum([w['avg_rt'] for w in result['workers']]) / (len(result['workers']) * 1000), 0)),
             int(round(sum([w['rss'] for w in result['workers']]) / (1024*1024), 0)),
             int(round(sum([w['tx'] for w in result['workers']]) / (1024*1024), 0)),
             datetime.datetime.fromtimestamp(max([w['last_spawn'] for w in result['workers']]))
             ]
        )

    for row in data:
        if len(row) == 2:
            print bcolors.FAIL + row[0].ljust(23, ' '), 'Not available', \
                bcolors.ENDC
            continue
        host = row[0]
        total_req = str(row[1])
        avg = str(row[2])
        if data.index(row) > 0:
            avg += 'ms'
        rss = str(row[3])
        if data.index(row) > 0:
            rss += 'M'
        tx = str(row[4])
        if data.index(row) > 0:
            tx += 'M'
        last_spawn = str(row[5])
        print host.ljust(23, ' '), total_req.ljust(11, ' '), \
            avg.ljust(9, ' '), rss.ljust(9, ' '), tx.ljust(9, ' '), \
            last_spawn.ljust(16, ' ')


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


if __name__ == '__main__':
    stats()
