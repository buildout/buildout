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

This is different from a normal bootstrapping process because the
buildout egg itself is installed as a develop egg.

$Id$
"""

import os, shutil, sys, subprocess, urllib2

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if (hasattr(v, '__path__') and
        len(v.__path__)==1 and
        not os.path.exists(os.path.join(v.__path__[0],'__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

for d in 'eggs', 'develop-eggs', 'bin':
    if not os.path.exists(d):
        os.mkdir(d)

if os.path.isdir('build'):
    shutil.rmtree('build')

try:
    to_reload = False
    import pkg_resources
    to_reload = True
    import setuptools # A flag.  Sometimes pkg_resources is installed alone.
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir='eggs', download_delay=0)

    import pkg_resources
    if to_reload:
        reload(pkg_resources)

env = os.environ.copy() # Windows needs yet-to-be-determined values from this.
env['PYTHONPATH'] = os.path.dirname(pkg_resources.__file__)
subprocess.Popen(
    [sys.executable] +
    ['-S', 'setup.py', '-q', 'develop', '-m', '-x', '-d', 'develop-eggs'],
    env=env).wait()

pkg_resources.working_set.add_entry('src')

import zc.buildout.easy_install
if not os.path.exists('parts'):
    os.mkdir('parts')
partsdir = os.path.join('parts', 'buildout')
if not os.path.exists(partsdir):
    os.mkdir(partsdir)
zc.buildout.easy_install.sitepackage_safe_scripts(
    'bin', pkg_resources.working_set, sys.executable, partsdir,
    reqs=['zc.buildout'])

bin_buildout = os.path.join('bin', 'buildout')

if is_jython:
    # Jython needs the script to be called twice via sys.executable
    assert subprocess.Popen([sys.executable] + [bin_buildout]).wait() == 0


sys.exit(subprocess.Popen(bin_buildout).wait())
