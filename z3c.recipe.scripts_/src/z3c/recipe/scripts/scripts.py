##############################################################################
#
# Copyright (c) 2009-2010 Zope Foundation and Contributors.
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
"""Install scripts from eggs.
"""
import os
import zc.buildout
import zc.buildout.easy_install
from zc.recipe.egg.egg import ScriptBase


class Base(ScriptBase):

    def __init__(self, buildout, name, options):
        if 'extends' in options:
            for key, value in buildout[options['extends']].items():
                options.setdefault(key, value)
        super(Base, self).__init__(buildout, name, options)
        self.default_eggs = '' # Disables feature from zc.recipe.egg.
        b_options = buildout['buildout']
        options['parts-directory'] = os.path.join(
            b_options['parts-directory'], self.name)

        value = options.setdefault(
            'allowed-eggs-from-site-packages',
            b_options.get('allowed-eggs-from-site-packages', '*'))
        self.allowed_eggs = tuple(name.strip() for name in value.split('\n'))

        self.include_site_packages = options.query_bool(
            'include-site-packages',
            default=b_options.get('include-site-packages', 'false'))

        self.exec_sitecustomize = options.query_bool(
            'exec-sitecustomize',
            default=b_options.get('exec-sitecustomize', 'false'))


class Interpreter(Base):

    def __init__(self, buildout, name, options):
        super(Interpreter, self).__init__(buildout, name, options)

        options.setdefault('name', name)

    def install(self):
        reqs, ws = self.working_set()
        options = self.options
        generated = []
        if not os.path.exists(options['parts-directory']):
            os.mkdir(options['parts-directory'])
            generated.append(options['parts-directory'])
        generated.extend(zc.buildout.easy_install.sitepackage_safe_scripts(
            options['bin-directory'], ws, options['executable'],
            options['parts-directory'],
            interpreter=options['name'],
            extra_paths=self.extra_paths,
            initialization=options.get('initialization', ''),
            include_site_packages=self.include_site_packages,
            exec_sitecustomize=self.exec_sitecustomize,
            relative_paths=self._relative_paths,
            ))
        return generated

    update = install


class Scripts(Base):

    def _install(self, reqs, ws, scripts):
        options = self.options
        generated = []
        if not os.path.exists(options['parts-directory']):
            os.mkdir(options['parts-directory'])
            generated.append(options['parts-directory'])
        generated.extend(zc.buildout.easy_install.sitepackage_safe_scripts(
            options['bin-directory'], ws, options['executable'],
            options['parts-directory'], reqs=reqs, scripts=scripts,
            interpreter=options.get('interpreter'),
            extra_paths=self.extra_paths,
            initialization=options.get('initialization', ''),
            include_site_packages=self.include_site_packages,
            exec_sitecustomize=self.exec_sitecustomize,
            relative_paths=self._relative_paths,
            script_arguments=options.get('arguments', ''),
            script_initialization=options.get('script-initialization', '')
            ))
        return generated
