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
import sys

if sys.version_info < (2, 7):
    raise SystemError("Outside Python 2.7, no support for Python 2.x.")

if sys.version_info > (3, ) and sys.version_info < (3, 5):
    raise SystemError("No support for Python 3.x under 3.5.")


import os, shutil, sys, subprocess, tempfile

for d in 'eggs', 'develop-eggs', 'bin', 'parts':
    if not os.path.exists(d):
        os.mkdir(d)

bin_buildout = os.path.join('bin', 'buildout')
if os.path.isfile(bin_buildout):
    os.remove(bin_buildout)

if os.path.isdir('build'):
    shutil.rmtree('build')

######################################################################
# Make sure we have a relatively clean environment

if '--no-clean' not in sys.argv:
    try:
        import pip
        print('Remove pip, setuptools, wheel')
        print('')
        if subprocess.call(
            [sys.executable] + ['-m', 'pip', 'uninstall', '-y', 'setuptools', 'pip',  'wheel']
        ):
            raise SystemError(
                "Buildout development with pre-installed pip and setuptools\n"
                "Could not uninstall with pip"
                )
        return_code = subprocess.call(
            [sys.executable] + sys.argv + ['--no-clean']
        )
        sys.exit(return_code)
    except ImportError:
        pass

    try:
        import pkg_resources, setuptools, pip
    except ImportError:
        pass
    else:
        raise SystemError(
            "Buildout development should not come with pre-installed setuptools or pip"
            )

#######################################################################
def install_pip():
    print('')
    print('Install pip')
    print('')
    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    tmp = tempfile.mkdtemp(prefix='buildout-dev-')
    try:
        get_pip = os.path.join(tmp, 'get-pip.py')
        with open(get_pip, 'wb') as f:
           f.write(urlopen('https://bootstrap.pypa.io/get-pip.py').read())

        if subprocess.call([sys.executable, get_pip]):
            raise RuntimeError("pip failed.")
    finally:
        shutil.rmtree(tmp)
    return_code = subprocess.call(
        [sys.executable] + sys.argv + ['--no-clean']
    )
    sys.exit(return_code)

try:
    import pip
except ImportError:
    install_pip()

######################################################################
print('')
print('Install buildout')
print('')
if subprocess.call(
    [sys.executable] +
    ['setup.py', '-q', 'develop', '-m', '-x', '-d', 'develop-eggs'],
    ):
    raise RuntimeError("buildout build failed.")

import pkg_resources

pkg_resources.working_set.add_entry('src')

import zc.buildout.easy_install
zc.buildout.easy_install.scripts(
    ['zc.buildout'], pkg_resources.working_set , sys.executable, 'bin')

######################################################################
def install_coverage():
    print('')
    print('Install coverage')
    print('')
    bin_pip = os.path.join('bin', 'pip')
    if subprocess.call(
        [sys.executable] +
        ['-m', 'pip', 'install', 'coverage'],
        ):
        raise RuntimeError("coverage install failed.")

try:
    import coverage
except ImportError:
    install_coverage()

######################################################################
print('')
print('Run buildout')
print('')
bin_buildout = os.path.join('bin', 'buildout')

if sys.platform.startswith('java'):
    # Jython needs the script to be called twice via sys.executable
    assert subprocess.Popen([sys.executable, bin_buildout, '-N']).wait() == 0

sys.exit(subprocess.Popen(bin_buildout).wait())
