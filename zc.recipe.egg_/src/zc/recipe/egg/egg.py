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

$Id$
"""

import UserDict, logging, os, re, zipfile
import zc.buildout
import zc.buildout.easy_install


class Eggs(object):

    include_site_packages = allowed_eggs = None

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = self.default_eggs = name
        if getattr(options, 'query_bool', None) is None:
            # Someone is not passing us a zc.buildout.buildout.Options
            # object.  Maybe we should have a deprecation warning.
            # Whatever.
            options = _BackwardsSupportOption(options)
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
                               if host.strip()!=''])
        self.allow_hosts = allow_hosts

        options['eggs-directory'] = b_options['eggs-directory']
        options['_e'] = options['eggs-directory'] # backward compat.
        options['develop-eggs-directory'] = b_options['develop-eggs-directory']
        options['_d'] = options['develop-eggs-directory'] # backward compat.

        python = options.setdefault('python', b_options['python'])
        options['executable'] = buildout[python]['executable']

    def working_set(self, extra=()):
        """Separate method to just get the working set

        This is intended for reuse by similar recipes.
        """
        options = self.options
        b_options = self.buildout['buildout']

        distributions = [
            r.strip()
            for r in options.get('eggs', self.default_eggs).split('\n')
            if r.strip()]
        orig_distributions = distributions[:]
        distributions.extend(extra)

        if b_options.get('offline') == 'true':
            ws = zc.buildout.easy_install.working_set(
                distributions, options['executable'],
                [options['develop-eggs-directory'],
                 options['eggs-directory']],
                include_site_packages=self.include_site_packages,
                allowed_eggs_from_site_packages=self.allowed_eggs,
                )
        else:
            kw = {}
            if 'unzip' in options:
                kw['always_unzip'] = options.query_bool('unzip', None)
            ws = zc.buildout.easy_install.install(
                distributions, options['eggs-directory'],
                links=self.links,
                index=self.index,
                executable=options['executable'],
                path=[options['develop-eggs-directory']],
                newest=b_options.get('newest') == 'true',
                include_site_packages=self.include_site_packages,
                allowed_eggs_from_site_packages=self.allowed_eggs,
                allow_hosts=self.allow_hosts,
                **kw)

        return orig_distributions, ws

    def install(self):
        reqs, ws = self.working_set()
        return ()

    update = install


class ScriptBase(Eggs):

    def __init__(self, buildout, name, options):
        super(ScriptBase, self).__init__(buildout, name, options)

        b_options = buildout['buildout']

        options['bin-directory'] = b_options['bin-directory']
        options['_b'] = options['bin-directory'] # backward compat.

        self.extra_paths = [
            os.path.join(b_options['directory'], p.strip())
            for p in options.get('extra-paths', '').split('\n')
            if p.strip()
            ]
        if self.extra_paths:
            options['extra-paths'] = '\n'.join(self.extra_paths)


        relative_paths = options.get(
            'relative-paths', b_options.get('relative-paths', 'false'))
        if relative_paths == 'true':
            options['buildout-directory'] = b_options['directory']
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
        if scripts or scripts is None or options.get('interpreter'):
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

            if options.query_bool('dependent-scripts', 'false'):
                # Generate scripts for all packages in the working set,
                # except setuptools.
                reqs = list(reqs)
                for dist in ws:
                    name = dist.project_name
                    if name != 'setuptools' and name not in reqs:
                        reqs.append(name)
            return self._install(reqs, ws, scripts)
        return ()

    update = install

    def _install(self, reqs, ws, scripts):
        # Subclasses implement this.
        raise NotImplementedError()


class Scripts(ScriptBase):

    def _install(self, reqs, ws, scripts):
        options = self.options
        return zc.buildout.easy_install.scripts(
            reqs, ws, options['executable'],
            options['bin-directory'],
            scripts=scripts,
            extra_paths=self.extra_paths,
            interpreter=options.get('interpreter'),
            initialization=options.get('initialization', ''),
            arguments=options.get('arguments', ''),
            relative_paths=self._relative_paths
            )

Egg = Scripts


class _BackwardsSupportOption(UserDict.UserDict):

    def __init__(self, data):
        self.data = data # We want to show mutations to the underlying dict.

    def query_bool(self, name, default=None):
        """Given a name, return a boolean value for that name.

        ``default``, if given, should be 'true', 'false', or None.
        """
        if default is not None:
            value = self.setdefault(name, default)
        else:
            value = self.get(name)
            if value is None:
                return value
        return _convert_bool(name, value)

    def get_bool(self, name):
        """Given a name, return a boolean value for that name.
        """
        return _convert_bool(name, self[name])


def _convert_bool(name, value):
    if value not in ('true', 'false'):
        raise zc.buildout.UserError(
            'Invalid value for %s option: %s' % (name, value))
    else:
        return value == 'true'
