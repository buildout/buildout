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
# handle -S

def normpath(p):
    if p.endswith(os.path.sep):
        return p[:-1]
    else:
        return p

nosite = 'site' not in sys.modules
if nosite:
    # They've asked not to import site.  Cool, but distribute is going to
    # import it anyway, so we're going to have to clean up. :(
    initial_paths = set(map(normpath, sys.path))
    import site
    to_remove = set(map(normpath, sys.path)) - initial_paths
else:
    to_remove = ()

######################################################################
# Make sure we have a relatively clean environment
try:
    import pkg_resources, setuptools
except ImportError:
    pass
else:
    message = (
        "Buildout development with a pre-installed setuptools or "
        "distribute is not supported."
        )
    if not nosite:
        message += '  Try running with -S option to Python.'
    raise SystemError(message)

######################################################################
# Install distribute
ez = {}

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

exec(urlopen('http://python-distribute.org/distribute_setup.py').read(), ez)
ez['use_setuptools'](to_dir='eggs', download_delay=0)

import pkg_resources

# Clean up
if nosite and 'site' in sys.modules:
    del sys.modules['site']
    sys.path[:] = [p for p in sys.path[:]
        if normpath(p) not in to_remove
        ]

######################################################################
# Install buildout

if subprocess.call(
    [sys.executable] +
    ['setup.py', '-q', 'develop', '-m', '-x', '-d', 'develop-eggs'],
    env = {'PYTHONPATH': os.path.dirname(pkg_resources.__file__)}):
    raise RuntimeError("buildout build failed.")

pkg_resources.working_set.add_entry('src')

import zc.buildout.easy_install
zc.buildout.easy_install.scripts(
    ['zc.buildout'], pkg_resources.working_set , sys.executable, 'bin')

bin_buildout = os.path.join('bin', 'buildout')

if sys.platform.startswith('java'):
    # Jython needs the script to be called twice via sys.executable
    assert subprocess.Popen([sys.executable] + [bin_buildout]).wait() == 0

sys.exit(subprocess.Popen(bin_buildout).wait())
