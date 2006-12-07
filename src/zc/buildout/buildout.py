#############################################################################
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
import cStringIO
import sys
import tempfile
import urllib2
import ConfigParser
import UserDict

import pkg_resources
import zc.buildout
import zc.buildout.easy_install

try:
    realpath = os.path.realpath
except AttributeError:
    def realpath(path):
        return path

pkg_resources_loc = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')).location

_isurl = re.compile('([a-zA-Z0-9+.-]+)://').match

class MissingOption(zc.buildout.UserError, KeyError):
    """A required option was missing
    """

class MissingSection(zc.buildout.UserError, KeyError):
    """A required section is missinh
    """

    def __str__(self):
        return "The referenced section, %r, was not defined." % self[0]


class Buildout(UserDict.DictMixin):

    def __init__(self, config_file, cloptions,
                 user_defaults=True, windows_restart=False):

        self.__windows_restart = windows_restart

        # default options
        data = dict(buildout={
            'eggs-directory': 'eggs',
            'develop-eggs-directory': 'develop-eggs',
            'bin-directory': 'bin',
            'parts-directory': 'parts',
            'installed': '.installed.cfg',
            'python': 'buildout',
            'executable': sys.executable,
            'log-level': 'INFO',
            'log-format': '%(name)s: %(message)s',
            })

        if not _isurl(config_file):
            config_file = os.path.abspath(config_file)
            base = os.path.dirname(config_file)
            if not os.path.exists(config_file):
                print 'Warning: creating', config_file
                open(config_file, 'w').write('[buildout]\nparts = \n')
            data['buildout']['directory'] = os.path.dirname(config_file)
        else:
            base = None

        # load user defaults, which override defaults
        if user_defaults and 'HOME' in os.environ:
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
                # The egg dire


        self._raw = data
        self._data = {}
        self._parts = []
        
        # initialize some attrs and buildout directories.
        options = self['buildout']

        links = options.get('find-links', '')
        self._links = links and links.split() or ()

        self._buildout_dir = options['directory']
        for name in ('bin', 'parts', 'eggs', 'develop-eggs'):
            d = self._buildout_path(options[name+'-directory'])
            options[name+'-directory'] = d

        if options['installed']:
            options['installed'] = os.path.join(options['directory'],
                                                options['installed'])

        self._setup_logging()

        offline = options.get('offline', 'false')
        if offline not in ('true', 'false'):
            self._error('Invalid value for offline option: %s', offline)
        options['offline'] = offline


    def _buildout_path(self, *names):
        return os.path.join(self._buildout_dir, *names)

    def bootstrap(self, args):
        self._setup_directories()

        # Now copy buildout and setuptools eggs, amd record destination eggs:
        entries = []
        for name in 'setuptools', 'zc.buildout':
            r = pkg_resources.Requirement.parse(name)
            dist = pkg_resources.working_set.find(r)
            if dist.precedence == pkg_resources.DEVELOP_DIST:
                dest = os.path.join(self['buildout']['develop-eggs-directory'],
                                    name+'.egg-link')
                open(dest, 'w').write(dist.location)
                entries.append(dist.location)
            else:
                dest = os.path.join(self['buildout']['eggs-directory'],
                                    os.path.basename(dist.location))
                entries.append(dest)
                if not os.path.exists(dest):
                    if os.path.isdir(dist.location):
                        shutil.copytree(dist.location, dest)
                    else:
                        shutil.copy2(dist.location, dest)

        # Create buildout script
        ws = pkg_resources.WorkingSet(entries)
        ws.require('zc.buildout')
        zc.buildout.easy_install.scripts(
            ['zc.buildout'], ws, sys.executable,
            self['buildout']['bin-directory'])

    def install(self, install_args):
        self._load_extensions()
        self._setup_directories()

        # Add develop-eggs directory to path so that it gets searched
        # for eggs:
        sys.path.insert(0, self['buildout']['develop-eggs-directory'])

        # Check for updates. This could cause the process to be rstarted
        self._maybe_upgrade()

        # load installed data
        installed_part_options = self._read_installed_part_options()

        # Remove old develop eggs
        self._uninstall(
            installed_part_options['buildout'].get(
                'installed_develop_eggs', '')
            )

        # Build develop eggs
        installed_develop_eggs = self._develop()

        # get configured and installed part lists
        conf_parts = self['buildout']['parts']
        conf_parts = conf_parts and conf_parts.split() or []
        installed_parts = installed_part_options['buildout']['parts']
        installed_parts = installed_parts and installed_parts.split() or []
        
        if install_args:
            install_parts = install_args
            uninstall_missing = False
        else:
            install_parts = conf_parts
            uninstall_missing = True

        # load and initialize recipes
        [self[part]['recipe'] for part in install_parts]
        if not install_args:
            install_parts = self._parts

        if self._log_level <= logging.DEBUG:
            sections = list(self)
            sections.sort()
            print    
            print 'Configuration data:'
            for section in self._data:
                _save_options(section, self[section], sys.stdout)
            print    


        # compute new part recipe signatures
        self._compute_part_signatures(install_parts)

        try:
            # uninstall parts that are no-longer used or who's configs
            # have changed
            for part in reversed(installed_parts):
                if part in install_parts:
                    old_options = installed_part_options[part].copy()
                    installed_files = old_options.pop('__buildout_installed__')
                    new_options = self.get(part)
                    if old_options == new_options:
                        # The options are the same, but are all of the
                        # installed files still there?  If not, we should
                        # reinstall.
                        if not installed_files:
                            continue
                        for f in installed_files.split('\n'):
                            if not os.path.exists(self._buildout_path(f)):
                                break
                        else:
                            continue

                    # output debugging info
                    for k in old_options:
                        if k not in new_options:
                            self._logger.debug("Part: %s, dropped option %s",
                                               part, k)
                        elif old_options[k] != new_options[k]:
                            self._logger.debug(
                                "Part: %s, option %s, %r != %r",
                                part, k, new_options[k], old_options[k],
                                )
                    for k in new_options:
                        if k not in old_options:
                            self._logger.debug("Part: %s, new option %s",
                                               part, k)

                elif not uninstall_missing:
                    continue

                # ununstall part
                self._logger.info('Uninstalling %s', part)

                # run uinstall recipe
                recipe, entry = _recipe(installed_part_options[part])
                try:
                    uninstaller = _install_and_load(
                        recipe, 'zc.buildout.uninstall', entry, self)
                    self._logger.info('Running uninstall recipe')
                    uninstaller(part, installed_part_options[part])
                except (ImportError, pkg_resources.DistributionNotFound), v:
                    pass

                # remove created files and directories
                self._uninstall(
                    installed_part_options[part]['__buildout_installed__'])
                installed_parts = [p for p in installed_parts if p != part]

            # install new parts
            for part in install_parts:
                signature = self[part].pop('__buildout_signature__')
                saved_options = self[part].copy()
                recipe = self[part].recipe
                if part in installed_parts:
                    self._logger.info('Updating %s', part)
                    old_options = installed_part_options[part]
                    old_installed_files = old_options['__buildout_installed__']
                    try:
                        update = recipe.update
                    except AttributeError:
                        update = recipe.install
                        self._logger.warning(
                            "The recipe for %s doesn't define an update "
                            "method. Using its install method",
                            part)

                    try:
                        installed_files = update()
                    except:
                        installed_parts.remove(part)
                        self._uninstall(old_installed_files)
                        raise
                    
                    if installed_files is None:
                        installed_files = old_installed_files.split('\n')

                else:
                    self._logger.info('Installing %s', part)
                    installed_files = recipe.install()
                    if installed_files is None:
                        self._logger.warning(
                            "The %s install returned None.  A path or "
                            "iterable os paths should be returned.",
                            part)
                        installed_files = ()
                    
                if isinstance(installed_files, str):
                    installed_files = [installed_files]

                installed_part_options[part] = saved_options
                saved_options['__buildout_installed__'
                              ] = '\n'.join(installed_files)
                saved_options['__buildout_signature__'] = signature

                installed_parts = [p for p in installed_parts if p != part]
                installed_parts.append(part)

        finally:
            installed_part_options['buildout']['parts'] = (
                ' '.join(installed_parts))
            installed_part_options['buildout']['installed_develop_eggs'
                                               ] = installed_develop_eggs
            
            self._save_installed_options(installed_part_options)

    def _setup_directories(self):

        # Create buildout directories
        for name in ('bin', 'parts', 'eggs', 'develop-eggs'):
            d = self['buildout'][name+'-directory']
            if not os.path.exists(d):
                self._logger.info('Creating directory %s', d)
                os.mkdir(d)

    def _develop(self):
        """Install sources by running setup.py develop on them
        """
        develop = self['buildout'].get('develop')
        if not develop:
            return ''

        dest = self['buildout']['develop-eggs-directory']
        old_files = os.listdir(dest)

        env = dict(os.environ, PYTHONPATH=pkg_resources_loc)
        here = os.getcwd()
        try:
            try:
                for setup in develop.split():
                    setup = self._buildout_path(setup)
                    self._logger.info("Develop: %s", setup)
                    zc.buildout.easy_install.develop(setup, dest)
            except:
                # if we had an error, we need to roll back changes, by
                # removing any files we created.
                self._sanity_check_develop_eggs_files(dest, old_files)
                self._uninstall('\n'.join(
                    [os.path.join(dest, f)
                     for f in os.listdir(dest)
                     if f not in old_files
                     ]))
                raise
                     
            else:
                self._sanity_check_develop_eggs_files(dest, old_files)
                return '\n'.join([os.path.join(dest, f)
                                  for f in os.listdir(dest)
                                  if f not in old_files
                                  ])

        finally:
            os.chdir(here)


    def _sanity_check_develop_eggs_files(self, dest, old_files):
        for f in os.listdir(dest):
            if f in old_files:
                continue
            if not (os.path.isfile(os.path.join(dest, f))
                    and f.endswith('.egg-link')):
                self._logger.warning(
                    "Unexpected entry, %s, in develop-eggs directory", f)

    def _compute_part_signatures(self, parts):
        # Compute recipe signature and add to options
        for part in parts:
            options = self.get(part)
            if options is None:
                options = self[part] = {}
            recipe, entry = _recipe(options)
            req = pkg_resources.Requirement.parse(recipe)
            sig = _dists_sig(pkg_resources.working_set.resolve([req]))
            options['__buildout_signature__'] = ' '.join(sig)

    def _read_installed_part_options(self):
        old = self['buildout']['installed']
        if old and os.path.isfile(old):
            parser = ConfigParser.RawConfigParser()
            parser.optionxform = lambda s: s
            parser.read(old)
            result = {}
            for section in parser.sections():
                options = {}
                for option, value in parser.items(section):
                    if '%(' in value:
                        for k, v in _spacey_defaults:
                            value = value.replace(k, v)
                    options[option] = value
                result[section] = Options(self, section, options)
                        
            return result
        else:
            return {'buildout': Options(self, 'buildout', {'parts': ''})}

    def _uninstall(self, installed):
        for f in installed.split('\n'):
            if not f:
                continue
            f = self._buildout_path(f)
            if os.path.isdir(f):
                shutil.rmtree(f)
            elif os.path.isfile(f):
                os.remove(f)
                
    def _install(self, part):
        options = self[part]
        recipe, entry = _recipe(options)
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
        installed = self['buildout']['installed']
        if not installed:
            return
        f = open(installed, 'w')
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

        level -= verbosity
        root_logger.setLevel(level)
        self._log_level = level

    def _maybe_upgrade(self):
        # See if buildout or setuptools need to be upgraded.
        # If they do, do the upgrade and restart the buildout process.

        if self['buildout'].get('offline') == 'true':
            return # skip upgrade in offline mode:
        
        ws = zc.buildout.easy_install.install(
            [
            (spec + ' ' + self['buildout'].get(spec+'-version', '')).strip()
            for spec in ('zc.buildout', 'setuptools')
            ],
            self['buildout']['eggs-directory'],
            links = self['buildout'].get('find-links', '').split(),
            index = self['buildout'].get('index'),
            path = [self['buildout']['develop-eggs-directory']],
            )

        upgraded = []
        for project in 'zc.buildout', 'setuptools':
            req = pkg_resources.Requirement.parse(project)
            if ws.find(req) != pkg_resources.working_set.find(req):
                upgraded.append(ws.find(req))

        if not upgraded:
            return

        should_run = realpath(
            os.path.join(os.path.abspath(self['buildout']['bin-directory']),
                         'buildout')
            )
        if sys.platform == 'win32':
            should_run += '-script.py'

        if (realpath(os.path.abspath(sys.argv[0])) != should_run):
            self._logger.debug("Running %r", realpath(sys.argv[0]))
            self._logger.debug("Local buildout is %r", should_run)
            self._logger.warn("Not upgrading because not running a local "
                              "buildout command")
            return

        if sys.platform == 'win32' and not self.__windows_restart:
            args = map(zc.buildout.easy_install._safe_arg, sys.argv)
            args.insert(1, '-W')
            if not __debug__:
                args.insert(0, '-O')
            args.insert(0, sys.executable)
            os.execv(sys.executable, args)            
        
        self._logger.info("Upgraded:\n  %s;\nrestarting.",
                          ",\n  ".join([("%s version %s"
                                       % (dist.project_name, dist.version)
                                       )
                                      for dist in upgraded
                                      ]
                                     ),
                          )
                
        # the new dist is different, so we've upgraded.
        # Update the scripts and return True
        zc.buildout.easy_install.scripts(
            ['zc.buildout'], ws, sys.executable,
            self['buildout']['bin-directory'],
            )

        # Restart
        args = map(zc.buildout.easy_install._safe_arg, sys.argv)
        if not __debug__:
            args.insert(0, '-O')
        args.insert(0, sys.executable)
        sys.exit(os.spawnv(os.P_WAIT, sys.executable, args))

    def _load_extensions(self):
        specs = self['buildout'].get('extensions', '').split()
        if specs:
            if self['buildout'].get('offline') == 'true':
                dest = None
            else:
                dest = self['buildout']['eggs-directory']
                if not os.path.exists(dest):
                    self._logger.info('Creating directory %s', dest)
                    os.mkdir(dest)
                    
            zc.buildout.easy_install.install(
                specs, dest,
                path=[self['buildout']['develop-eggs-directory']],
                working_set=pkg_resources.working_set,
                )
            for ep in pkg_resources.iter_entry_points('zc.buildout.extension'):
                ep.load()(self)

    def setup(self, args):
        setup = args.pop(0)
        if os.path.isdir(setup):
            setup = os.path.join(setup, 'setup.py')

        self._logger.info("Running setup script %s", setup)
        setup = os.path.abspath(setup)

        fd, tsetup = tempfile.mkstemp()
        try:
            os.write(fd, zc.buildout.easy_install.runsetup_template % dict(
                setuptools=pkg_resources_loc,
                setupdir=os.path.dirname(setup),
                setup=setup,
                __file__ = setup,
                ))
            os.spawnl(os.P_WAIT, sys.executable, sys.executable, tsetup,
                      *[zc.buildout.easy_install._safe_arg(a)
                        for a in args])
        finally:
            os.close(fd)
            os.remove(tsetup)

    runsetup = setup # backward compat.

    def __getitem__(self, section):
        try:
            return self._data[section]
        except KeyError:
            pass

        try:
            data = self._raw[section]
        except KeyError:
            raise MissingSection(section)

        options = Options(self, section, data)
        self._data[section] = options
        options._initialize()
        return options          

    def __setitem__(self, key, value):
        raise NotImplementedError('__setitem__')

    def __delitem__(self, key):
        raise NotImplementedError('__delitem__')

    def keys(self):
        return self._raw.keys()

    def __iter__(self):
        return iter(self._raw)


def _install_and_load(spec, group, entry, buildout):
    try:

        req = pkg_resources.Requirement.parse(spec)

        buildout_options = buildout['buildout']
        if pkg_resources.working_set.find(req) is None:
            if buildout_options['offline'] == 'true':
                dest = None
                path = [buildout_options['develop-eggs-directory'],
                        buildout_options['eggs-directory'],
                        ]
            else:
                dest = buildout_options['eggs-directory']
                path = [buildout_options['develop-eggs-directory']]

            zc.buildout.easy_install.install(
                [spec], dest,
                links=buildout._links,
                index=buildout_options.get('index'),
                path=path,
                working_set=pkg_resources.working_set,
                )

        return pkg_resources.load_entry_point(
            req.project_name, group, entry)

    except Exception, v:
        buildout._logger.log(
            1,
            "Could't load %s entry point %s\nfrom %s:\n%s.",
            group, entry, spec, v)
        raise

class Options(UserDict.DictMixin):

    def __init__(self, buildout, section, data):
        self.buildout = buildout
        self.name = section
        self._raw = data
        self._data = {}

    def _initialize(self):
        # force substitutions
        for k in self._raw:
            self.get(k)

        recipe = self.get('recipe')
        if not recipe:
            return
        
        reqs, entry = _recipe(self._data)
        buildout = self.buildout
        recipe_class = _install_and_load(reqs, 'zc.buildout', entry, buildout)

        self.recipe = recipe_class(buildout, self.name, self)
        buildout._parts.append(self.name)

    def get(self, option, default=None, seen=None):
        try:
            return self._data[option]
        except KeyError:
            pass

        v = self._raw.get(option)
        if v is None:
            return default

        if '${' in v:
            key = self.name, option
            if seen is None:
                seen = [key]
            elif key in seen:
                raise zc.buildout.UserError(
                    "Circular reference in substitutions.\n"
                    "We're evaluating %s\nand are referencing: %s.\n"
                    % (", ".join([":".join(k) for k in seen]),
                       ":".join(key)
                       )
                    )
            else:
                seen.append(key)
            v = '$$'.join([self._sub(s, seen) for s in v.split('$$')])
            seen.pop()

        self._data[option] = v
        return v

    _template_split = re.compile('([$]{[^}]*})').split
    _simple = re.compile('[-a-zA-Z0-9 ._]+$').match
    _valid = re.compile('[-a-zA-Z0-9 ._]+:[-a-zA-Z0-9 ._]+$').match
    def _sub(self, template, seen):
        value = self._template_split(template)
        subs = []
        for ref in value[1::2]:
            s = tuple(ref[2:-1].split(':'))
            if not self._valid(ref):
                if len(s) < 2:
                    raise zc.buildout.UserError("The substitution, %s,\n"
                                                "doesn't contain a colon."
                                                % ref)
                if len(s) > 2:
                    raise zc.buildout.UserError("The substitution, %s,\n"
                                                "has too many colons."
                                                % ref)
                if not self._simple(s[0]):
                    raise zc.buildout.UserError(
                        "The section name in substitution, %s,\n"
                        "has invalid characters."
                        % ref)
                if not self._simple(s[1]):
                    raise zc.buildout.UserError(
                        "The option name in substitution, %s,\n"
                        "has invalid characters."
                        % ref)
                
            v = self.buildout[s[0]].get(s[1], None, seen)
            if v is None:
                raise MissingOption("Referenced option does not exist:", *s)
            subs.append(v)
        subs.append('')

        return ''.join([''.join(v) for v in zip(value[::2], subs)])
        
    def __getitem__(self, key):
        try:
            return self._data[key]
        except KeyError:
            pass

        v = self.get(key)
        if v is None:
            raise MissingOption("Missing option: %s:%s"
                                % (self.name, key))
        return v

    def __setitem__(self, option, value):
        if not isinstance(value, str):
            raise TypeError('Option values must be strings', value)
        self._data[option] = value

    def __delitem__(self, key):
        if key in self._raw:
            del self._raw[key]
            if key in self._data:
                del self._data[key]
        elif key in self._data:
            del self._data[key]
        else:
            raise KeyError, key

    def keys(self):
        raw = self._raw
        return list(self._raw) + [k for k in self._data if k not in raw]

    def copy(self):
        return dict([(k, self[k]) for k in self.keys()])

_spacey_nl = re.compile('[ \t\r\f\v]*\n[ \t\r\f\v\n]*'
                        '|'
                        '^[ \t\r\f\v]+'
                        '|'
                        '[ \t\r\f\v]+$'
                        )

_spacey_defaults = [
    ('%(__buildout_space__)s',   ' '),
    ('%(__buildout_space_n__)s', '\n'),
    ('%(__buildout_space_r__)s', '\r'),
    ('%(__buildout_space_f__)s', '\f'),
    ('%(__buildout_space_v__)s', '\v'),
    ]

def _quote_spacey_nl(match):
    match = match.group(0).split('\n', 1)
    result = '\n\t'.join(
        [(s
          .replace(' ', '%(__buildout_space__)s')
          .replace('\r', '%(__buildout_space_r__)s')
          .replace('\f', '%(__buildout_space_f__)s')
          .replace('\v', '%(__buildout_space_v__)s')
          .replace('\n', '%(__buildout_space_n__)s')
          )
         for s in match]
        )
    return result

def _save_options(section, options, f):
    print >>f, '[%s]' % section
    items = options.items()
    items.sort()
    for option, value in items:
        value = _spacey_nl.sub(_quote_spacey_nl, value)
        if value.startswith('\n\t'):
            value = '%(__buildout_space_n__)s' + value[2:]
        if value.endswith('\n\t'):
            value = value[:-2] + '%(__buildout_space_n__)s'
        print >>f, option, '=', value

def _open(base, filename, seen):
    """Open a configuration file and return the result as a dictionary,

    Recursively open other files based on buildout options found.
    """

    if _isurl(filename):
        fp = urllib2.urlopen(filename)
        base = filename[:filename.rfind('/')]
    elif _isurl(base):
        if os.path.isabs(filename):
            fp = open(filename)
            base = os.path.dirname(filename)
        else:
            filename = base + '/' + filename
            fp = urllib2.urlopen(filename)
            base = filename[:filename.rfind('/')]
    else:
        filename = os.path.join(base, filename)
        fp = open(filename)
        base = os.path.dirname(filename)

    if filename in seen:
        raise zc.buildout.UserError("Recursive file include", seen, filename)

    seen.append(filename)

    result = {}

    parser = ConfigParser.RawConfigParser()
    parser.optionxform = lambda s: s
    parser.readfp(fp)
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
        self._logger.warn(
            "The extendedBy option is deprecated.  Stop using it."
            )
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
    
def _dists_sig(dists):
    result = []
    for dist in dists:
        location = dist.location
        if dist.precedence == pkg_resources.DEVELOP_DIST:
            result.append(dist.project_name + '-' + _dir_hash(location))
        else:
            result.append(os.path.basename(location))
    return result

def _update(d1, d2):
    for section in d2:
        if section in d1:
            d1[section].update(d2[section])
        else:
            d1[section] = d2[section]
    return d1

def _recipe(options):
    recipe = options['recipe']
    if ':' in recipe:
        recipe, entry = recipe.split(':')
    else:
        entry = 'default'

    return recipe, entry

def _error(*message):
    sys.stderr.write('Error: ' + ' '.join(message) +'\n')
    sys.exit(1)

_usage = """\
Usage: buildout [options] [assignments] [command [command arguments]]

Options:

  -h, --help

     Print this message and exit.

  -v

     Increase the level of verbosity.  This option can be used multiple times.

  -q

     Decrease the level of verbosity.  This option can be used multiple times.

  -c config_file

     Specify the path to the buildout configuration file to be used.
     This defaults to the file named "buildout.cfg" in the current
     working directory.

  -U

     Don't read user defaults.

Assignments are of the form: section:option=value and are used to
provide configuration options that override those given in the
configuration file.  For example, to run the buildout in offline mode,
use buildout:offline=true.

Options and assignments can be interspersed.

Commands:

  install [parts]

    Install parts.  If no command arguments are given, then the parts
    definition from the configuration file is used.  Otherwise, the
    arguments specify the parts to be installed.

  bootstrap

    Create a new buildout in the current working directory, copying
    the buildout and setuptools eggs and, creating a basic directory
    structure and a buildout-local buildout script.

"""
def _help():
    print _usage
    sys.exit(0)

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    config_file = 'buildout.cfg'
    verbosity = 0
    options = []
    windows_restart = False
    user_defaults = True
    while args:
        if args[0][0] == '-':
            op = orig_op = args.pop(0)
            op = op[1:]
            while op and op[0] in 'vqhWU':
                if op[0] == 'v':
                    verbosity += 10
                elif op[0] == 'q':
                    verbosity -= 10
                elif op[0] == 'W':
                    windows_restart = True
                elif op[0] == 'U':
                    user_defaults = False
                else:
                    _help()
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
                if orig_op == '--help':
                    _help()
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

    if args:
        command = args.pop(0)
        if command not in ('install', 'bootstrap', 'runsetup', 'setup'):
            _error('invalid command:', command)
    else:
        command = 'install'

    try:
        try:
            buildout = Buildout(config_file, options,
                                user_defaults, windows_restart)
            getattr(buildout, command)(args)
        except zc.buildout.UserError, v:
            _error(str(v))
            
    finally:
            logging.shutdown()

if sys.version_info[:2] < (2, 4):
    def reversed(iterable):
        result = list(iterable);
        result.reverse()
        return result
