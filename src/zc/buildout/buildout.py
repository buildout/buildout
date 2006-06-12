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
"""Buildout main script

$Id$
"""

import md5
import os
import pprint
import re
import shutil
import sys
import ConfigParser

import zc.buildout.easy_install
import pkg_resources
import zc.buildout.easy_install
import zc.buildout.egglinker

class MissingOption(KeyError):
    """A required option was missing
    """

class Options(dict):

    def __init__(self, buildout, section, data):
        self.buildout = buildout
        self.section = section
        super(Options, self).__init__(data)

    def __getitem__(self, option):
        try:
            return super(Options, self).__getitem__(option)
        except KeyError:
            raise MissingOption("Missing option", self.section, option)

    def copy(self):
        return Options(self.buildout, self.section, self)

class Buildout(dict):

    def __init__(self, config_file, cloptions):
        config_file = os.path.abspath(config_file)
        self._config_file = config_file

        super(Buildout, self).__init__()

        # default options
        data = dict(buildout={'directory': os.path.dirname(config_file),
                              'eggs-directory': 'eggs',
                              'bin-directory': 'bin',
                              'parts-directory': 'parts',
                              'installed': '.installed.cfg',
                              },
                       )

        # load user defaults, which override defaults
        if 'HOME' in os.environ:
            user_config = os.path.join(os.environ['HOME'],
                                       '.buildout', 'default.cfg')
            if os.path.exists(user_config):
                _update(data, _open(os.path.dirname(user_config), user_config,
                                    []))

        # load configuration files
        _update(data, _open(os.path.dirname(config_file), config_file, []))

        # apply command-line options
        for (section, option, value) in cloptions:
            options = data.get(section)
            if options is None:
                options = self[section] = {}
            options[option] = value

        # do substitutions
        converted = {}
        for section, options in data.iteritems():
            for option, value in options.iteritems():
                if '$' in value:
                    value = self._dosubs(section, option, value,
                                         data, converted, [])
                    options[option] = value
                converted[(section, option)] = value

        # copy data into self:
        for section, options in data.iteritems():
            self[section] = Options(self, section, options)
        
        # initialize some attrs and buildout directories.
        options = self['buildout']

        links = options.get('find-links', '')
        self._links = links and links.split() or ()

        self._buildout_dir = options['directory']
        for name in ('bin', 'parts', 'eggs'):
            d = self.buildout_path(options[name+'-directory'])
            setattr(self, name, d)
            if not os.path.exists(d):
                os.mkdir(d)

    def _dosubs(self, section, option, value, data, converted, seen):
        key = section, option
        r = converted.get(key)
        if r is not None:
            return r
        if key in seen:
            raise ValueError('Circular references', seen, key)
        seen.append(key)
        value = '$$'.join([self._dosubs_esc(s, data, converted, seen)
                           for s in value.split('$$')
                           ])
        seen.pop()
        return value

    _template_split = re.compile('([$]{\w+:\w+})').split
    def _dosubs_esc(self, value, data, converted, seen):
        value = self._template_split(value)
        subs = []
        for s in value[1::2]:
            s = tuple(s[2:-1].split(':'))
            v = converted.get(s)
            if v is None:
                options = data.get(s[0])
                if options is None:
                    raise KeyError("Referenced section does not exist", s[0])
                v = options.get(s[1])
                if v is None:
                    raise KeyError("Referenced option does not exist", *s)
                if '$' in v:
                    v = self._dosubs(s[0], s[1], v, data, converted, seen)
                    options[s[1]] = v
                converted[s] = v
            subs.append(v)
        subs.append('')

        return ''.join([''.join(v) for v in zip(value[::2], subs)])

    def buildout_path(self, *names):
        return os.path.join(self._buildout_dir, *names)

    def install(self, install_parts):
        self._develop()
        new_part_options = self._gather_part_info()
        installed_part_options = self._read_installed_part_options()
        old_parts = installed_part_options['buildout']['parts'].split()
        old_parts.reverse()

        new_old_parts = []
        for part in old_parts:
            if install_parts and (part not in install_parts):
                # We were asked to install specific parts and this
                # wasn't one of them.  Leave it alone.
                new_old_parts.append(part)
                continue
                
            installed_options = installed_part_options[part].copy()
            installed = installed_options.pop('__buildout_installed__')
            if installed_options != new_part_options.get(part):
                self._uninstall(installed)
                del installed_part_options[part]
            else:
                new_old_parts.append(part)
        new_old_parts.reverse()

        new_parts = []
        try:
            for part in new_part_options['buildout']['parts'].split():
                if (not install_parts) or (part in install_parts):
                    installed = self._install(part)
                    new_part_options[part]['__buildout_installed__'] = installed
                    installed_part_options[part] = new_part_options[part]
                new_parts.append(part)
                new_old_parts = [p for p in new_old_parts if p != part]
        finally:
            new_parts.extend(new_old_parts)
            installed_part_options['buildout']['parts'] = ' '.join(new_parts)
            self._save_installed_options(installed_part_options)

    def _develop(self):
        """Install sources by running setup.py develop on them
        """
        develop = self['buildout'].get('develop')
        if develop:
            here = os.getcwd()
            try:
                for setup in develop.split():
                    setup = self.buildout_path(setup)
                    if os.path.isdir(setup):
                        setup = os.path.join(setup, 'setup.py')

                    os.chdir(os.path.dirname(setup))
                    os.spawnle(
                        os.P_WAIT, sys.executable, sys.executable,
                        setup, '-q', 'develop', '-m', '-x',
                        '-f', ' '.join(self._links),
                        '-d', self.eggs,
                        {'PYTHONPATH':
                         os.path.dirname(pkg_resources.__file__)},
                        )
            finally:
                os.chdir(os.path.dirname(here))

    def _gather_part_info(self):
        """Get current part info, including part options and recipe info
        """
        parts = self['buildout']['parts']
        part_info = {'buildout': {'parts': parts}}
        recipes_requirements = []
        pkg_resources.working_set.add_entry(self.eggs)

        parts = parts and parts.split() or []
        for part in parts:
            options = self.get(part)
            if options is None:
                options = self[part] = {}
            options = options.copy()
            recipe, entry = self._recipe(part, options)
            zc.buildout.easy_install.install(
                recipe, self.eggs, self._links)
            recipes_requirements.append(recipe)
            part_info[part] = options

        # Load up the recipe distros
        pkg_resources.require(recipes_requirements)

        base = self.eggs + os.path.sep
        for part in parts:
            options = part_info[part]
            recipe, entry = self._recipe(part, options)
            req = pkg_resources.Requirement.parse(recipe)
            sig = _dists_sig(pkg_resources.working_set.resolve([req]), base)
            options['__buildout_signature__'] = ' '.join(sig)

        return part_info

    def _recipe(self, part, options):
        recipe = options.get('recipe', part)
        if ':' in recipe:
            recipe, entry = recipe.split(':')
        else:
            entry = 'default'

        return recipe, entry

    def _read_installed_part_options(self):
        old = self._installed_path()
        if os.path.isfile(old):
            parser = ConfigParser.SafeConfigParser()
            parser.read(old)
            return dict([(section, dict(parser.items(section)))
                         for section in parser.sections()])
        else:
            return {'buildout': {'parts': ''}}

    def _installed_path(self):        
        return self.buildout_path(self['buildout']['installed'])

    def _uninstall(self, installed):
        for f in installed.split():
            f = self.buildout_path(f)
            if os.path.isdir(f):
                shutil.rmtree(f)
            elif os.path.isfile(f):
                os.remove(f)
                
    def _install(self, part):
        options = self[part]
        recipe, entry = self._recipe(part, options)
        recipe_class = pkg_resources.load_entry_point(
            recipe, 'zc.buildout', entry)
        installed = recipe_class(self, part, options).install()
        if installed is None:
            installed = []
        elif isinstance(installed, basestring):
            installed = [installed]
        base = self.buildout_path('')
        installed = [d.startswith(base) and d[len(base):] or d
                     for d in installed]
        return ' '.join(installed)


    def _save_installed_options(self, installed_options):
        f = open(self._installed_path(), 'w')
        _save_options('buildout', installed_options['buildout'], f)
        for part in installed_options['buildout']['parts'].split():
            print >>f
            _save_options(part, installed_options[part], f)
        f.close()
        
def _save_options(section, options, f):
    print >>f, '[%s]' % section
    items = options.items()
    items.sort()
    for option, value in items:
        print >>f, option, '=', str(value).replace('\n', '\n\t')
    

def _open(base, filename, seen):
    """Open a configuration file and return the result as a dictionary,

    Recursively open other files based on buildout options found.
    """

    filename = os.path.join(base, filename)
    if filename in seen:
        raise ValueError("Recursive file include", seen, filename)

    base = os.path.dirname(filename)
    seen.append(filename)

    result = {}

    parser = ConfigParser.SafeConfigParser()
    parser.readfp(open(filename))
    extends = extended_by = None
    for section in parser.sections():
        options = dict(parser.items(section))
        if section == 'buildout':
            extends = options.pop('extends', extends)
            extended_by = options.pop('extended-by', extended_by)
        result[section] = options

    if extends:
        extends = extends.split()
        extends.reverse()
        for fname in extends:
            result = _update(_open(base, fname, seen), result)

    if extended_by:
        for fname in extended_by.split():
            result = _update(result, _open(base, fname, seen))

    seen.pop()
    return result
    

def _dir_hash(dir):
    hash = md5.new()
    for (dirpath, dirnames, filenames) in os.walk(dir):
        filenames[:] = [f for f in filenames
                        if not (f.endswith('pyc') or f.endswith('pyo'))
                        ]
        hash.update(' '.join(dirnames))
        hash.update(' '.join(filenames))
        for name in filenames:
            hash.update(open(os.path.join(dirpath, name)).read())
    return hash.digest().encode('base64').strip()
    
def _dists_sig(dists, base):
    result = []
    for dist in dists:
        location = dist.location
        if dist.precedence == pkg_resources.DEVELOP_DIST:
            result.append(dist.project_name + '-' + _dir_hash(location))
        else:
            if location.startswith(base):
                location = location[len(base):]
            result.append(location)
    return result

def _update(d1, d2):
    for section in d2:
        if section in d1:
            d1[section].update(d2[section])
        else:
            d1[section] = d2[section]
    return d1

def _error(*message):
    sys.syderr.write(' '.join(message) +'\n')
    sys.exit(1)

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    if args and args[0] == '-c':
        args.pop(0)
        if not args:
            _error("No configuration file specified,")
        config_file = args.pop(0)
    else:
        config_file = 'buildout.cfg'

    options = []
    while args and '=' in args[0]:
        option, value = args.pop(0).split('=', 1)
        if len(option.split(':')) != 2:
            _error('Invalid option:', option)
        section, option = option.split(':')
        options.append((section.strip(), option.strip(), value.strip()))

    buildout = Buildout(config_file, options)

    if args:
        command = args.pop(0)
        if command != 'install':
            _error('invalid command:', command)
    else:
        command = 'install'

    getattr(buildout, command)(args)
