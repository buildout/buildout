##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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
"""

import copy
import logging
import os
import re
import sys
import zc.buildout.easy_install


class Eggs(object):

    _WORKING_SET_CACHE_ATTR_NAME = '_zc_recipe_egg_working_set_cache'

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options
        b_options = buildout['buildout']
        links = options.get('find-links', b_options['find-links'])
        if links:
            links = links.split()
            options['find-links'] = '\n'.join(links)
        else:
            links = ()
        self.links = links

        index = options.get('index', b_options.get('index'))
        if index is not None:
            options['index'] = index
        self.index = index

        allow_hosts = b_options['allow-hosts']
        allow_hosts = tuple([host.strip() for host in allow_hosts.split('\n')
                            if host.strip() != ''])
        self.allow_hosts = allow_hosts

        options['eggs-directory'] = b_options['eggs-directory']
        options['_e'] = options['eggs-directory']  # backward compat.
        options['develop-eggs-directory'] = b_options['develop-eggs-directory']
        options['_d'] = options['develop-eggs-directory']  # backward compat.

    def working_set(self, extra=()):
        """Separate method to just get the working set

        This is intended for reuse by similar recipes.
        """
        options = self.options
        buildout_section = self.buildout['buildout']

        # Backward compat. :(
        options['executable'] = sys.executable

        orig_distributions = [
            r.strip()
            for r in options.get('eggs', self.name).split('\n')
            if r.strip()
            ]

        ws = self._working_set(
            distributions=orig_distributions + list(extra),
            develop_eggs_dir=options['develop-eggs-directory'],
            eggs_dir=options['eggs-directory'],
            offline=(buildout_section.get('offline') == 'true'),
            newest=(buildout_section.get('newest') == 'true'),
            links=self.links,
            index=self.index,
            allow_hosts=self.allow_hosts,
            )

        return orig_distributions, ws

    def install(self):
        reqs, ws = self.working_set()
        return ()

    update = install

    def _working_set(
        self,
        distributions,
        eggs_dir,
        develop_eggs_dir,
        offline=False,
        newest=True,
        links=(),
        index=None,
        allow_hosts=('*',),
    ):
        """Helper function to build a working set.

        Return an instance of `pkg_resources.WorkingSet`.

        Results are cached. The cache key is composed by all the arguments
        passed to the function. See also `self._get_cache_storage()`.
        """
        cache_storage = self._get_cache_storage()
        cache_key = (
            tuple(distributions),
            eggs_dir,
            develop_eggs_dir,
            offline,
            newest,
            tuple(links),
            index,
            tuple(allow_hosts),
        )
        if cache_key not in cache_storage:
            if offline:
                ws = zc.buildout.easy_install.working_set(
                    distributions,
                    [develop_eggs_dir, eggs_dir]
                    )
            else:
                ws = zc.buildout.easy_install.install(
                    distributions, eggs_dir,
                    links=links,
                    index=index,
                    path=[develop_eggs_dir],
                    newest=newest,
                    allow_hosts=allow_hosts)
            cache_storage[cache_key] = ws

        # `pkg_resources.WorkingSet` instances are mutable, so we need to return
        # a copy.
        return copy.deepcopy(cache_storage[cache_key])

    def _get_cache_storage(self):
        """Return a mapping where to store generated working sets.

        The cache storage is stored in an attribute of `self.buildout` with
        name given by `self._WORKING_SET_CACHE_ATTR_NAME`.
        """
        cache_storage = getattr(
            self.buildout,
            self._WORKING_SET_CACHE_ATTR_NAME,
            None)
        if cache_storage is None:
            cache_storage = {}
            setattr(
                self.buildout,
                self._WORKING_SET_CACHE_ATTR_NAME,
                cache_storage)
        return cache_storage


class Scripts(Eggs):

    def __init__(self, buildout, name, options):
        super(Scripts, self).__init__(buildout, name, options)

        options['bin-directory'] = buildout['buildout']['bin-directory']
        options['_b'] = options['bin-directory']  # backward compat.

        self.extra_paths = [
            os.path.join(buildout['buildout']['directory'], p.strip())
            for p in options.get('extra-paths', '').split('\n')
            if p.strip()
            ]
        if self.extra_paths:
            options['extra-paths'] = '\n'.join(self.extra_paths)

        relative_paths = options.get(
            'relative-paths',
            buildout['buildout'].get('relative-paths', 'false')
            )
        if relative_paths == 'true':
            options['buildout-directory'] = buildout['buildout']['directory']
            self._relative_paths = options['buildout-directory']
        else:
            self._relative_paths = ''
            assert relative_paths == 'false'

    parse_entry_point = re.compile(
        '([^=]+)=(\w+(?:[.]\w+)*):(\w+(?:[.]\w+)*)$'
        ).match

    def install(self):
        reqs, ws = self.working_set()
        options = self.options

        scripts = options.get('scripts')
        if scripts or scripts is None:
            if scripts is not None:
                scripts = scripts.split()
                scripts = dict([
                    ('=' in s) and s.split('=', 1) or (s, s)
                    for s in scripts
                    ])

            for s in options.get('entry-points', '').split():
                parsed = self.parse_entry_point(s)
                if not parsed:
                    logging.getLogger(self.name).error(
                        "Cannot parse the entry point %s.", s)
                    raise zc.buildout.UserError("Invalid entry point")
                reqs.append(parsed.groups())

            if get_bool(options, 'dependent-scripts'):
                # Generate scripts for all packages in the working set,
                # except setuptools.
                reqs = list(reqs)
                for dist in ws:
                    name = dist.project_name
                    if name != 'setuptools' and name not in reqs:
                        reqs.append(name)

            return zc.buildout.easy_install.scripts(
                reqs, ws, sys.executable, options['bin-directory'],
                scripts=scripts,
                extra_paths=self.extra_paths,
                interpreter=options.get('interpreter'),
                initialization=options.get('initialization', ''),
                arguments=options.get('arguments', ''),
                relative_paths=self._relative_paths,
                )

        return ()

    update = install


def get_bool(options, name, default=False):
    value = options.get(name)
    if not value:
        return default
    if value == 'true':
        return True
    elif value == 'false':
        return False
    else:
        raise zc.buildout.UserError(
            "Invalid value for %s option: %s" % (name, value))

Egg = Scripts
