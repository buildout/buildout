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
import pkg_resources
import zc.buildout.easy_install
import zc.recipe.egg

class TestRunner:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options
        options['script'] = os.path.join(buildout['buildout']['bin-directory'],
                                         options.get('script', self.name),
                                         )
        self.egg = zc.recipe.egg.Egg(buildout, name, options)

    def install(self):
        options = self.options
        requirements, ws = self.egg.working_set(('zope.testing', ))

        path = [dist.location for dist in ws]
        project_names = [
            pkg_resources.Requirement.parse(r).project_name
            for r in requirements
            ]
        
        locations = [dist.location for dist in ws
                     if dist.project_name in project_names]

        result = []
        script = options['script']
        if sys.platform == 'win32':
            # generate exe file and give the script a magic name:
            open(script+'.exe', 'wb').write(
                pkg_resources.resource_string('setuptools', 'cli.exe')
                )
            result.append(script+'.exe')
            script += '-script.py'

        open(script, 'w').write(tests_template % dict(
            PYTHON=options['executable'],
            PATH=repr(path)[1:-1].replace(', ', ',\n  '),
            TESTPATH=repr(locations)[1:-1].replace(
                ', ', ",\n  '--test-path', "),
            ))
        try:
            os.chmod(script, 0755)
        except (AttributeError, os.error):
            pass

        result.append(script)

        return result


tests_template = """#!%(PYTHON)s

import sys
sys.path[0:0] = [
  %(PATH)s,
  ]

from zope.testing import testrunner

defaults = [
  '--test-path', %(TESTPATH)s,
  ]

sys.exit(testrunner.run(defaults))
"""
                                 
