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

import zc.buildout.egglinker
import zc.buildout.easy_install

class Egg:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

    def install(self):
        distribution = self.options.get('distribution', self.name)
        links = self.options.get(
            'find_links',
            self.buildout['buildout'].get('find_links'),
            )
        if links:
            links = links.split()
        else:
            links = ()

        buildout = self.buildout
        zc.buildout.easy_install.install(
            distribution,
            buildout.eggs,
            [buildout.buildout_path(link) for link in links],
            always_copy = True,
            )

        scripts = self.options.get('scripts')
        if scripts or scripts is None:
            if scripts is not None:
                scripts = scripts.split()
                scripts = dict([
                    ('=' in s) and s.split('=', 1) or (s, s)
                    for s in scripts
                    ])
            return zc.buildout.egglinker.scripts(
                [distribution], buildout.bin, [buildout.eggs],
                scripts=scripts)
            
