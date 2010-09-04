##############################################################################
#
# Copyright (c) 2005-2009 Zope Corporation and Contributors.
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
"""

from rmtree import rmtree
try:
    from hashlib import md5
except ImportError:
    # Python 2.4 and older
    from md5 import md5

import ConfigParser
import copy
import distutils.errors
import glob
import itertools
import logging
import os
import pkg_resources
import re
import shutil
import sys
import tempfile
import UserDict
import warnings
import zc.buildout
import zc.buildout.download
import zc.buildout.easy_install


realpath = zc.buildout.easy_install.realpath

pkg_resources_loc = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')).location

_isurl = re.compile('([a-zA-Z0-9+.-]+)://').match

is_jython = sys.platform.startswith('java')

if is_jython:
    import subprocess

_sys_executable_has_broken_dash_S = (
    zc.buildout.easy_install._has_broken_dash_S(sys.executable))

class MissingOption(zc.buildout.UserError, KeyError):
    """A required option was missing.
    """

class MissingSection(zc.buildout.UserError, KeyError):
    """A required section is missing.
    """

    def __str__(self):
        return "The referenced section, %r, was not defined." % self[0]


def _annotate_section(section, note):
    for key in section:
        section[key] = (section[key], note)
    return section

def _annotate(data, note):
    for key in data:
        data[key] = _annotate_section(data[key], note)
    return data

def _print_annotate(data):
    sections = data.keys()
    sections.sort()
    print
    print "Annotated sections"
    print "="*len("Annotated sections")
    for section in sections:
        print
        print '[%s]' % section
        keys = data[section].keys()
        keys.sort()
        for key in keys:
            value, notes = data[section][key]
            keyvalue = "%s= %s" % (key, value)
            print keyvalue
            line = '   '
            for note in notes.split():
                if note == '[+]':
                    line = '+= '
                elif note == '[-]':
                    line = '-= '
                else:
                    print line, note
                    line = '   '
    print


def _unannotate_section(section):
    for key in section:
        value, note = section[key]
        section[key] = value
    return section

def _unannotate(data):
    for key in data:
        data[key] = _unannotate_section(data[key])
    return data

_buildout_default_options = _annotate_section({
    'accept-buildout-test-releases': 'false',
    'allow-hosts': '*',
    'allow-picked-versions': 'true',
    'allowed-eggs-from-site-packages': '*',
    'bin-directory': 'bin',
    'develop-eggs-directory': 'develop-eggs',
    'eggs-directory': 'eggs',
    'executable': sys.executable,
    'exec-sitecustomize': 'true',
    'find-links': '',
    'include-site-packages': 'true',
    'install-from-cache': 'false',
    'installed': '.installed.cfg',
    'log-format': '',
    'log-level': 'INFO',
    'newest': 'true',
    'offline': 'false',
    'parts-directory': 'parts',
    'prefer-final': 'false',
    'python': 'buildout',
    'relative-paths': 'false',
    'socket-timeout': '',
    'unzip': 'false',
    'use-dependency-links': 'true',
    }, 'DEFAULT_VALUE')


class Buildout(UserDict.DictMixin):

    def __init__(self, config_file, cloptions,
                 user_defaults=True, windows_restart=False, command=None):

        __doing__ = 'Initializing.'

        self.__windows_restart = windows_restart

        # default options
        data = dict(buildout=_buildout_default_options.copy())
        self._buildout_dir = os.getcwd()

        if not _isurl(config_file):
            config_file = os.path.abspath(config_file)
            base = os.path.dirname(config_file)
            if not os.path.exists(config_file):
                if command == 'init':
                    print 'Creating %r.' % config_file
                    open(config_file, 'w').write('[buildout]\nparts = \n')
                elif command == 'setup':
                    # Sigh. This model of a buildout instance
                    # with methods is breaking down. :(
                    config_file = None
                    data['buildout']['directory'] = ('.', 'COMPUTED_VALUE')
                else:
                    raise zc.buildout.UserError(
                        "Couldn't open %s" % config_file)

            if config_file:
                data['buildout']['directory'] = (os.path.dirname(config_file),
                    'COMPUTED_VALUE')
        else:
            base = None


        cloptions = dict(
            (section, dict((option, (value, 'COMMAND_LINE_VALUE'))
                           for (_, option, value) in v))
            for (section, v) in itertools.groupby(sorted(cloptions),
                                                  lambda v: v[0])
            )
        override = cloptions.get('buildout', {}).copy()

        # load user defaults, which override defaults
        if user_defaults:
            user_config = os.path.join(os.path.expanduser('~'),
                                       '.buildout', 'default.cfg')
            if os.path.exists(user_config):
                _update(data, _open(os.path.dirname(user_config), user_config,
                                    [], data['buildout'].copy(), override))

        # load configuration files
        if config_file:
            _update(data, _open(os.path.dirname(config_file), config_file, [],
                                data['buildout'].copy(), override))

        # apply command-line options
        _update(data, cloptions)

        self._annotated = copy.deepcopy(data)
        self._raw = _unannotate(data)
        self._data = {}
        self._parts = []
        # provide some defaults before options are parsed
        # because while parsing options those attributes might be
        # used already (Gottfried Ganssauge)
        buildout_section = data['buildout']

        # Try to make sure we have absolute paths for standard
        # directories. We do this before doing substitutions, in case
        # a one of these gets read by another section.  If any
        # variable references are used though, we leave it as is in
        # _buildout_path.
        if 'directory' in buildout_section:
            self._buildout_dir = buildout_section['directory']
            for name in ('bin', 'parts', 'eggs', 'develop-eggs'):
                d = self._buildout_path(buildout_section[name+'-directory'])
                buildout_section[name+'-directory'] = d

        # Attributes on this buildout object shouldn't be used by
        # recipes in their __init__.  It can cause bugs, because the
        # recipes will be instantiated below (``options = self['buildout']``)
        # before this has completed initializing.  These attributes are
        # left behind for legacy support but recipe authors should
        # beware of using them.  A better practice is for a recipe to
        # use the buildout['buildout'] options.
        links = buildout_section['find-links']
        self._links = links and links.split() or ()
        allow_hosts = buildout_section['allow-hosts'].split('\n')
        self._allow_hosts = tuple([host.strip() for host in allow_hosts
                                   if host.strip() != ''])
        self._logger = logging.getLogger('zc.buildout')
        self.offline = (buildout_section['offline'] == 'true')
        self.newest = (buildout_section['newest'] == 'true')
        self.accept_buildout_test_releases = (
            buildout_section['accept-buildout-test-releases'] == 'true')

        ##################################################################
        ## WARNING!!!
        ## ALL ATTRIBUTES MUST HAVE REASONABLE DEFAULTS AT THIS POINT
        ## OTHERWISE ATTRIBUTEERRORS MIGHT HAPPEN ANY TIME FROM RECIPES.
        ## RECIPES SHOULD GENERALLY USE buildout['buildout'] OPTIONS, NOT
        ## BUILDOUT ATTRIBUTES.
        ##################################################################
        # initialize some attrs and buildout directories.
        options = self['buildout']

        # now reinitialize
        links = options.get('find-links', '')
        self._links = links and links.split() or ()

        allow_hosts = options['allow-hosts'].split('\n')
        self._allow_hosts = tuple([host.strip() for host in allow_hosts
                                   if host.strip() != ''])

        self._buildout_dir = options['directory']

        # Make sure we have absolute paths for standard directories.  We do this
        # a second time here in case someone overrode these in their configs.
        for name in ('bin', 'parts', 'eggs', 'develop-eggs'):
            d = self._buildout_path(options[name+'-directory'])
            options[name+'-directory'] = d

        if options['installed']:
            options['installed'] = os.path.join(options['directory'],
                                                options['installed'])

        self._setup_logging()

        versions = options.get('versions')
        if versions:
            zc.buildout.easy_install.default_versions(dict(self[versions]))


        self.offline = options.get_bool('offline')
        if self.offline:
            options['newest'] = 'false'
        self.newest = options.get_bool('newest')
        zc.buildout.easy_install.prefer_final(
            options.get_bool('prefer-final'))
        self.accept_buildout_test_releases = options.get_bool(
            'accept-buildout-test-releases')
        zc.buildout.easy_install.use_dependency_links(
            options.get_bool('use-dependency-links'))
        zc.buildout.easy_install.allow_picked_versions(
            options.get_bool('allow-picked-versions'))
        zc.buildout.easy_install.install_from_cache(
            options.get_bool('install-from-cache'))
        zc.buildout.easy_install.always_unzip(options.get_bool('unzip'))
        allowed_eggs = tuple(name.strip() for name in options[
            'allowed-eggs-from-site-packages'].split('\n'))
        self.include_site_packages = options.get_bool('include-site-packages')
        self.exec_sitecustomize = options.get_bool('exec-sitecustomize')
        if (_sys_executable_has_broken_dash_S and
            (not self.include_site_packages or allowed_eggs != ('*',))):
            # We can't do this if the executable has a broken -S.
            warnings.warn(zc.buildout.easy_install.BROKEN_DASH_S_WARNING)
            self.include_site_packages = True
        zc.buildout.easy_install.allowed_eggs_from_site_packages(allowed_eggs)
        zc.buildout.easy_install.include_site_packages(
            self.include_site_packages)

        download_cache = options.get('download-cache')
        if download_cache:
            download_cache = os.path.join(options['directory'], download_cache)
            if not os.path.isdir(download_cache):
                raise zc.buildout.UserError(
                    'The specified download cache:\n'
                    '%r\n'
                    "Doesn't exist.\n"
                    % download_cache)
            download_cache = os.path.join(download_cache, 'dist')
            if not os.path.isdir(download_cache):
                os.mkdir(download_cache)

            zc.buildout.easy_install.download_cache(download_cache)

        # "Use" each of the defaults so they aren't reported as unused options.
        for name in _buildout_default_options:
            options[name]

        # Do the same for extends-cache which is not among the defaults but
        # wasn't recognized as having been used since it was used before
        # tracking was turned on.
        options.get('extends-cache')

        os.chdir(options['directory'])

    def _buildout_path(self, name):
        if '${' in name:
            return name
        return os.path.join(self._buildout_dir, name)

    def bootstrap(self, args):
        __doing__ = 'Bootstrapping.'

        self._setup_directories()

        options = self['buildout']

        # Get a base working set for our distributions that corresponds to the
        # stated desires in the configuration.
        distributions = ['setuptools', 'zc.buildout']
        if options.get('offline') == 'true':
            ws = zc.buildout.easy_install.working_set(
                distributions, options['executable'],
                [options['develop-eggs-directory'],
                 options['eggs-directory']],
                prefer_final=not self.accept_buildout_test_releases,
                )
        else:
            ws = zc.buildout.easy_install.install(
                distributions, options['eggs-directory'],
                links=self._links,
                index=options.get('index'),
                executable=options['executable'],
                path=[options['develop-eggs-directory']],
                newest=self.newest,
                allow_hosts=self._allow_hosts,
                prefer_final=not self.accept_buildout_test_releases,
                )

        # Now copy buildout and setuptools eggs, and record destination eggs:
        entries = []
        for name in 'setuptools', 'zc.buildout':
            r = pkg_resources.Requirement.parse(name)
            dist = ws.find(r)
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

        # Create buildout script.
        # Ideally the (possibly) new version of buildout would get a
        # chance to write the script.  Not sure how to do that.
        ws = pkg_resources.WorkingSet(entries)
        ws.require('zc.buildout')
        partsdir = os.path.join(options['parts-directory'], 'buildout')
        if not os.path.exists(partsdir):
            os.mkdir(partsdir)
        # (Honor the relative-paths option.)
        relative_paths = options.get('relative-paths', 'false')
        if relative_paths == 'true':
            relative_paths = options['directory']
        else:
            assert relative_paths == 'false'
            relative_paths = ''
        if (self.accept_buildout_test_releases and
            self._annotated['buildout']['accept-buildout-test-releases'][1] ==
            'COMMAND_LINE_VALUE'):
            # Bootstrap was called with '--accept-buildout-test-releases'.
            # Continue to honor that setting.
            script_initialization = _early_release_initialization_code
        else:
            script_initialization = ''
        zc.buildout.easy_install.sitepackage_safe_scripts(
            options['bin-directory'], ws, options['executable'], partsdir,
            reqs=['zc.buildout'], relative_paths=relative_paths,
            include_site_packages=self.include_site_packages,
            script_initialization=script_initialization,
            exec_sitecustomize=self.exec_sitecustomize,
            )

    init = bootstrap

    def install(self, install_args):
        __doing__ = 'Installing.'

        self._load_extensions()
        self._setup_directories()

        # Add develop-eggs directory to path so that it gets searched
        # for eggs:
        sys.path.insert(0, self['buildout']['develop-eggs-directory'])

        # Check for updates. This could cause the process to be restarted.
        self._maybe_upgrade()

        # load installed data
        (installed_part_options, installed_exists
         )= self._read_installed_part_options()

        # Remove old develop eggs
        self._uninstall(
            installed_part_options['buildout'].get(
                'installed_develop_eggs', '')
            )

        # Build develop eggs
        installed_develop_eggs = self._develop()
        installed_part_options['buildout']['installed_develop_eggs'
                                           ] = installed_develop_eggs

        if installed_exists:
            self._update_installed(
                installed_develop_eggs=installed_develop_eggs)

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

        if self._log_level < logging.DEBUG:
            sections = list(self)
            sections.sort()
            print
            print 'Configuration data:'
            for section in self._data:
                _save_options(section, self[section], sys.stdout)
            print


        # compute new part recipe signatures
        self._compute_part_signatures(install_parts)

        # uninstall parts that are no-longer used or whose configs
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
                if self._logger.getEffectiveLevel() < logging.DEBUG:
                    for k in old_options:
                        if k not in new_options:
                            self._logger.debug("Part %s, dropped option %s.",
                                               part, k)
                        elif old_options[k] != new_options[k]:
                            self._logger.debug(
                                "Part %s, option %s changed:\n%r != %r",
                                part, k, new_options[k], old_options[k],
                                )
                    for k in new_options:
                        if k not in old_options:
                            self._logger.debug("Part %s, new option %s.",
                                               part, k)

            elif not uninstall_missing:
                continue

            self._uninstall_part(part, installed_part_options)
            installed_parts = [p for p in installed_parts if p != part]

            if installed_exists:
                self._update_installed(parts=' '.join(installed_parts))

        # Check for unused buildout options:
        _check_for_unused_options_in_section(self, 'buildout')

        # install new parts
        for part in install_parts:
            signature = self[part].pop('__buildout_signature__')
            saved_options = self[part].copy()
            recipe = self[part].recipe
            if part in installed_parts: # update
                need_to_save_installed = False
                __doing__ = 'Updating %s.', part
                self._logger.info(*__doing__)
                old_options = installed_part_options[part]
                old_installed_files = old_options['__buildout_installed__']

                try:
                    update = recipe.update
                except AttributeError:
                    update = recipe.install
                    self._logger.warning(
                        "The recipe for %s doesn't define an update "
                        "method. Using its install method.",
                        part)

                try:
                    installed_files = self[part]._call(update)
                except:
                    installed_parts.remove(part)
                    self._uninstall(old_installed_files)
                    if installed_exists:
                        self._update_installed(
                            parts=' '.join(installed_parts))
                    raise

                old_installed_files = old_installed_files.split('\n')
                if installed_files is None:
                    installed_files = old_installed_files
                else:
                    if isinstance(installed_files, str):
                        installed_files = [installed_files]
                    else:
                        installed_files = list(installed_files)

                    need_to_save_installed = [
                        p for p in installed_files
                        if p not in old_installed_files]

                    if need_to_save_installed:
                        installed_files = (old_installed_files
                                           + need_to_save_installed)

            else: # install
                need_to_save_installed = True
                __doing__ = 'Installing %s.', part
                self._logger.info(*__doing__)
                installed_files = self[part]._call(recipe.install)
                if installed_files is None:
                    self._logger.warning(
                        "The %s install returned None.  A path or "
                        "iterable of paths should be returned.",
                        part)
                    installed_files = ()
                elif isinstance(installed_files, str):
                    installed_files = [installed_files]
                else:
                    installed_files = list(installed_files)

            installed_part_options[part] = saved_options
            saved_options['__buildout_installed__'
                          ] = '\n'.join(installed_files)
            saved_options['__buildout_signature__'] = signature

            installed_parts = [p for p in installed_parts if p != part]
            installed_parts.append(part)
            _check_for_unused_options_in_section(self, part)

            if need_to_save_installed:
                installed_part_options['buildout']['parts'] = (
                    ' '.join(installed_parts))
                self._save_installed_options(installed_part_options)
                installed_exists = True
            else:
                assert installed_exists
                self._update_installed(parts=' '.join(installed_parts))

        if installed_develop_eggs:
            if not installed_exists:
                self._save_installed_options(installed_part_options)
        elif (not installed_parts) and installed_exists:
            os.remove(self['buildout']['installed'])

        self._unload_extensions()

    def _update_installed(self, **buildout_options):
        installed = self['buildout']['installed']
        f = open(installed, 'a')
        f.write('\n[buildout]\n')
        for option, value in buildout_options.items():
            _save_option(option, value, f)
        f.close()

    def _uninstall_part(self, part, installed_part_options):
        # uninstall part
        __doing__ = 'Uninstalling %s.', part
        self._logger.info(*__doing__)

        # run uninstall recipe
        recipe, entry = _recipe(installed_part_options[part])
        try:
            uninstaller = _install_and_load(
                recipe, 'zc.buildout.uninstall', entry, self)
            self._logger.info('Running uninstall recipe.')
            uninstaller(part, installed_part_options[part])
        except (ImportError, pkg_resources.DistributionNotFound), v:
            pass

        # remove created files and directories
        self._uninstall(
            installed_part_options[part]['__buildout_installed__'])

    def _setup_directories(self):
        __doing__ = 'Setting up buildout directories'

        # Create buildout directories
        for name in ('bin', 'parts', 'eggs', 'develop-eggs'):
            d = self['buildout'][name+'-directory']
            if not os.path.exists(d):
                self._logger.info('Creating directory %r.', d)
                os.mkdir(d)

    def _develop(self):
        """Install sources by running setup.py develop on them
        """
        __doing__ = 'Processing directories listed in the develop option'

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
                    files = glob.glob(setup)
                    if not files:
                        self._logger.warn("Couldn't develop %r (not found)",
                                          setup)
                    else:
                        files.sort()
                    for setup in files:
                        self._logger.info("Develop: %r", setup)
                        __doing__ = 'Processing develop directory %r.', setup
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
                    "Unexpected entry, %r, in develop-eggs directory.", f)

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

            return result, True
        else:
            return ({'buildout': Options(self, 'buildout', {'parts': ''})},
                    False,
                    )

    def _uninstall(self, installed):
        for f in installed.split('\n'):
            if not f:
                continue
            f = self._buildout_path(f)
            if os.path.isdir(f):
                rmtree(f)
            elif os.path.isfile(f):
                try:
                    os.remove(f)
                except OSError:
                    if not (
                        sys.platform == 'win32' and
                        (realpath(os.path.join(os.path.dirname(sys.argv[0]),
                                               'buildout.exe'))
                         ==
                         realpath(f)
                         )
                        # Sigh. This is the exectable used to run the buildout
                        # and, of course, it's in use. Leave it.
                        ):
                        raise

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

    def _error(self, message, *args):
        raise zc.buildout.UserError(message % args)

    def _setup_logging(self):
        root_logger = logging.getLogger()
        self._logger = logging.getLogger('zc.buildout')
        handler = logging.StreamHandler(sys.stdout)
        log_format = self['buildout']['log-format']
        if not log_format:
            # No format specified. Use different formatter for buildout
            # and other modules, showing logger name except for buildout
            log_format = '%(name)s: %(message)s'
            buildout_handler = logging.StreamHandler(sys.stdout)
            buildout_handler.setFormatter(logging.Formatter('%(message)s'))
            self._logger.propagate = False
            self._logger.addHandler(buildout_handler)

        handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(handler)

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
        __doing__ = 'Checking for upgrades.'

        if not self.newest:
            return

        options = self['buildout']

        specs = ['zc.buildout']
        if zc.buildout.easy_install.is_distribute:
            specs.append('distribute')
        else:
            specs.append('setuptools')
        ws = zc.buildout.easy_install.install(
            [
            (spec + ' ' + options.get(spec+'-version', '')).strip()
            for spec in specs
            ],
            options['eggs-directory'],
            links = options.get('find-links', '').split(),
            index = options.get('index'),
            path = [options['develop-eggs-directory']],
            allow_hosts = self._allow_hosts,
            prefer_final=not self.accept_buildout_test_releases,
            )

        upgraded = []
        for project in 'zc.buildout', 'setuptools':
            req = pkg_resources.Requirement.parse(project)
            project_location = pkg_resources.working_set.find(req).location
            if ws.find(req).location != project_location:
                upgraded.append(ws.find(req))

        if not upgraded:
            return

        __doing__ = 'Upgrading.'

        should_run = realpath(
            os.path.join(os.path.abspath(options['bin-directory']),
                         'buildout')
            )
        if sys.platform == 'win32':
            should_run += '-script.py'

        if (realpath(os.path.abspath(sys.argv[0])) != should_run):
            self._logger.debug("Running %r.", realpath(sys.argv[0]))
            self._logger.debug("Local buildout is %r.", should_run)
            self._logger.warn("Not upgrading because not running a local "
                              "buildout command.")
            return

        if sys.platform == 'win32' and not self.__windows_restart:
            args = map(zc.buildout.easy_install._safe_arg, sys.argv)
            args.insert(1, '-W')
            if not __debug__:
                args.insert(0, '-O')
            args.insert(0, zc.buildout.easy_install._safe_arg (sys.executable))
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
        # Ideally the new version of buildout would get a chance to write the
        # script.  Not sure how to do that.
        partsdir = os.path.join(options['parts-directory'], 'buildout')
        if os.path.exists(partsdir):
            # This is primarily for unit tests, in which .py files change too
            # fast for Python to know to regenerate the .pyc/.pyo files.
            shutil.rmtree(partsdir)
        os.mkdir(partsdir)
        if (self.accept_buildout_test_releases and
            self._annotated['buildout']['accept-buildout-test-releases'][1] ==
            'COMMAND_LINE_VALUE'):
            # Bootstrap was called with '--accept-buildout-test-releases'.
            # Continue to honor that setting.
            script_initialization = _early_release_initialization_code
        else:
            script_initialization = ''
        # (Honor the relative-paths option.)
        relative_paths = options.get('relative-paths', 'false')
        if relative_paths == 'true':
            relative_paths = options['directory']
        else:
            assert relative_paths == 'false'
            relative_paths = ''
        zc.buildout.easy_install.sitepackage_safe_scripts(
            options['bin-directory'], ws, options['executable'], partsdir,
            reqs=['zc.buildout'], relative_paths=relative_paths,
            include_site_packages=self.include_site_packages,
            script_initialization=script_initialization,
            exec_sitecustomize=self.exec_sitecustomize,
            )

        # Restart
        args = map(zc.buildout.easy_install._safe_arg, sys.argv)
        if not __debug__:
            args.insert(0, '-O')
        args.insert(0, zc.buildout.easy_install._safe_arg(sys.executable))
        # We want to make sure that our new site.py is used for rerunning
        # buildout, so we put the partsdir in PYTHONPATH for our restart.
        # This overrides any set PYTHONPATH, but since we generally are
        # trying to run with a completely "clean" python (only the standard
        # library) then that should be fine.
        env = os.environ.copy()
        env['PYTHONPATH'] = partsdir
        if is_jython:
            sys.exit(
                subprocess.Popen(
                    [sys.executable] + list(args), env=env).wait())
        else:
            sys.exit(os.spawnve(os.P_WAIT, sys.executable, args, env))

    def _load_extensions(self):
        __doing__ = 'Loading extensions.'
        specs = self['buildout'].get('extensions', '').split()
        if specs:
            path = [self['buildout']['develop-eggs-directory']]
            if self.offline:
                dest = None
                path.append(self['buildout']['eggs-directory'])
            else:
                dest = self['buildout']['eggs-directory']
                if not os.path.exists(dest):
                    self._logger.info('Creating directory %r.', dest)
                    os.mkdir(dest)

            zc.buildout.easy_install.install(
                specs, dest, path=path,
                working_set=pkg_resources.working_set,
                links = self['buildout'].get('find-links', '').split(),
                index = self['buildout'].get('index'),
                newest=self.newest, allow_hosts=self._allow_hosts,
                prefer_final=not self.accept_buildout_test_releases)

            # Clear cache because extensions might now let us read pages we
            # couldn't read before.
            zc.buildout.easy_install.clear_index_cache()

            for ep in pkg_resources.iter_entry_points('zc.buildout.extension'):
                ep.load()(self)

    def _unload_extensions(self):
        __doing__ = 'Unloading extensions.'
        specs = self['buildout'].get('extensions', '').split()
        if specs:
            for ep in pkg_resources.iter_entry_points(
                'zc.buildout.unloadextension'):
                ep.load()(self)

    def setup(self, args):
        if not args:
            raise zc.buildout.UserError(
                "The setup command requires the path to a setup script or \n"
                "directory containing a setup script, and its arguments."
                )
        setup = args.pop(0)
        if os.path.isdir(setup):
            setup = os.path.join(setup, 'setup.py')

        self._logger.info("Running setup script %r.", setup)
        setup = os.path.abspath(setup)

        fd, tsetup = tempfile.mkstemp()
        exe = zc.buildout.easy_install._safe_arg(sys.executable)
        try:
            os.write(fd, zc.buildout.easy_install.runsetup_template % dict(
                setuptools=pkg_resources_loc,
                setupdir=os.path.dirname(setup),
                setup=setup,
                __file__ = setup,
                ))
            if is_jython:
                arg_list = list()

                for a in args:
                    arg_list.append(zc.buildout.easy_install._safe_arg(a))

                subprocess.Popen([exe] + list(tsetup) + arg_list).wait()

            else:
                os.spawnl(os.P_WAIT, sys.executable, exe, tsetup,
                        *[zc.buildout.easy_install._safe_arg(a)
                            for a in args])
        finally:
            os.close(fd)
            os.remove(tsetup)

    runsetup = setup # backward compat.

    def annotate(self, args):
        _print_annotate(self._annotated)

    def __getitem__(self, section):
        __doing__ = 'Getting section %s.', section
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
    __doing__ = 'Loading recipe %r.', spec
    try:
        req = pkg_resources.Requirement.parse(spec)

        buildout_options = buildout['buildout']
        if pkg_resources.working_set.find(req) is None:
            __doing__ = 'Installing recipe %s.', spec
            if buildout.offline:
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
                newest=buildout.newest,
                allow_hosts=buildout._allow_hosts,
                prefer_final=not buildout.accept_buildout_test_releases)

        __doing__ = 'Loading %s recipe entry %s:%s.', group, spec, entry
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
        self._cooked = {}
        self._data = {}

    def _initialize(self):
        name = self.name
        __doing__ = 'Initializing section %s.', name

        if '<' in self._raw:
            self._raw = self._do_extend_raw(name, self._raw, [])

        # force substitutions
        for k, v in self._raw.items():
            if '${' in v:
                self._dosub(k, v)

        if self.name == 'buildout':
            return # buildout section can never be a part

        recipe = self.get('recipe')
        if not recipe:
            return

        reqs, entry = _recipe(self._data)
        buildout = self.buildout
        recipe_class = _install_and_load(reqs, 'zc.buildout', entry, buildout)

        __doing__ = 'Initializing part %s.', name
        self.recipe = recipe_class(buildout, name, self)
        buildout._parts.append(name)

    def _do_extend_raw(self, name, data, doing):
        if name == 'buildout':
            return data
        if name in doing:
            raise zc.buildout.UserError("Infinite extending loop %r" % name)
        doing.append(name)
        try:
            to_do = data.pop('<', None)
            if to_do is None:
                return data
            __doing__ = 'Loading input sections for %r', name

            result = {}
            for iname in to_do.split('\n'):
                iname = iname.strip()
                if not iname:
                    continue
                raw = self.buildout._raw.get(iname)
                if raw is None:
                    raise zc.buildout.UserError("No section named %r" % iname)
                result.update(self._do_extend_raw(iname, raw, doing))

            result.update(data)
            return result
        finally:
            assert doing.pop() == name

    def _dosub(self, option, v):
        __doing__ = 'Getting option %s:%s.', self.name, option
        seen = [(self.name, option)]
        v = '$$'.join([self._sub(s, seen) for s in v.split('$$')])
        self._cooked[option] = v

    def get(self, option, default=None, seen=None):
        try:
            return self._data[option]
        except KeyError:
            pass

        v = self._cooked.get(option)
        if v is None:
            v = self._raw.get(option)
            if v is None:
                return default

        __doing__ = 'Getting option %s:%s.', self.name, option

        if '${' in v:
            key = self.name, option
            if seen is None:
                seen = [key]
            elif key in seen:
                raise zc.buildout.UserError(
                    "Circular reference in substitutions.\n"
                    )
            else:
                seen.append(key)
            v = '$$'.join([self._sub(s, seen) for s in v.split('$$')])
            seen.pop()

        self._data[option] = v
        return v

    _template_split = re.compile('([$]{[^}]*})').split
    _simple = re.compile('[-a-zA-Z0-9 ._]+$').match
    _valid = re.compile('\${[-a-zA-Z0-9 ._]*:[-a-zA-Z0-9 ._]+}$').match
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

            section, option = s
            if not section:
                section = self.name
            v = self.buildout[section].get(option, None, seen)
            if v is None:
                if option == '_buildout_section_name_':
                    v = self.name
                else:
                    raise MissingOption("Referenced option does not exist:",
                                        section, option)
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
            raise MissingOption("Missing option: %s:%s" % (self.name, key))
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
            if key in self._cooked:
                del self._cooked[key]
        elif key in self._data:
            del self._data[key]
        else:
            raise KeyError, key

    def keys(self):
        raw = self._raw
        return list(self._raw) + [k for k in self._data if k not in raw]

    def copy(self):
        result = self._raw.copy()
        result.update(self._cooked)
        result.update(self._data)
        return result

    def _call(self, f):
        buildout_directory = self.buildout['buildout']['directory']
        self._created = []
        try:
            try:
                os.chdir(buildout_directory)
                return f()
            except:
                for p in self._created:
                    if os.path.isdir(p):
                        rmtree(p)
                    elif os.path.isfile(p):
                        os.remove(p)
                    else:
                        self.buildout._logger.warn("Couldn't clean up %r.", p)
                raise
        finally:
            self._created = None
            os.chdir(buildout_directory)

    def created(self, *paths):
        try:
            self._created.extend(paths)
        except AttributeError:
            raise TypeError(
                "Attempt to register a created path while not installing",
                self.name)
        return self._created

    def query_bool(self, name, default=None):
        """Given a name, return a boolean value for that name.

        ``default``, if given, should be 'true', 'false', or None.
        """
        if default is not None:
            value = self.setdefault(name, default=default)
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

def _save_option(option, value, f):
    value = _spacey_nl.sub(_quote_spacey_nl, value)
    if value.startswith('\n\t'):
        value = '%(__buildout_space_n__)s' + value[2:]
    if value.endswith('\n\t'):
        value = value[:-2] + '%(__buildout_space_n__)s'
    print >>f, option, '=', value

def _save_options(section, options, f):
    print >>f, '[%s]' % section
    items = options.items()
    items.sort()
    for option, value in items:
        _save_option(option, value, f)

def _open(base, filename, seen, dl_options, override):
    """Open a configuration file and return the result as a dictionary,

    Recursively open other files based on buildout options found.
    """
    _update_section(dl_options, override)
    _dl_options = _unannotate_section(dl_options.copy())
    is_temp = False
    download = zc.buildout.download.Download(
        _dl_options, cache=_dl_options.get('extends-cache'), fallback=True,
        hash_name=True)
    if _isurl(filename):
        path, is_temp = download(filename)
        fp = open(path)
        base = filename[:filename.rfind('/')]
    elif _isurl(base):
        if os.path.isabs(filename):
            fp = open(filename)
            base = os.path.dirname(filename)
        else:
            filename = base + '/' + filename
            path, is_temp = download(filename)
            fp = open(path)
            base = filename[:filename.rfind('/')]
    else:
        filename = os.path.join(base, filename)
        fp = open(filename)
        base = os.path.dirname(filename)

    if filename in seen:
        if is_temp:
            fp.close()
            os.remove(path)
        raise zc.buildout.UserError("Recursive file include", seen, filename)

    root_config_file = not seen
    seen.append(filename)

    result = {}

    parser = ConfigParser.RawConfigParser()
    parser.optionxform = lambda s: s
    parser.readfp(fp)
    if is_temp:
        fp.close()
        os.remove(path)

    extends = extended_by = None
    for section in parser.sections():
        options = dict(parser.items(section))
        if section == 'buildout':
            extends = options.pop('extends', extends)
            extended_by = options.pop('extended-by', extended_by)
        result[section] = options

    result = _annotate(result, filename)

    if root_config_file and 'buildout' in result:
        dl_options = _update_section(dl_options, result['buildout'])

    if extends:
        extends = extends.split()
        eresult = _open(base, extends.pop(0), seen, dl_options, override)
        for fname in extends:
            _update(eresult, _open(base, fname, seen, dl_options, override))
        result = _update(eresult, result)

    if extended_by:
        self._logger.warn(
            "The extendedBy option is deprecated.  Stop using it."
            )
        for fname in extended_by.split():
            result = _update(result,
                             _open(base, fname, seen, dl_options, override))

    seen.pop()
    return result


ignore_directories = '.svn', 'CVS'
def _dir_hash(dir):
    hash = md5()
    for (dirpath, dirnames, filenames) in os.walk(dir):
        dirnames[:] = [n for n in dirnames if n not in ignore_directories]
        filenames[:] = [f for f in filenames
                        if (not (f.endswith('pyc') or f.endswith('pyo'))
                            and os.path.exists(os.path.join(dirpath, f)))
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

def _update_section(s1, s2):
    s2 = s2.copy() # avoid mutating the second argument, which is unexpected
    for k, v in s2.items():
        v2, note2 = v
        if k.endswith('+'):
            key = k.rstrip(' +')
            v1, note1 = s1.get(key, ("", ""))
            newnote = ' [+] '.join((note1, note2)).strip()
            s2[key] = "\n".join((v1).split('\n') +
                v2.split('\n')), newnote
            del s2[k]
        elif k.endswith('-'):
            key = k.rstrip(' -')
            v1, note1 = s1.get(key, ("", ""))
            newnote = ' [-] '.join((note1, note2)).strip()
            s2[key] = ("\n".join(
                [v for v in v1.split('\n')
                   if v not in v2.split('\n')]), newnote)
            del s2[k]

    s1.update(s2)
    return s1

def _update(d1, d2):
    for section in d2:
        if section in d1:
            d1[section] = _update_section(d1[section], d2[section])
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

def _doing():
    _, v, tb = sys.exc_info()
    message = str(v)
    doing = []
    while tb is not None:
        d = tb.tb_frame.f_locals.get('__doing__')
        if d:
            doing.append(d)
        tb = tb.tb_next

    if doing:
        sys.stderr.write('While:\n')
        for d in doing:
            if not isinstance(d, str):
                d = d[0] % d[1:]
            sys.stderr.write('  %s\n' % d)

def _error(*message):
    sys.stderr.write('Error: ' + ' '.join(message) +'\n')
    sys.exit(1)

_internal_error_template = """
An internal error occurred due to a bug in either zc.buildout or in a
recipe being used:
"""

def _check_for_unused_options_in_section(buildout, section):
    options = buildout[section]
    unused = [option for option in options._raw if option not in options._data]
    if unused:
        buildout._logger.warn("Unused options for %s: %s."
                              % (section, ' '.join(map(repr, unused)))
                              )

_early_release_initialization_code = """\
sys.argv.insert(1, 'buildout:accept-buildout-test-releases=true')
print ('NOTE: Accepting early releases of build system packages.  Rerun '
       'bootstrap without --accept-buildout-test-releases (-t) to return to '
       'default behavior.')
"""

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

  -t socket_timeout

     Specify the socket timeout in seconds.

  -U

     Don't read user defaults.

  -o

    Run in off-line mode.  This is equivalent to the assignment
    buildout:offline=true.

  -O

    Run in non-off-line mode.  This is equivalent to the assignment
    buildout:offline=false.  This is the default buildout mode.  The
    -O option would normally be used to override a true offline
    setting in a configuration file.

  -n

    Run in newest mode.  This is equivalent to the assignment
    buildout:newest=true.  With this setting, which is the default,
    buildout will try to find the newest versions of distributions
    available that satisfy its requirements.

  -N

    Run in non-newest mode.  This is equivalent to the assignment
    buildout:newest=false.  With this setting, buildout will not seek
    new distributions if installed distributions satisfy it's
    requirements.

  -D

    Debug errors.  If an error occurs, then the post-mortem debugger
    will be started. This is especially useful for debuging recipe
    problems.

  -s

    Squelch warnings about using an executable with a broken -S
    implementation.

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

    Note that the semantics differ depending on whether any parts are
    specified.  If parts are specified, then only those parts will be
    installed. If no parts are specified, then the parts specified by
    the buildout parts option will be installed along with all of
    their dependencies.

  bootstrap

    Create a new buildout in the current working directory, copying
    the buildout and setuptools eggs and, creating a basic directory
    structure and a buildout-local buildout script.

  init

    Initialize a buildout, creating a buildout.cfg file if it doesn't
    exist and then performing the same actions as for the buildout
    command.

  setup script [setup command and options]

    Run a given setup script arranging that setuptools is in the
    script's path and and that it has been imported so that
    setuptools-provided commands (like bdist_egg) can be used even if
    the setup script doesn't import setuptools itself.

    The script can be given either as a script path or a path to a
    directory containing a setup.py script.

  annotate

    Display annotated sections. All sections are displayed, sorted
    alphabetically. For each section, all key-value pairs are displayed,
    sorted alphabetically, along with the origin of the value (file name or
    COMPUTED_VALUE, DEFAULT_VALUE, COMMAND_LINE_VALUE).

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
    debug = False
    ignore_broken_dash_s = False
    while args:
        if args[0][0] == '-':
            op = orig_op = args.pop(0)
            op = op[1:]
            while op and op[0] in 'vqhWUoOnNDAs':
                if op[0] == 'v':
                    verbosity += 10
                elif op[0] == 'q':
                    verbosity -= 10
                elif op[0] == 'W':
                    windows_restart = True
                elif op[0] == 'U':
                    user_defaults = False
                elif op[0] == 'o':
                    options.append(('buildout', 'offline', 'true'))
                elif op[0] == 'O':
                    options.append(('buildout', 'offline', 'false'))
                elif op[0] == 'n':
                    options.append(('buildout', 'newest', 'true'))
                elif op[0] == 'N':
                    options.append(('buildout', 'newest', 'false'))
                elif op[0] == 'D':
                    debug = True
                elif op[0] == 's':
                    ignore_broken_dash_s = True
                else:
                    _help()
                op = op[1:]

            if op[:1] in  ('c', 't'):
                op_ = op[:1]
                op = op[1:]

                if op_ == 'c':
                    if op:
                        config_file = op
                    else:
                        if args:
                            config_file = args.pop(0)
                        else:
                            _error("No file name specified for option", orig_op)
                elif op_ == 't':
                    try:
                        timeout = int(args.pop(0))
                    except IndexError:
                        _error("No timeout value specified for option", orig_op)
                    except ValueError:
                        _error("No timeout value must be numeric", orig_op)

                    import socket
                    print 'Setting socket time out to %d seconds' % timeout
                    socket.setdefaulttimeout(timeout)

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

    if verbosity < 0 or ignore_broken_dash_s:
        broken_dash_S_filter_action = 'ignore'
    elif verbosity == 0: # This is the default.
        broken_dash_S_filter_action = 'once'
    else:
        broken_dash_S_filter_action = 'default'
    warnings.filterwarnings(
        broken_dash_S_filter_action,
        re.escape(
            zc.buildout.easy_install.BROKEN_DASH_S_WARNING),
        UserWarning)
    if verbosity:
        options.append(('buildout', 'verbosity', str(verbosity)))

    if args:
        command = args.pop(0)
        if command not in (
            'install', 'bootstrap', 'runsetup', 'setup', 'init',
            'annotate',
            ):
            _error('invalid command:', command)
    else:
        command = 'install'

    try:
        try:
            buildout = Buildout(config_file, options,
                                user_defaults, windows_restart, command)
            getattr(buildout, command)(args)
        except SystemExit:
            pass
        except Exception, v:
            _doing()
            exc_info = sys.exc_info()
            import pdb, traceback
            if debug:
                traceback.print_exception(*exc_info)
                sys.stderr.write('\nStarting pdb:\n')
                pdb.post_mortem(exc_info[2])
            else:
                if isinstance(v, (zc.buildout.UserError,
                                  distutils.errors.DistutilsError,
                                  )
                              ):
                    _error(str(v))
                else:
                    sys.stderr.write(_internal_error_template)
                    traceback.print_exception(*exc_info)
                    sys.exit(1)


    finally:
        logging.shutdown()

if sys.version_info[:2] < (2, 4):
    def reversed(iterable):
        result = list(iterable);
        result.reverse()
        return result
