##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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
"""A few built-in recipes

$Id$
"""

import os, sys
import zc.buildout.egglinker

class TestRunner:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

    def install(self):
        distributions = self.options['distributions'].split()
        path = zc.buildout.egglinker.path(
            distributions+['zope.testing'],
            [self.buildout.eggs],
            )
        
        locations = [zc.buildout.egglinker.location(distribution,
                                                    [self.buildout.eggs])
                     for distribution in distributions]
        script = self.options.get('script', self.name)
        script = self.buildout.buildout_path('bin', script)
        open(script, 'w').write(tests_template % dict(
            PYTHON=sys.executable,
            PATH="',\n  '".join(path),
            TESTPATH="',\n  '--test-path', '".join(locations),
            ))
        try:
            os.chmod(script, 0755)
        except (AttributeError, os.error):
            pass

        return script


tests_template = """#!%(PYTHON)s

import sys
sys.path[0:0] = [
  '%(PATH)s',
  ]

from zope.testing import testrunner

defaults = [
  '--test-path', '%(TESTPATH)s',
  ]

sys.exit(testrunner.run(defaults))
"""
                                 
