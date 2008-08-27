##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors.
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
"""Bootstrap the buildout project itself.

This is different from a normal boostrapping process because the
buildout egg itself is installed as a develop egg.

$Id$
"""

import os, sys, urllib2

is_jython = sys.platform.startswith('java')

if is_jython:
    import subprocess

for d in 'eggs', 'develop-eggs', 'bin':
    if not os.path.exists(d):
        os.mkdir(d)

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir='eggs', download_delay=0)

    import pkg_resources

if is_jython:
    subprocess.Popen([sys.executable] + ['setup.py', '-q', 'develop', '-m', '-x',
                        '-d', 'develop-eggs'], 
                        env = {'PYTHONPATH': os.path.dirname(pkg_resources.__file__)}).wait()
else:
    os.spawnle(os.P_WAIT, sys.executable, sys.executable, 'setup.py',
               '-q', 'develop', '-m', '-x', '-d', 'develop-eggs',
               {'PYTHONPATH': os.path.dirname(pkg_resources.__file__)},
               )

pkg_resources.working_set.add_entry('src')

import zc.buildout.easy_install
zc.buildout.easy_install.scripts(
    ['zc.buildout'], pkg_resources.working_set , sys.executable, 'bin')

bin_buildout = os.path.join('bin', 'buildout')

if is_jython:
    # Jython needs the script to be called twice via sys.executable
    assert subprocess.Popen([sys.executable] + [bin_buildout]).wait() == 0
    sys.exit(subprocess.Popen([sys.executable] + [bin_buildout]).wait())
else:
    sys.exit(os.spawnl(os.P_WAIT, bin_buildout, bin_buildout))
