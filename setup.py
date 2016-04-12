import os
import sys
import shutil

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()
shutil.rmtree('tap/static/doc', ignore_errors=True)
shutil.copytree('doc/build/html', 'tap/static/doc')

requires = [
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'waitress',
    'mako',
    'pyramid_mako',
    'simplejson',
    'python-dateutil',
    'python-memcached',
    'pyramid_dogpile_cache',
    'thrift',
    'xlrd',
    'celery==3.1.20',
    ]
if sys.version_info < (2, 7):
    requires.append('ordereddict')

setup(name='tap',
      version='0.3.3',
      description='tap',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='tap',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = tap:main
      [console_scripts]
      tap_worker = tap.scripts.worker:start
      tap_initdb = tap.scripts.initializedb:main
      tap_dbconnupdate = tap.scripts.dbtools:check_dbconn
      tap_stats = tap.service.rpcstats:main
      tap_dump = tap.scripts.dbtools:tap_dump
      tap_import = tap.scripts.dbtools:tap_import
      """,
      )
