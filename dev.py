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

This is different from a normal bootstrapping process because the
buildout egg itself is installed as a develop egg.
"""

import os, shutil, sys, subprocess
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# Detect https://bugs.launchpad.net/virtualenv/+bug/572545 .
has_broken_dash_S = subprocess.call(
    [sys.executable, '-S', '-c', 'import pickle'])

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = list(map(quote, args))
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site
sys.path[:] = clean_path
for k, v in list(sys.modules.items()):
    if (hasattr(v, '__path__') and
        len(v.__path__)==1 and
        not os.path.exists(os.path.join(v.__path__[0],'__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setup_source = 'http://python-distribute.org/distribute_setup.py'

usage = '''\
[DESIRED PYTHON FOR DEVELOPING BUILDOUT] dev.py

Bootstraps buildout itself for development.

This is different from a normal bootstrapping process because the
buildout egg itself is installed as a develop egg.
'''



for d in 'eggs', 'develop-eggs', 'bin':
    if not os.path.exists(d):
        os.mkdir(d)
if os.path.isdir('build'):
    shutil.rmtree('build')

try:
    to_reload = False
    import pkg_resources
    to_reload = True
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
    import setuptools # A flag.  Sometimes pkg_resources is installed alone.
except ImportError:
    ez_code = urllib2.urlopen(setup_source).read().replace(
        '\r\n'.encode(), '\n'.encode())
    ez = {}
    exec(ez_code, ez)
    setup_args = dict(to_dir='eggs', download_delay=0, no_fake=True)
    ez['use_setuptools'](**setup_args)
    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

env = os.environ.copy() # Windows needs yet-to-be-determined values from this.
env['PYTHONPATH'] = os.path.dirname(pkg_resources.__file__)

cmd = [sys.executable,
       'setup.py', '-q', 'develop', '-m', '-x', '-d', 'develop-eggs']

if not has_broken_dash_S:
    cmd.insert(1, '-S')

subprocess.Popen(cmd, env=env).wait()

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
