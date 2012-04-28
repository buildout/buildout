##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

# parsing arguments
parser = OptionParser(
    'This is a custom version of the zc.buildout %prog script.  It is '
    'intended to meet a temporary need if you encounter problems with '
    'the zc.buildout 1.5 release.')
parser.add_option("-v", "--version", dest="version", default='1.4.4',
                          help='Use a specific zc.buildout version.  *This '
                          'bootstrap script defaults to '
                          '1.4.4, unlike usual buildpout bootstrap scripts.*')
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

ws  = pkg_resources.working_set

requirement = 'distribute'

env = dict(os.environ,
           PYTHONPATH=
           ws.find(pkg_resources.Requirement.parse(requirement)).location
           )

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

if 'bootstrap-testing-find-links' in os.environ:
    cmd.extend(['-f', os.environ['bootstrap-testing-find-links']])

cmd.append('zc.buildout' + VERSION)

import subprocess
if subprocess.call(cmd, env=env) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)
