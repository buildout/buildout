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

import logging
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

    # XXX need test
    def __setitem__(self, option, value):
        if not isinstance(value, str):
            raise TypeError('Option values must be strings', value)
        super(Options, self).__setitem__(option, value)

    def copy(self):
        return Options(self.buildout, self.section, self)

class Buildout(dict):

    def __init__(self, config_file, cloptions):
        config_file = os.path.abspath(config_file)
        self._config_file = config_file

        super(Buildout, self).__init__()

        # default options
        data = dict(buildout={
            'directory': os.path.dirname(config_file),
            'eggs-directory': 'eggs',
            'bin-directory': 'bin',
            'parts-directory': 'parts',
            'installed': '.installed.cfg',
            'python': 'buildout',
            'executable': sys.executable,
            'log-level': 'WARNING',
            'log-format': '%(name)s: %(message)s',
            })

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
            d = self._buildout_path(options[name+'-directory'])
            options[name+'-directory'] = d

        options['installed'] = os.path.join(options['directory'],
                                            options['installed'])

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

    def _buildout_path(self, *names):
        return os.path.join(self._buildout_dir, *names)

    def install(self, install_parts):

        # Create buildout directories
        for name in ('bin', 'parts', 'eggs'):
            d = self['buildout'][name+'-directory']
            if not os.path.exists(d):
                self._logger.info('Creating directory %s', d)
                os.mkdir(d)

        # Build develop eggs
        self._develop()

        # load installed data
        installed_part_options = self._read_installed_part_options()

        # get configured and installed part lists
        conf_parts = self['buildout']['parts']
        conf_parts = conf_parts and conf_parts.split() or []
        installed_parts = installed_part_options['buildout']['parts']
        installed_parts = installed_parts and installed_parts.split() or []


        # If install_parts is given, then they must be listed in parts
        # and we don't uninstall anything. Otherwise, we install
        # the configured parts and uninstall anything else.
        if install_parts:
            extra = [p for p in install_parts if p not in conf_parts]
            if extra:
                self._error('Invalid install parts:', *extra)
            uninstall_missing = False
        else:
            install_parts = conf_parts
            uninstall_missing = True

        # load recipes
        recipes = self._load_recipes(install_parts)

        # compute new part recipe signatures
        self._compute_part_signatures(install_parts)

        try:
            # uninstall parts that are no-longer used or who's configs
            # have changed
            for part in reversed(installed_parts):
                if part in install_parts:
                    old_options = installed_part_options[part].copy()
                    old_options.pop('__buildout_installed__')
                    if old_options == self.get(part):
                        continue
                elif not uninstall_missing:
                    continue

                # ununstall part
                self._logger.info('Uninstalling %s', part)
                self._uninstall(
                    installed_part_options[part]['__buildout_installed__'])
                installed_parts = [p for p in installed_parts if p != part]

            # install new parts
            for part in install_parts:
                self._logger.info('Installing %s', part)
                installed_part_options[part] = self[part].copy()
                del self[part]['__buildout_signature__']
                installed_files = recipes[part].install() or ()
                if isinstance(installed_files, str):
                    installed_files = [installed_files]
                installed_part_options[part]['__buildout_installed__'] = (
                    '\n'.join(installed_files)
                    )
                if part not in installed_parts:
                    installed_parts.append(part)
        finally:
            installed_part_options['buildout']['parts'] = ' '.join(
                [p for p in conf_parts if p in installed_parts]
                +
                [p for p in installed_parts if p not in conf_parts] 
            )
            self._save_installed_options(installed_part_options)

    def _develop(self):
        """Install sources by running setup.py develop on them
        """
        develop = self['buildout'].get('develop')
        if develop:
            here = os.getcwd()
            try:
                for setup in develop.split():
                    setup = self._buildout_path(setup)
                    if os.path.isdir(setup):
                        setup = os.path.join(setup, 'setup.py')
                    self._logger.info("Running %s -q develop ...", setup)
                    os.chdir(os.path.dirname(setup))
                    os.spawnle(
                        os.P_WAIT, sys.executable, sys.executable,
                        setup, '-q', 'develop', '-m', '-x',
                        '-f', ' '.join(self._links),
                        '-d', self['buildout']['eggs-directory'],
                        {'PYTHONPATH':
                         os.path.dirname(pkg_resources.__file__)},
                        )
            finally:
                os.chdir(os.path.dirname(here))

    def _load_recipes(self, parts):
        recipes = {}
        recipes_requirements = []
        pkg_resources.working_set.add_entry(self['buildout']['eggs-directory'])

        # Install the recipe distros
        for part in parts:
            options = self.get(part)
            if options is None:
                options = self[part] = {}
            recipe, entry = self._recipe(part, options)
            zc.buildout.easy_install.install(
                recipe, self['buildout']['eggs-directory'], self._links)
            recipes_requirements.append(recipe)

        # Add the distros to the working set
        pkg_resources.require(recipes_requirements)

        # instantiate the recipes
        for part in parts:
            options = self[part]
            recipe, entry = self._recipe(part, options)
            recipe_class = pkg_resources.load_entry_point(
                recipe, 'zc.buildout', entry)
            recipes[part] = recipe_class(self, part, options)
        
        return recipes

    def _compute_part_signatures(self, parts):
        # Compute recipe signature and add to options
        base = self['buildout']['eggs-directory'] + os.path.sep
        for part in parts:
            options = self.get(part)
            if options is None:
                options = self[part] = {}
            recipe, entry = self._recipe(part, options)
            req = pkg_resources.Requirement.parse(recipe)
            sig = _dists_sig(pkg_resources.working_set.resolve([req]), base)
            options['__buildout_signature__'] = ' '.join(sig)

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
            return dict([
                (section, Options(self, section, parser.items(section)))
                for section in parser.sections()])
        else:
            return {'buildout': Options(self, 'buildout', {'parts': ''})}

    def _installed_path(self):        
        return self._buildout_path(self['buildout']['installed'])

    def _uninstall(self, installed):
        for f in installed.split():
            f = self._buildout_path(f)
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
        base = self._buildout_path('')
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

    def _error(self, message, *args, **kw):
        self._logger.error(message, *args, **kw)
        sys.exit(1)

    def _setup_logging(self):
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(self['buildout']['log-format']))
        root_logger.addHandler(handler)
        self._logger = logging.getLogger('buildout')
        level = self['buildout']['log-level']
        if level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            level = getattr(logging, level)
        else:
            try:
                level = int(level)
            except ValueError:
                self._error("Invalid logging level %s", level)
        verbosity = self['buildout'].get('verbosity', 0)
        try:
            verbosity = int(verbosity)
        except ValueError:
            self._error("Invalid verbosity %s", verbosity)
        
        root_logger.setLevel(level-verbosity)
        
        
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

    config_file = 'buildout.cfg'
    verbosity = 0
    options = []
    while args:
        if args[0][0] == '-':
            op = orig_op = args.pop(0)
            op = op[1:]
            while op and op[0] in 'vq':
                if op[0] == 'v':
                    verbosity += 10
                else:
                    verbosity -= 10
                op = op[1:]
            if op[:1] == 'c':
                op = op[1:]
                if op:
                    config_file = op
                else:
                    if args:
                        config_file = args.pop(0)
                    else:
                        _error("No file name specified for option", orig_op)
            elif op:
                _error("Invalid option", '-'+op[0])
        elif '=' in args[0]:
            option, value = args.pop(0).split('=', 1)
            if len(option.split(':')) != 2:
                _error('Invalid option:', option)
            section, option = option.split(':')
            options.append((section.strip(), option.strip(), value.strip()))
        else:
            # We've run out of command-line options and option assignnemnts
            # The rest should be commands, so we'll stop here
            break

    if verbosity:
        options.append(('buildout', 'verbosity', str(verbosity)))

    buildout = Buildout(config_file, options)
    buildout._setup_logging()

    if args:
        command = args.pop(0)
        if command != 'install':
            _error('invalid command:', command)
    else:
        command = 'install'

    try:
        getattr(buildout, command)(args)
    finally:
        logging.shutdown()

if sys.version_info[:2] < (2, 4):
    def reversed(iterable):
        result = list(iterable);
        result.reverse()
        return result
