#!/usr/bin/env python
#coding=utf8


import os
import urllib

URLS = [
    # 'http://127.0.0.1:8080/api/MERCHANTSSECURITIES/jjlb_jj_page?JJLX=GPX&pxzd=RZF&pagenum=1&perpage=10&pxfs=desc',
    'http://127.0.0.1:8080/management/project',
]


def check():
    for url in URLS:
        response = urllib.urlopen(url)
        if response.code != 200:
            # 重启服务
            print "restart service: uwsgi", url
            os.system("supervisorctl -c /etc/supervisord.ini restart uwsgi")


if __name__ == '__main__':
    check()
