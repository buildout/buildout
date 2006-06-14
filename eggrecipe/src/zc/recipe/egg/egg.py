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

import os
import zc.buildout.egglinker
import zc.buildout.easy_install

class Egg:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options
        links = options.get('find-links',
                            buildout['buildout'].get('find-links'))
        if links:
            buildout_directory = buildout['buildout']['directory']
            links = [os.path.join(buildout_directory, link)
                     for link in links.split()]
            options['find-links'] = '\n'.join(links)
        else:
            links = ()
        self.links = links

        options['_b'] = buildout['buildout']['bin-directory']
        options['_e'] = buildout['buildout']['eggs-directory']

    def install(self):
        options = self.options
        distribution = options.get('distribution', self.name)
        zc.buildout.easy_install.install(
            distribution, options['_e'], self.links)

        scripts = options.get('scripts')
        if scripts or scripts is None:
            if scripts is not None:
                scripts = scripts.split()
                scripts = dict([
                    ('=' in s) and s.split('=', 1) or (s, s)
                    for s in scripts
                    ])
            return zc.buildout.egglinker.scripts(
                [distribution],
                options['_b'], [options['_e']], scripts=scripts)
            
