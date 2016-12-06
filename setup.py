import os
import sys
import shutil

import distutils.cmd
import distutils.log
from setuptools import setup, find_packages

import tap


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()


class TapCommand(distutils.cmd.Command):
    """
    Customize commands for setup scripts.
    """

    description = 'Tap commands'
    user_options = [
        # The format is (long option, short option, description).
        ('action=', 'a', 'Specify the action: [doc/extract_i18n]'),
    ]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        self.action = 'doc'

    def finalize_options(self):
        """Post-process options."""

    def run(self):
        """Run command."""
        if self.action == 'doc':
            shutil.rmtree('tap/static/doc', ignore_errors=True)
            shutil.copytree('doc/build/html', 'tap/static/doc')
        elif self.action == 'extract_i18n':
            os.system("pot-create  ./ -c ./lingua.ini -o tap/locale/tap.pot")

            prefix = '/usr/local/Cellar/gettext/0.19.7/bin/'
            cmd_cn = ("%smsgmerge --update "
                      "tap/locale/zh_CN/LC_MESSAGES/tap.po "
                      "tap/locale/tap.pot") % prefix
            cmd_en = ("%smsgmerge --update -q tap/locale/en/LC_MESSAGES/tap.po "
                      "tap/locale/tap.pot") % prefix
            self.announce(cmd_cn, distutils.log.INFO)
            os.system(cmd_cn)
            self.announce(cmd_en, distutils.log.INFO)
            os.system(cmd_en)


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
    'captcha',
    'babel',
]
if sys.version_info < (2, 7):
    requires.append('ordereddict')


setup(
    name='tap',
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
    keywords='web wsgi bfg pylons pyramid',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='tap',
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = tap.server:main
    [console_scripts]
    tap_worker = tap.scripts.worker:start
    tap_initdb = tap.scripts.initializedb:main
    tap_dbconnupdate = tap.scripts.dbtools:check_dbconn
    tap_stats = tap.service.rpcstats:main
    tap_dump = tap.scripts.dbtools:tap_dump
    tap_import = tap.scripts.dbtools:tap_import
    """,
    cmdclass={
        'tap': TapCommand
    }
)

# pot-create  ./ -o tap/locale/tap.pot
# msgmerge --update tap/locale/zh_CN/LC_MESSAGES/tap.po tap/locale/tap.pot
# msgmerge --update tap/locale/en/LC_MESSAGES/tap.po tap/locale/tap.pot
# msgfmt -o locale/zh_CN/LC_MESSAGES/tap.mo locale/zh_CN/LC_MESSAGES/tap.po
