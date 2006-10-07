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

class Custom:

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

        build_ext = {}
        for be_option in ('include-dirs', 'library-dirs', 'rpath'):
            value = options.get(be_option)
            if value is None:
                continue
            value = [
                os.path.join(
                    buildout['buildout']['directory'],
                    v.strip()
                    )
                for v in value.strip().split('\n')
                if v.strip()
            ]
            build_ext[be_option] = ':'.join(value)
            options[be_option] = ':'.join(value)
        self.build_ext = build_ext

    def install(self):
        if self.buildout['buildout'].get('offline') == 'true':
            return ()
        options = self.options
        distribution = options.get('eggs', self.name).strip()
        build_ext = dict([
            (k, options[k])
            for k in ('include-dirs', 'library-dirs', 'rpath')
            if k in options
            ])
        zc.buildout.easy_install.build(
            distribution, options['_d'], self.build_ext,
            self.links, self.index, options['executable'], [options['_e']],
            )
        
        return ()

    update = install
