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
"""Install packages as eggs

$Id$
"""

import os, re, zipfile
import zc.buildout.easy_install

class Egg:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options
        links = options.get('find-links',
                            buildout['buildout'].get('find-links'))
        if links:
            links = links.split()
            options['find-links'] = '\n'.join(links)
        else:
            links = ()
        self.links = links

        index = options.get('index', buildout['buildout'].get('index'))
        if index is not None:
            options['index'] = index
        self.index = index

        options['_b'] = buildout['buildout']['bin-directory']
        options['_e'] = buildout['buildout']['eggs-directory']
        options['_d'] = buildout['buildout']['develop-eggs-directory']

        assert options.get('unzip') in ('true', 'false', None)

        python = options.get('python', buildout['buildout']['python'])
        options['executable'] = buildout[python]['executable']

    def working_set(self):
        """Separate method to just get the working set

        This is intended for reuse by similar recipes.
        """
        options = self.options

        distributions = [
            r.strip()
            for r in options.get('eggs', self.name).split('\n')
            if r.strip()]
        
        ws = zc.buildout.easy_install.install(
            distributions, options['_e'],
            links = self.links,
            index = self.index, 
            executable = options['executable'],
            always_unzip=options.get('unzip') == 'true',
            path=[options['_d']]
            )

        return distributions, ws

    def install(self):
        distributions, ws = self.working_set()
        options = self.options

        scripts = options.get('scripts')
        if scripts or scripts is None:
            if scripts is not None:
                scripts = scripts.split()
                scripts = dict([
                    ('=' in s) and s.split('=', 1) or (s, s)
                    for s in scripts
                    ])
            return zc.buildout.easy_install.scripts(
                distributions, ws, options['executable'],
                options['_b'], scripts=scripts)

