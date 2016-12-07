#coding=utf8

from optparse import OptionParser

from tap.scripts.asynctasks import start_celeryworker


def start():
    """
    start worker entry point
    :return:
    """
    usage = "usage: %prog production.ini [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-w', '--worker', type="string", dest="worker",
                      help="specify which worker to start.")
    (options, args) = parser.parse_args()

    if options.worker == 'celery':
        start_celeryworker()
    else:
        parser.error("need worker name.")
