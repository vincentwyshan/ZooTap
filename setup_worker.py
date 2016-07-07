import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'simplejson',
    'python-dateutil',
    'python-memcached',
    'pyramid_dogpile_cache',
    'thrift',
    'xlrd',
    'celery==3.1.20',
    'captcha',
    'psutil',
    'croniter',
    ]
if sys.version_info < (2, 7):
    requires.append('ordereddict')

import tap

setup(name='tap',
      version=tap.__version__,
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
      keywords='tap worker tools',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='tap',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = tap:main
      [console_scripts]
      """,
      )
