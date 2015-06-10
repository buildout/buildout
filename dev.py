##############################################################################
#
# Copyright (c) 2005 Zope Foundation and Contributors.
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
"""

import os, shutil, sys, subprocess

for d in 'eggs', 'develop-eggs', 'bin', 'parts':
    if not os.path.exists(d):
        os.mkdir(d)

if os.path.isdir('build'):
    shutil.rmtree('build')

######################################################################
# Make sure we have a relatively clean environment
try:
    import pkg_resources, setuptools
except ImportError:
    pass
else:
    raise SystemError(
        "Buildout development with a pre-installed setuptools or "
        "distribute is not supported.")

######################################################################
# Install distribute
ez = {}

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

# XXX use a more permanent ez_setup.py URL when available.
exec(urlopen('https://bootstrap.pypa.io/ez_setup.py').read(), ez)
ez['use_setuptools'](to_dir='eggs', download_delay=0)

import pkg_resources, setuptools
setuptools_path = os.path.dirname(os.path.dirname(setuptools.__file__))

######################################################################
# Install buildout
if subprocess.call(
    [sys.executable] +
    ['setup.py', '-q', 'develop', '-m', '-x', '-d', 'develop-eggs'],
    env=dict(os.environ, PYTHONPATH=setuptools_path)):
    raise RuntimeError("buildout build failed.")

pkg_resources.working_set.add_entry('src')

import zc.buildout.easy_install
zc.buildout.easy_install.scripts(
    ['zc.buildout'], pkg_resources.working_set , sys.executable, 'bin')

bin_buildout = os.path.join('bin', 'buildout')

if sys.platform.startswith('java'):
    # Jython needs the script to be called twice via sys.executable
    assert subprocess.Popen([sys.executable] + [bin_buildout]).wait() == 0

if sys.version_info < (2, 6):
    bin_buildout = [bin_buildout, '-c2.4.cfg']
sys.exit(subprocess.Popen(bin_buildout).wait())
