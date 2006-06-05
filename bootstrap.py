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
"""Bootstrap a buildout

$Id$
"""

import os, sys, urllib2

for d in 'eggs', 'bin':
    if not os.path.exists(d):
        os.mkdir(d)

ez = {}
exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                     ).read() in ez

ez['use_setuptools'](to_dir='eggs', download_delay=0)

import setuptools.command.easy_install
import pkg_resources
import setuptools.package_index
import distutils.dist

os.spawnle(os.P_WAIT, sys.executable, sys.executable, 'setup.py',
           '-q', 'develop', '-m', '-x', '-d', 'eggs',
           {'PYTHONPATH': os.path.dirname(pkg_resources.__file__)},
           )

## easy = setuptools.command.easy_install.easy_install(
##     distutils.dist.Distribution(),
##     multi_version=True,
##     exclude_scripts=True,
##     sitepy_installed=True,
##     install_dir='eggs',
##     outputs=[],
##     quiet=True,
##     zip_ok=True,
##     args=['zc.buildout'],
##     )
## easy.finalize_options()
## easy.easy_install('zc.buildout')

env = pkg_resources.Environment(['eggs'])

ws = pkg_resources.WorkingSet()
sys.path[0:0] = [
    d.location
    for d in ws.resolve([pkg_resources.Requirement.parse('zc.buildout')], env)
    ]

import zc.buildout.egglinker
zc.buildout.egglinker.scripts(['zc.buildout'], 'bin', ['eggs'])

sys.exit(os.spawnl(os.P_WAIT, 'bin/buildout', 'bin/buildout'))
