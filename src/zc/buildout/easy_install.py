#############################################################################
#
# Copyright (c) 2005 Zope Foundation and Contributors.
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
"""Python easy_install API

This module provides a high-level Python API for installing packages.
It doesn't install scripts.  It uses setuptools and requires it to be
installed.
"""

import copy
import distutils.errors
import email
import errno
import glob
import logging
import operator
import os
import pkg_resources
import posixpath
import re
import setuptools.archive_util
import setuptools.command.easy_install
import setuptools.command.setopt
import shutil
import subprocess
import sys
import tempfile
import zc.buildout
import zc.buildout.rmtree
import zipfile
from . import _package_index
from functools import cached_property
from packaging import specifiers
from packaging.utils import canonicalize_name
from packaging.utils import is_normalized_name
from pkg_resources import Distribution
from setuptools.wheel import Wheel
from zc.buildout import WINDOWS
from zc.buildout.utils import IS_SETUPTOOLS_80_PLUS
from zc.buildout.utils import normalize_name
import warnings
import csv



BIN_SCRIPTS = 'Scripts' if WINDOWS else 'bin'

warnings.filterwarnings(
    'ignore', '.+is being parsed as a legacy, non PEP 440, version')

_oprp = getattr(os.path, 'realpath', lambda path: path)
def realpath(path):
    return os.path.normcase(os.path.abspath(_oprp(path)))

default_index_url = os.environ.get(
    'buildout_testing_index_url',
    'https://pypi.org/simple',
    )

logger = logging.getLogger('zc.buildout.easy_install')
macosVersionString = re.compile(r"macosx-(\d+)\.(\d+)-(.*)")

url_match = re.compile('[a-z0-9+.-]+://').match
is_source_encoding_line = re.compile(r'coding[:=]\s*([-\w.]+)').search
# Source encoding regex from http://www.python.org/dev/peps/pep-0263/

is_win32 = sys.platform == 'win32'
is_jython = sys.platform.startswith('java')

if is_jython:
    import java.lang.System
    jython_os_name = (java.lang.System.getProperties()['os.name']).lower()

# Include buildout and setuptools eggs in paths.  We get this
# initially from the entire working set.  Later, we'll use the install
# function to narrow to just the buildout and setuptools paths.
buildout_and_setuptools_path = sorted({d.location for d in pkg_resources.working_set})
setuptools_path = buildout_and_setuptools_path
pip_path = buildout_and_setuptools_path
logger.debug('before restricting versions: pip_path %r', pip_path)

FILE_SCHEME = re.compile('file://', re.I).match
DUNDER_FILE_PATTERN = re.compile(r"__file__ = '(?P<filename>.+)'$")


class EnvironmentMixin(object):
    """Mixin class for Environment and PackageIndex for canonicalized names.

    * pkg_resources defines the Environment class
    * setuptools defines a PackageIndex class that inherits from Environment
    * Buildout needs a few fixes that should be used by both.

    The fixes are needed for this issue, where distributions created by
    setuptools 69.3+ get a different name than with older versions:
    https://github.com/buildout/buildout/issues/647
    """
    def __getitem__(self, project_name):
        """Return a newest-to-oldest list of distributions for `project_name`

        Uses case-insensitive `project_name` comparison, assuming all the
        project's distributions use their project's name converted to all
        lowercase as their key.

        """
        distribution_key = normalize_name(project_name)
        return self._distmap.get(distribution_key, [])

    def add(self, dist):
        """Add `dist` if we ``can_add()`` it and it has not already been added
        """
        if self.can_add(dist) and dist.has_version():
            # Instead of 'dist.key' we add a normalized version.
            distribution_key = normalize_name(dist.key)
            dists = self._distmap.setdefault(distribution_key, [])
            if dist not in dists:
                dists.append(dist)
                dists.sort(key=operator.attrgetter('hashcmp'), reverse=True)


class Environment(EnvironmentMixin, pkg_resources.Environment):
    """Buildout version of Environment with canonicalized names.

    * pkg_resources defines the Environment class
    * setuptools defines a PackageIndex class that inherits from Environment
    * Buildout needs a few fixes that should be used by both.

    The fixes are needed for this issue, where distributions created by
    setuptools 69.3+ get a different name than with older versions:
    https://github.com/buildout/buildout/issues/647

    And since May 2025 we override the can_add method to work better on Mac:
    accept distributions when the architecture (machine type) matches,
    instead of failing when the major or minor version do not match.
    See long explanation in https://github.com/buildout/buildout/pull/707
    It boils down to this, depending on how you installed Python:

    % bin/zopepy
    >>> import pkg_resources
    >>> pkg_resources.get_platform()
    'macosx-11.0-arm64'
    >>> pkg_resources.get_supported_platform()
    'macosx-15.4-arm64'

    Here macosx-11.0 is the platform on which the Python was built/compiled.
    And macosx-15.4 is the current platform (my laptop).

    This gives problems when we get a Mac-specific wheel.  We turn it into an
    egg that has the result of get_supported_platform() in its name.
    Then our code in easy_install._get_matching_dist_in_location creates a
    pkg_resources.Environment with the egg location.  Under the hood,
    pkg_resources.compatible_platforms is called, and this does not find any
    matching dists because it compares the platform in the egg name with that
    of the system, which is pkg_resources.get_platform().

    So an egg created on the current machine by the current Python may not be
    recognized.  This is obviously wrong.
    """

    @cached_property
    def _mac_machine_type(self):
        """Machine type (architecture) on Mac.

        Adapted from pkg_resources.compatible_platforms.
        If self.platform is something like 'macosx-15.4-arm64', we return 'arm64.
        """
        match = macosVersionString.match(self.platform)
        if match is None:
            # no Mac
            return ""
        return match.group(3)

    def can_add(self, dist: Distribution) -> bool:
        """Is distribution `dist` acceptable for this environment?

        The distribution must match the platform and python version
        requirements specified when this environment was created, or False
        is returned.

        For Mac we make a change compared to the original.  Platforms like
        'macosx-11.0-arm64' and 'macosx-15.4-arm64' are considered compatible.
        """
        if super().can_add(dist):
            return True
        if sys.platform != "darwin":
            # Our override is only useful on Mac OSX.
            return False

        # The rest of the code is a combination of the original
        # pkg_resources.Environment.can_add and pkg_resources.compatible_platforms.
        py_compat = (
            self.python is None
            or dist.py_version is None
            or dist.py_version == self.python
        )
        if not py_compat:
            return False
        provMac = macosVersionString.match(dist.platform)
        if not provMac:
            # The dist is not for Mac.
            return False
        provided_machine_type = provMac.group(3)
        if provided_machine_type != self._mac_machine_type:
            return False
        logger.debug(
            "Accepted dist %s although its provided platform %s does not "
            "match our supported platform %s.",
            dist,
            dist.platform,
            self.platform,
        )
        return True


class AllowHostsPackageIndex(EnvironmentMixin, _package_index.PackageIndex):
    """Will allow urls that are local to the system.

    This class had its own url_ok method, but we merged this into
    _package_index.py.
    """
    pass


_indexes = {}
def _get_index(index_url, find_links, allow_hosts=('*',)):
    key = index_url, tuple(find_links)
    index = _indexes.get(key)
    if index is not None:
        return index

    if index_url is None:
        index_url = default_index_url
    if index_url.startswith('file://'):
        index_url = index_url[7:]
    index = AllowHostsPackageIndex(index_url, hosts=allow_hosts)

    if find_links:
        index.add_find_links(find_links)

    _indexes[key] = index
    return index

clear_index_cache = _indexes.clear

if is_win32:
    # work around spawn lamosity on windows
    # XXX need safe quoting (see the subproces.list2cmdline) and test
    def _safe_arg(arg):
        return '"%s"' % arg
else:
    _safe_arg = str

if is_win32:
    # In setuptools 80.3 the setuptools.command.easy_install module was first
    # removed, and later only partially restored as wrapper around the new
    # setuptools._scripts module.
    try:
        from setuptools._scripts import get_win_launcher
    except ImportError:
        from setuptools.command.easy_install import get_win_launcher
else:
    get_win_launcher = None


def call_subprocess(args, **kw):
    if subprocess.call(args, **kw) != 0:
        raise Exception(
            "Failed to run command:\n%s"
            % repr(args)[1:-1])


def get_subprocess_output(args, **kw):
    result = subprocess.run(
        args, **kw,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    stdout = result.stdout.decode("utf-8")
    if result.returncode:
        cmd = repr(args)[1:-1]
        msg = f"Failed to run command:\n{cmd}"
        logger.error(msg + "\nError output follows:")
        print(stdout)
        raise Exception(msg)
    return stdout


def _execute_permission():
    current_umask = os.umask(0o022)
    # os.umask only returns the current umask if you also give it one, so we
    # have to give it a dummy one and immediately set it back to the real
    # value...  Distribute does the same.
    os.umask(current_umask)
    return 0o777 - current_umask



def get_namespace_package_paths(dist):
    """
    Generator of the expected pathname of each __init__.py file of the
    namespaces of a distribution.
    """
    base = [dist.location]
    init = ['__init__.py']
    for namespace in dist.get_metadata_lines('namespace_packages.txt'):
        yield os.path.join(*(base + namespace.split('.') + init))

def namespace_packages_need_pkg_resources(dist):
    if os.path.isfile(dist.location):
        # Zipped egg, with namespaces, surely needs setuptools
        return True
    # If they have `__init__.py` files that use pkg_resources and don't
    # fallback to using `pkgutil`, then they need setuptools/pkg_resources:
    for path in get_namespace_package_paths(dist):
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                source = f.read()
                if (source and
                        b'pkg_resources' in source and
                        not b'pkgutil' in source):
                    return True
    return False

def dist_needs_pkg_resources(dist):
    """
    A distribution needs setuptools/pkg_resources added as requirement if:

        * It has namespace packages declared with:
        - `pkg_resources.declare_namespace()`
        * Those namespace packages don't fall back to `pkgutil`
        * It doesn't have `setuptools/pkg_resources` as requirement already
    """

    return (
        dist.has_metadata('namespace_packages.txt') and
        # This will need to change when `pkg_resources` gets its own
        # project:
        'setuptools' not in {r.project_name for r in dist.requires()} and
        namespace_packages_need_pkg_resources(dist)
    )


class Installer(object):

    _versions = {}
    _required_by = {}
    _picked_versions = {}
    _download_cache = None
    _install_from_cache = False
    _prefer_final = True
    _use_dependency_links = True
    _allow_picked_versions = True
    _store_required_by = False
    _allow_unknown_extras = False

    def __init__(self,
                 dest=None,
                 links=(),
                 index=None,
                 executable=sys.executable,
                 always_unzip=None, # Backward compat :/
                 path=None,
                 newest=True,
                 versions=None,
                 use_dependency_links=None,
                 allow_hosts=('*',),
                 check_picked=True,
                 allow_unknown_extras=False,
                 ):
        assert executable == sys.executable, (executable, sys.executable)
        self._dest = dest if dest is None else pkg_resources.normalize_path(dest)
        self._allow_hosts = allow_hosts
        self._allow_unknown_extras = allow_unknown_extras

        if self._install_from_cache:
            if not self._download_cache:
                raise ValueError("install_from_cache set to true with no"
                                 " download cache")
            links = ()
            index = 'file://' + self._download_cache

        if use_dependency_links is not None:
            self._use_dependency_links = use_dependency_links
        self._links = links = list(self._fix_file_links(links))
        if self._download_cache and (self._download_cache not in links):
            links.insert(0, self._download_cache)

        self._index_url = index
        path = (path and path[:] or []) + buildout_and_setuptools_path
        self._path = path
        if self._dest is None:
            newest = False
        self._newest = newest
        self._env = self._make_env()
        self._index = _get_index(index, links, self._allow_hosts)
        self._requirements_and_constraints = []
        self._check_picked = check_picked

        if versions is not None:
            self._versions = normalize_versions(versions)

    def _make_env(self):
        full_path = self._get_dest_dist_paths() + self._path
        env = Environment(full_path)
        # this needs to be called whenever self._env is modified (or we could
        # make an Environment subclass):
        self._eggify_env_dest_dists(env, self._dest)
        return env

    def _env_rescan_dest(self):
        self._env.scan(self._get_dest_dist_paths())
        self._eggify_env_dest_dists(self._env, self._dest)

    def _get_dest_dist_paths(self):
        dest = self._dest
        if dest is None:
            return []
        eggs = glob.glob(os.path.join(dest, '*.egg'))
        dists = [os.path.dirname(dist_info) for dist_info in
                 glob.glob(os.path.join(dest, '*', '*.dist-info'))]
        return list(set(eggs + dists))

    @staticmethod
    def _eggify_env_dest_dists(env, dest):
        """
        Make sure everything found under `dest` is seen as an egg, even if it's
        some other kind of dist.
        """
        for project_name in env:
            for dist in env[project_name]:
                if os.path.dirname(dist.location) == dest:
                    dist.precedence = pkg_resources.EGG_DIST

    def _version_conflict_information(self, name):
        """Return textual requirements/constraint information for debug purposes

        We do a very simple textual search, as that filters out most
        extraneous information without missing anything.

        """
        output = [
            "Version and requirements information containing %s:" % name]
        version_constraint = self._versions.get(canonicalize_name(name))
        if version_constraint:
            output.append(
                "[versions] constraint on %s: %s" % (name, version_constraint))
        output += [line for line in self._requirements_and_constraints
                   if name.lower() in line.lower()]
        return '\n  '.join(output)

    def _satisfied(self, req, source=None):
        dists = [dist for dist in self._env[req.project_name] if dist in req]
        if not dists:
            logger.debug('We have no distributions for %s that satisfies %r.',
                         req.project_name, str(req))

            return None, self._obtain(req, source)

        # Note that dists are sorted from best to worst, as promised by
        # env.__getitem__

        for dist in dists:
            if (dist.precedence == pkg_resources.DEVELOP_DIST):
                logger.debug('We have a develop egg: %s', dist)
                return dist, None

        # Special common case, we have a specification for a single version:
        specs = req.specs
        if len(specs) == 1 and specs[0][0] == '==':
            logger.debug('We have the distribution that satisfies %r.',
                         str(req))
            return dists[0], None

        if self._prefer_final:
            fdists = [dist for dist in dists
                      if self._final_version(dist.parsed_version)
                      ]
            if fdists:
                # There are final dists, so only use those
                dists = fdists

        if not self._newest:
            # We don't need the newest, so we'll use the newest one we
            # find, which is the first returned by
            # Environment.__getitem__.
            return dists[0], None

        best_we_have = dists[0] # Because dists are sorted from best to worst

        # We have some installed distros.  There might, theoretically, be
        # newer ones.  Let's find out which ones are available and see if
        # any are newer.  We only do this if we're willing to install
        # something, which is only true if dest is not None:

        best_available = self._obtain(req, source)

        if best_available is None:
            # That's a bit odd.  There aren't any distros available.
            # We should use the best one we have that meets the requirement.
            logger.debug(
                'There are no distros available that meet %r.\n'
                'Using our best, %s.',
                str(req), best_we_have)
            return best_we_have, None

        if self._prefer_final:
            if self._final_version(best_available.parsed_version):
                if self._final_version(best_we_have.parsed_version):
                    if (best_we_have.parsed_version
                        <
                        best_available.parsed_version
                        ):
                        return None, best_available
                else:
                    return None, best_available
            else:
                if (not self._final_version(best_we_have.parsed_version)
                    and
                    (best_we_have.parsed_version
                     <
                     best_available.parsed_version
                     )
                    ):
                    return None, best_available
        else:
            if (best_we_have.parsed_version
                <
                best_available.parsed_version
                ):
                return None, best_available

        logger.debug(
            'We have the best distribution that satisfies %r.',
            str(req))
        return best_we_have, None

    def _call_pip_install(self, spec, dest, dist):

        tmp = tempfile.mkdtemp(dir=dest)
        try:
            paths = call_pip_install(spec, tmp)

            dists = []
            env = Environment(paths)
            for project in env:
                dists.extend(env[project])

            if not dists:
                raise zc.buildout.UserError("Couldn't install: %s" % dist)

            if len(dists) > 1:
                logger.warn("Installing %s\n"
                            "caused multiple distributions to be installed:\n"
                            "%s\n",
                            dist, '\n'.join(map(str, dists)))
            else:
                d = dists[0]
                if d.project_name != dist.project_name:
                    logger.warn("Installing %s\n"
                                "Caused installation of a distribution:\n"
                                "%s\n"
                                "with a different project name.",
                                dist, d)
                if d.version != dist.version:
                    logger.warn("Installing %s\n"
                                "Caused installation of a distribution:\n"
                                "%s\n"
                                "with a different version.",
                                dist, d)

            result = []
            for d in dists:
                result.append(_move_to_eggs_dir_and_compile(d, dest))

            return result

        finally:
            zc.buildout.rmtree.rmtree(tmp)

    def _obtain(self, requirement, source=None):
        # initialize out index for this project:
        index = self._index

        if index.obtain(requirement) is None:
            # Nothing is available.
            return None

        # Filter the available dists for the requirement and source flag
        dists = [dist for dist in index[requirement.project_name]
                 if ((dist in requirement)
                     and
                     ((not source) or
                      (dist.precedence == pkg_resources.SOURCE_DIST)
                      )
                     )
                 ]

        # If we prefer final dists, filter for final and use the
        # result if it is non empty.
        if self._prefer_final:
            fdists = [dist for dist in dists
                      if self._final_version(dist.parsed_version)
                      ]
            if fdists:
                # There are final dists, so only use those
                dists = fdists

        # Now find the best one:
        best = []
        bestv = None
        for dist in dists:
            distv = dist.parsed_version
            if bestv is None or distv > bestv:
                best = [dist]
                bestv = distv
            elif distv == bestv:
                best.append(dist)

        if not best:
            return None

        if len(best) == 1:
            return best[0]

        if self._download_cache:
            for dist in best:
                if (realpath(os.path.dirname(dist.location))
                    ==
                    self._download_cache
                    ):
                    return dist

        best.sort()
        return best[-1]

    def _fetch(self, dist, tmp, download_cache):
        if (download_cache
            and (realpath(os.path.dirname(dist.location)) == download_cache)
            ):
            logger.debug("Download cache has %s at: %s", dist, dist.location)
            return dist

        logger.debug("Fetching %s from: %s", dist, dist.location)
        new_location = self._index.download(dist.location, tmp)
        if (download_cache
            and (realpath(new_location) == realpath(dist.location))
            and os.path.isfile(new_location)
            ):
            # setuptools avoids making extra copies, but we want to copy
            # to the download cache
            shutil.copy2(new_location, tmp)
            new_location = os.path.join(tmp, os.path.basename(new_location))

        return dist.clone(location=new_location)

    def _get_dist(self, requirement, ws):
        __doing__ = 'Getting distribution for %r.', str(requirement)

        # Maybe an existing dist is already the best dist that satisfies the
        # requirement.  If not, get a link to an available distribution that
        # we could download.  The method returns a tuple with an existing
        # dist or an available dist.  Either 'dist' is None, or 'avail'
        # is None, or both are None.
        dist, avail = self._satisfied(requirement)

        if dist is None:
            if self._dest is None:
                raise zc.buildout.UserError(
                    "We don't have a distribution for %s\n"
                    "and can't install one in offline (no-install) mode.\n"
                    % requirement)

            logger.info(*__doing__)

            if avail is None:
                # We have no existing dist, and none is available for download.
                raise MissingDistribution(requirement, ws)

            # We may overwrite distributions, so clear importer
            # cache.
            sys.path_importer_cache.clear()

            tmp = self._download_cache
            if tmp is None:
                tmp = tempfile.mkdtemp('get_dist')

            try:
                dist = self._fetch(avail, tmp, self._download_cache)

                if dist is None:
                    raise zc.buildout.UserError(
                        "Couldn't download distribution %s." % avail)

                dists = [_move_to_eggs_dir_and_compile(dist, self._dest)]
                for _d in dists:
                    if _d not in ws:
                        ws.add(_d, replace=True)

            finally:
                if tmp != self._download_cache:
                    zc.buildout.rmtree.rmtree(tmp)

            self._env_rescan_dest()
            dist = self._env.best_match(requirement, ws)

            logger.info("Got %s.", dist)

        else:
            dists = [dist]
            if dist not in ws:
                ws.add(dist)


        if not self._install_from_cache and self._use_dependency_links:
            self._add_dependency_links_from_dists(dists)

        if self._check_picked:
            self._check_picked_requirement_versions(requirement, dists)

        return dists

    def _add_dependency_links_from_dists(self, dists):
        reindex = False
        links = self._links
        for dist in dists:
            if dist.has_metadata('dependency_links.txt'):
                for link in dist.get_metadata_lines('dependency_links.txt'):
                    link = link.strip()
                    if link not in links:
                        logger.debug('Adding find link %r from %s',
                                     link, dist)
                        links.append(link)
                        reindex = True
        if reindex:
            self._index = _get_index(self._index_url, links, self._allow_hosts)

    def _check_picked_requirement_versions(self, requirement, dists):
        """ Check whether we picked a version and, if we did, report it """
        for dist in dists:
            if not (dist.precedence == pkg_resources.DEVELOP_DIST
                or
                (len(requirement.specs) == 1
                 and
                 requirement.specs[0][0] == '==')
                ):
                logger.debug('Picked: %s = %s',
                             dist.project_name, dist.version)
                self._picked_versions[dist.project_name] = dist.version

                if not self._allow_picked_versions:
                    msg = NOT_PICKED_AND_NOT_ALLOWED.format(
                        name=dist.project_name,
                        version=dist.version
                    )
                    raise zc.buildout.UserError(msg)

    def _maybe_add_setuptools(self, ws, dist):
        if dist_needs_pkg_resources(dist):
            # We have a namespace package but no requirement for setuptools
            if dist.precedence == pkg_resources.DEVELOP_DIST:
                logger.warning(
                    "Develop distribution: %s\n"
                    "uses namespace packages but the distribution "
                    "does not require setuptools.",
                    dist)
            requirement = self._constrain(
                pkg_resources.Requirement.parse('setuptools')
                )
            if ws.find(requirement) is None:
                self._get_dist(requirement, ws)

    def _constrain(self, requirement):
        """Return requirement with optional [versions] constraint added."""
        canonical_name = canonicalize_name(requirement.project_name)
        constraint = self._versions.get(canonical_name)
        if constraint:
            try:
                requirement = _constrained_requirement(constraint,
                                                       requirement)
            except IncompatibleConstraintError:
                logger.info(self._version_conflict_information(canonical_name))
                raise

        return requirement

    def install(self, specs, working_set=None):

        logger.debug('Installing %s.', repr(specs)[1:-1])
        self._requirements_and_constraints.append(
            "Base installation request: %s" % repr(specs)[1:-1])

        for_buildout_run = bool(working_set)

        requirements = [pkg_resources.Requirement.parse(spec)
                        for spec in specs]

        requirements = [
            self._constrain(requirement)
            for requirement in requirements
            if not requirement.marker or requirement.marker.evaluate()
        ]

        if working_set is None:
            ws = pkg_resources.WorkingSet([])
        else:
            ws = working_set

        for requirement in requirements:
            for dist in self._get_dist(requirement, ws):
                self._maybe_add_setuptools(ws, dist)

        # OK, we have the requested distributions and they're in the working
        # set, but they may have unmet requirements.  We'll resolve these
        # requirements. This is code modified from
        # pkg_resources.WorkingSet.resolve.  We can't reuse that code directly
        # because we have to constrain our requirements (see
        # versions_section_ignored_for_dependency_in_favor_of_site_packages in
        # zc.buildout.tests).
        requirements.reverse() # Set up the stack.
        processed = {}  # This is a set of processed requirements.
        best = {}  # This is a mapping of package name -> dist.
        # Note that we don't use the existing environment, because we want
        # to look for new eggs unless what we have is the best that
        # matches the requirement.
        env = Environment(ws.entries)

        while requirements:
            # Process dependencies breadth-first.
            current_requirement = requirements.pop(0)
            req = self._constrain(current_requirement)
            if req in processed:
                # Ignore cyclic or redundant dependencies.
                continue
            dist = best.get(req.key)
            if dist is None:
                try:
                    dist = env.best_match(req, ws)
                except pkg_resources.VersionConflict as err:
                    logger.debug(
                        "Version conflict while processing requirement %s "
                        "(constrained to %s)",
                        current_requirement, req)
                    # Installing buildout itself and its extensions and
                    # recipes requires the global
                    # ``pkg_resources.working_set`` to be active, which also
                    # includes all system packages. So there might be
                    # conflicts, which are fine to ignore. We'll grab the
                    # correct version a few lines down.
                    if not for_buildout_run:
                        raise VersionConflict(err, ws)
            if dist is None:
                if self._dest:
                    logger.debug('Getting required %r', str(req))
                else:
                    logger.debug('Adding required %r', str(req))
                self._log_requirement(ws, req)
                for dist in self._get_dist(req, ws):
                    self._maybe_add_setuptools(ws, dist)
            if dist not in req:
                # Oops, the "best" so far conflicts with a dependency.
                logger.info(self._version_conflict_information(req.key))
                raise VersionConflict(
                    pkg_resources.VersionConflict(dist, req), ws)

            best[req.key] = dist

            missing_requested = sorted(
                set(req.extras) - set(dist.extras)
            )
            for missing in missing_requested:
                logger.warning(
                    '%s does not provide the extra \'%s\'',
                    dist, missing
                )

            if missing_requested:
                if not self._allow_unknown_extras:
                    raise zc.buildout.UserError(
                        "Couldn't find the required extra. "
                        "This means the requirement is incorrect. "
                        "If the requirement is itself from software you "
                        "requested, then there might be a bug in "
                        "requested software. You can ignore this by "
                        "using 'allow-unknown-extras=true', however "
                        "that may simply cause needed software to be omitted."
                    )

                extra_requirements = sorted(
                    set(dist.extras) & set(req.extras)
                )
            else:
                extra_requirements = dist.requires(req.extras)[::-1]

            for extra_requirement in extra_requirements:
                self._requirements_and_constraints.append(
                    "Requirement of %s: %s" % (
                        current_requirement, extra_requirement))
            requirements.extend(extra_requirements)

            processed[req] = True
        return ws

    def build(self, spec, build_ext):

        requirement = self._constrain(pkg_resources.Requirement.parse(spec))

        dist, avail = self._satisfied(requirement, 1)
        if dist is not None:
            return [dist.location]

        # Retrieve the dist:
        if avail is None:
            raise zc.buildout.UserError(
                "Couldn't find a source distribution for %r."
                % str(requirement))

        if self._dest is None:
            raise zc.buildout.UserError(
                "We don't have a distribution for %s\n"
                "and can't build one in offline (no-install) mode.\n"
                % requirement
                )

        logger.debug('Building %r', spec)

        tmp = self._download_cache
        if tmp is None:
            tmp = tempfile.mkdtemp('get_dist')

        try:
            dist = self._fetch(avail, tmp, self._download_cache)

            build_tmp = tempfile.mkdtemp('build')
            try:
                setuptools.archive_util.unpack_archive(dist.location,
                                                       build_tmp)
                if os.path.exists(os.path.join(build_tmp, 'setup.py')):
                    base = build_tmp
                else:
                    setups = glob.glob(
                        os.path.join(build_tmp, '*', 'setup.py'))
                    if not setups:
                        raise distutils.errors.DistutilsError(
                            "Couldn't find a setup script in %s"
                            % os.path.basename(dist.location)
                            )
                    if len(setups) > 1:
                        raise distutils.errors.DistutilsError(
                            "Multiple setup scripts in %s"
                            % os.path.basename(dist.location)
                            )
                    base = os.path.dirname(setups[0])

                setup_cfg = os.path.join(base, 'setup.cfg')
                if not os.path.exists(setup_cfg):
                    f = open(setup_cfg, 'w')
                    f.close()
                setuptools.command.setopt.edit_config(
                    setup_cfg, dict(build_ext=build_ext))

                dists = self._call_pip_install(base, self._dest, dist)

                return [dist.location for dist in dists]
            finally:
                zc.buildout.rmtree.rmtree(build_tmp)

        finally:
            if tmp != self._download_cache:
                zc.buildout.rmtree.rmtree(tmp)

    def _fix_file_links(self, links):
        for link in links:
            if link.startswith('file://') and link[-1] != '/':
                if os.path.isdir(link[7:]):
                    # work around excessive restriction in setuptools:
                    link += '/'
            yield link

    def _log_requirement(self, ws, req):
        if (not logger.isEnabledFor(logging.DEBUG) and
            not Installer._store_required_by):
            # Sorting the working set and iterating over it's requirements
            # is expensive, so short circuit the work if it won't even be
            # logged.  When profiling a simple buildout with 10 parts with
            # identical and large working sets, this resulted in a
            # decrease of run time from 93.411 to 15.068 seconds, about a
            # 6 fold improvement.
            return

        ws = list(ws)
        ws.sort()
        for dist in ws:
            if req in dist.requires():
                logger.debug("  required by %s." % dist)
                req_ = str(req)
                if req_ not in Installer._required_by:
                    Installer._required_by[req_] = set()
                Installer._required_by[req_].add(str(dist.as_requirement()))

    def _final_version(self, parsed_version):
        return not parsed_version.is_prerelease


def normalize_versions(versions):
    """Return version dict with keys canonicalized.

    PyPI is case-insensitive and not all distributions are consistent in
    their own naming.  Also, there are dashes, underscores, dots...
    """
    return dict([(canonicalize_name(k), v) for (k, v) in versions.items()])


def default_versions(versions=None):
    old = Installer._versions
    if versions is not None:
        Installer._versions = normalize_versions(versions)
    return old

def download_cache(path=-1):
    old = Installer._download_cache
    if path != -1:
        if path:
            path = realpath(path)
        Installer._download_cache = path
    return old

def install_from_cache(setting=None):
    old = Installer._install_from_cache
    if setting is not None:
        Installer._install_from_cache = bool(setting)
    return old

def prefer_final(setting=None):
    old = Installer._prefer_final
    if setting is not None:
        Installer._prefer_final = bool(setting)
    return old

def use_dependency_links(setting=None):
    old = Installer._use_dependency_links
    if setting is not None:
        Installer._use_dependency_links = bool(setting)
    return old

def allow_picked_versions(setting=None):
    old = Installer._allow_picked_versions
    if setting is not None:
        Installer._allow_picked_versions = bool(setting)
    return old

def store_required_by(setting=None):
    old = Installer._store_required_by
    if setting is not None:
        Installer._store_required_by = bool(setting)
    return old

def get_picked_versions():
    picked_versions = sorted(Installer._picked_versions.items())
    required_by = Installer._required_by
    return (picked_versions, required_by)


def install(specs, dest,
            links=(), index=None,
            executable=sys.executable,
            always_unzip=None, # Backward compat :/
            path=None, working_set=None, newest=True, versions=None,
            use_dependency_links=None, allow_hosts=('*',),
            include_site_packages=None,
            allowed_eggs_from_site_packages=None,
            check_picked=True,
            allow_unknown_extras=False,
            ):
    assert executable == sys.executable, (executable, sys.executable)
    assert include_site_packages is None
    assert allowed_eggs_from_site_packages is None

    installer = Installer(dest, links, index, sys.executable,
                          always_unzip, path,
                          newest, versions, use_dependency_links,
                          allow_hosts=allow_hosts,
                          check_picked=check_picked,
                          allow_unknown_extras=allow_unknown_extras)
    return installer.install(specs, working_set)

buildout_and_setuptools_dists = list(install(['zc.buildout'], None,
                                             check_picked=False))
buildout_and_setuptools_path = sorted({d.location
                                for d in buildout_and_setuptools_dists})

pip_dists = [d for d in buildout_and_setuptools_dists if d.project_name != 'zc.buildout']
pip_path = sorted({d.location for d in pip_dists})
logger.debug('after restricting versions: pip_path %r', pip_path)
pip_pythonpath = os.pathsep.join(pip_path)

setuptools_path = pip_path
setuptools_pythonpath = pip_pythonpath


def build(spec, dest, build_ext,
          links=(), index=None,
          executable=sys.executable,
          path=None, newest=True, versions=None, allow_hosts=('*',)):
    assert executable == sys.executable, (executable, sys.executable)
    installer = Installer(dest, links, index, executable,
                          True, path, newest,
                          versions, allow_hosts=allow_hosts)
    return installer.build(spec, build_ext)


def _rm(*paths):
    for path in paths:
        if os.path.isdir(path):
            zc.buildout.rmtree.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)


def _create_egg_link(setup, dest, egg_name):
    """Create egg-link file.

    setuptools 80 basically removes its own 'setup.py develop' code, and
    replaces it with 'pip install -e' (which then calls setuptools again,
    but okay). See https://github.com/pypa/setuptools/pull/4955
    This leads to a different outcome.  There is no longer an .egg-link file
    that we can copy.
    So we create it ourselves, based on the previous setuptools code.

    So what should be in the .egg-link file?  Two lines: an egg path and a
    relative setup.py path.  For example with setuptools 79 we may have a
    file zc.recipe.egg.egg-link with as contents two lines:

      /Users/maurits/community/buildout/zc.recipe.egg_/src
      ../

    The relative setup.py path on the second line does not seem really used,
    but it should be there according to some checks, so let's try to get it
    right.  There is only so much we can do, but we support two common cases:
    a src-layout and a layout with the code starting at the same level as
    the setup.py file.
    """
    setup = os.path.realpath(setup)
    egg_path = os.path.dirname(setup)
    if not egg_name:
        egg_name = os.path.basename(egg_path)
    if 'src' in os.listdir(egg_path):
        egg_path = os.path.join(egg_path, 'src')
        setup_path = '..'
    else:
        setup_path = '.'
    # Return TWO lines, so NO line ending on the last line.
    contents = f"{egg_path}\n{setup_path}"
    egg_link = os.path.join(dest, egg_name) + '.egg-link'
    with open(egg_link, "w") as myfile:
        myfile.write(contents)
    return egg_link


def _copyeggs(src, dest, suffix, undo):
    """Copy eggs.

    Expected is:
    * 'src' is a temporary directory where the develop egg has been built.
    * 'dest' is the 'develop-eggs' directory
    * 'suffix' is '.egg-link'
    * 'undo' is a list of cleanup actions that will be undone automatically
      after this function returns (or throws an exception).

    The only thing we need to do: find the file with the given suffix in src,
    and move it to dest.  This works until and including setuptools 79.

    For setuptools 80+ we call _create_egg_link.
    """
    egg_links = glob.glob(os.path.join(src, "*" + suffix))
    if egg_links:
        assert len(egg_links) == 1, str(egg_links)
        egg_link = egg_links[0]
        name = os.path.basename(egg_link)
        new = os.path.join(dest, name)
        _rm(new)
        os.rename(egg_link, new)
        return new


_develop_distutils_scripts = {}


def _detect_distutils_scripts(directory):
    """Record detected distutils scripts from develop eggs

    ``setup.py develop`` doesn't generate metadata on distutils scripts, in
    contrast to ``setup.py install``. So we have to store the information for
    later.

    This won't find anything on setuptools 80.0.0+, because this does the
    editable install with pip, instead of its previous own code.  The result
    is different.  There is no egg-link file, so our code stops early.

    Maybe we could skip this check, use a different way of getting the proper
    egg_name, and still look for the 'EASY-INSTALL-DEV-SCRIPT' marker that
    setuptools adds.  But after setuptools 80.3.0 this marker is not set
    anymore: the setuptools.command.easy_install module was first removed,
    and later only partially restored.

    So if we would change the logic here, it would only be potentially useful
    for a very short range of setuptools versions.
    Also, we look for distutils scripts, which sounds like something that is
    long deprecated.
    """
    dir_contents = os.listdir(directory)
    egginfo_filenames = [filename for filename in dir_contents
                         if filename.endswith('.egg-link')]
    if not egginfo_filenames:
        return
    egg_name = egginfo_filenames[0].replace('.egg-link', '')
    marker = 'EASY-INSTALL-DEV-SCRIPT'
    scripts_found = []
    for filename in dir_contents:
        if filename.endswith('.exe'):
            continue
        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            continue
        with open(filepath) as fp:
            dev_script_content = fp.read()
        if marker in dev_script_content:
            # The distutils bin script points at the actual file we need.
            for line in dev_script_content.splitlines():
                match = DUNDER_FILE_PATTERN.search(line)
                if match:
                    # The ``__file__ =`` line in the generated script points
                    # at the actual distutils script we need.
                    actual_script_filename = match.group('filename')
                    with open(actual_script_filename) as fp:
                        actual_script_content = fp.read()
                    scripts_found.append([filename, actual_script_content])

    if scripts_found:
        logger.debug(
            "Distutils scripts found for develop egg %s: %s",
            egg_name, scripts_found)
        _develop_distutils_scripts[egg_name] = scripts_found


def develop(setup, dest,
            build_ext=None,
            executable=sys.executable):
    """Make a development/editable install of a package.

    This expects to get a path to a setup.py file (or a directory containing
    it) as the first argument.  And then it basically calls
    `python setup.py develop`.  This is a deprecated way of installing a
    package.  In setuptools 80 this still works, but setuptools has internally
    changed to call `pip install`.  So at some point we may need to do that
    ourselves.

    Also, since this expects a setup.py file, this currently does not work
    at all for a package that does not use setuptools, but for example
    hatchling.  This also may be solvable by calling `pip install`.
    """
    assert executable == sys.executable, (executable, sys.executable)
    if os.path.isdir(setup):
        directory = setup
        setup = os.path.join(directory, 'setup.py')
    else:
        directory = os.path.dirname(setup)
    logger.debug("Making editable install of %s", setup)

    undo = []
    try:
        if build_ext:
            setup_cfg = os.path.join(directory, 'setup.cfg')
            if os.path.exists(setup_cfg):
                os.rename(setup_cfg, setup_cfg+'-develop-aside')
                def restore_old_setup():
                    if os.path.exists(setup_cfg):
                        os.remove(setup_cfg)
                    os.rename(setup_cfg+'-develop-aside', setup_cfg)
                undo.append(restore_old_setup)
            else:
                f = open(setup_cfg, 'w')
                f.close()
                undo.append(lambda: os.remove(setup_cfg))
            setuptools.command.setopt.edit_config(
                setup_cfg, dict(build_ext=build_ext))

        fd, tsetup = tempfile.mkstemp()
        undo.append(lambda: os.remove(tsetup))
        undo.append(lambda: os.close(fd))

        # setuptools/distutils is showing more and more warnings.
        # And they may be very long, like this gem of 31 lines:
        # https://github.com/pypa/setuptools/blob/v79.0.1/setuptools/command/easy_install.py#L1336
        # That one shows up now that setuptools 80 forces us to no longer
        # use the --multi-version option when calling 'setup.py develop'.
        # And they may get repeated for several packages.
        # And they change the output of our doctests, causing lots of test
        # failures, making us abandon a potentially working bugfix, or causing
        # us to spend hours trying to fix or normalize test output.
        # See the current case: I want to test if removing the --multi-version
        # option works.  The new avalanche of log lines makes this impossible.
        #
        # In other words: I have *had* it with those warnings.
        #
        # So I set the root logger to simply not log at all.
        # Unfortunately, this removes error logging as well; I tried to change
        # the log level, but that somehow did not work.
        # You will still see exceptions though.
        # And: if you call buildout with '-v', our log level is DEBUG,
        # and then I don't disable the root logger.
        #
        # Note that I currently only do this in this specific place,
        # so when calling 'setup.py develop'.
        log_level = logger.getEffectiveLevel()
        extra = disable_root_logger if log_level > logging.DEBUG else ""
        os.write(fd, (runsetup_template % dict(
            setupdir=directory,
            setup=setup,
            __file__ = setup,
            extra=extra,
            )).encode())

        tmp3 = tempfile.mkdtemp('build', dir=dest)
        undo.append(lambda : zc.buildout.rmtree.rmtree(tmp3))

        # We used to pass '-m', or '--multi-version' to 'setup.py develop'.
        # The help says: "make apps have to require() a version".
        # But this option is no longer available since setuptools 80.
        # See https://github.com/buildout/buildout/pull/708
        # After some changes in our code, it seems to work without it.
        # But let's be safe and still use this flag on older setuptools.
        args = [executable,  tsetup, '-q', 'develop', '-N', '-d', tmp3]
        if not IS_SETUPTOOLS_80_PLUS:
            # Insert '-m' before '-N'.
            args.insert(args.index('-N'), '-m')
        if log_level <= logging.DEBUG:
            if log_level == logging.NOTSET:
                del args[2]
            else:
                args[2] == '-v'
            logger.debug("in: %r\n%s", directory, ' '.join(args))

        output = get_subprocess_output(args)
        if log_level <= logging.DEBUG:
            print(output)

        # This won't find anything on setuptools 80+.
        # Can't be helped, I think.
        _detect_distutils_scripts(tmp3)

        # This won't find anything on setuptools 80+.
        # But on older setuptools it still works fine.
        egg_link = _copyeggs(tmp3, dest, '.egg-link', undo)
        if egg_link:
            logger.debug("Successfully made editable install: %s", egg_link)
            return egg_link

        # The following is needed on setuptools 80+.
        # It might even work on older setuptools as fallback.
        # Search for name of package that got installed. Start from the bottom.
        # There should be a nicer way.
        egg_name = ""
        search = "Installing collected packages:"
        for line in reversed(output.splitlines()):
            if line.startswith(search):
                egg_name = line[len(search):].strip()
                if "," in egg_name or " " in egg_name:
                    logger.warning(
                        "Ignoring multiple egg names in output line: %r",
                        line,
                    )
                    egg_name = ""
                break

        egg_link = _create_egg_link(setup, dest, egg_name)
        if egg_link:
            logger.debug("Successfully made editable install: %s", egg_link)
            return egg_link
        logger.error(
            "Failure making editable install: no egg-link created for %s",
            setup,
        )

    finally:
        undo.reverse()
        [f() for f in undo]


def working_set(specs, executable, path=None,
                include_site_packages=None,
                allowed_eggs_from_site_packages=None):
    # Backward compat:
    if path is None:
        path = executable
    else:
        assert executable == sys.executable, (executable, sys.executable)
    assert include_site_packages is None
    assert allowed_eggs_from_site_packages is None

    return install(specs, None, path=path)



def scripts(reqs, working_set, executable, dest=None,
            scripts=None,
            extra_paths=(),
            arguments='',
            interpreter=None,
            initialization='',
            relative_paths=False,
            ):
    assert executable == sys.executable, (executable, sys.executable)

    path = [dist.location for dist in working_set]
    path.extend(extra_paths)
    # order preserving unique
    unique_path = []
    for p in path:
        if p not in unique_path:
            unique_path.append(p)
    path = [realpath(p) for p in unique_path]

    generated = []

    if isinstance(reqs, str):
        raise TypeError('Expected iterable of requirements or entry points,'
                        ' got string.')

    if initialization:
        initialization = '\n'+initialization+'\n'

    entry_points = []
    distutils_scripts = []
    for req in reqs:
        if isinstance(req, str):
            orig_req = pkg_resources.Requirement.parse(req)
            if orig_req.marker and not orig_req.marker.evaluate():
                continue
            dist = None
            if is_normalized_name(orig_req.name):
                dist = working_set.find(orig_req)
                if dist is None:
                    raise ValueError(
                        f"Could not find requirement '{orig_req.name}' in working set. "
                    )
            else:
                # First try finding the package by its canonical name.
                canonicalized_name = canonicalize_name(orig_req.name)
                canonical_req = pkg_resources.Requirement.parse(canonicalized_name)
                dist = working_set.find(canonical_req)
                if dist is None:
                    # Now try to find the package by the original name we got from
                    # the requirements.  This may succeed with setuptools versions
                    # older than 75.8.2.
                    dist = working_set.find(orig_req)
                    if dist is None:
                        raise ValueError(
                            f"Could not find requirement '{orig_req.name}' in working "
                            f"set. Could not find it with normalized "
                            f"'{canonicalized_name}' either."
                        )

            # regular console_scripts entry points
            for name in pkg_resources.get_entry_map(dist, 'console_scripts'):
                entry_point = dist.get_entry_info('console_scripts', name)
                entry_points.append(
                    (name, entry_point.module_name,
                     '.'.join(entry_point.attrs))
                    )
            # The metadata on "old-style" distutils scripts is not retained by
            # distutils/setuptools, except by placing the original scripts in
            # /EGG-INFO/scripts/.
            if dist.metadata_isdir('scripts'):
                # egg-info metadata from installed egg.
                for name in dist.metadata_listdir('scripts'):
                    if dist.metadata_isdir('scripts/' + name):
                        # Probably Python 3 __pycache__ directory.
                        continue
                    if name.lower().endswith('.exe'):
                        # windows: scripts are implemented with 2 files
                        #          the .exe gets also into metadata_listdir
                        #          get_metadata chokes on the binary
                        continue
                    contents = dist.get_metadata('scripts/' + name)
                    distutils_scripts.append((name, contents))
            elif dist.key in _develop_distutils_scripts:
                # Development eggs don't have metadata about scripts, so we
                # collected it ourselves in develop()/ and
                # _detect_distutils_scripts().
                for name, contents in _develop_distutils_scripts[dist.key]:
                    distutils_scripts.append((name, contents))

        else:
            entry_points.append(req)

    entry_points_names = []

    for name, module_name, attrs in entry_points:
        entry_points_names.append(name)
        if scripts is not None:
            sname = scripts.get(name)
            if sname is None:
                continue
        else:
            sname = name

        sname = os.path.join(dest, sname)
        spath, rpsetup = _relative_path_and_setup(sname, path, relative_paths)

        generated.extend(
            _script(module_name, attrs, spath, sname, arguments,
                    initialization, rpsetup)
            )

    # warn when a script name passed in 'scripts' argument
    # is not defined in an entry point.
    if scripts is not None:
        for name, target in scripts.items():
            if name not in entry_points_names:
                if name == target:
                    logger.warning("Could not generate script '%s' as it is not "
                        "defined in the egg entry points.", name)
                else:
                    logger.warning("Could not generate script '%s' as script "
                        "'%s' is not defined in the egg entry points.", name, target)

    for name, contents in distutils_scripts:
        if scripts is not None:
            sname = scripts.get(name)
            if sname is None:
                continue
        else:
            sname = name

        sname = os.path.join(dest, sname)
        spath, rpsetup = _relative_path_and_setup(sname, path, relative_paths)

        generated.extend(
            _distutils_script(spath, sname, contents, initialization, rpsetup)
            )

    if interpreter:
        sname = os.path.join(dest, interpreter)
        spath, rpsetup = _relative_path_and_setup(sname, path, relative_paths)
        generated.extend(_pyscript(spath, sname, rpsetup, initialization))

    return generated


def _relative_path_and_setup(sname, path, relative_paths):
    if relative_paths:
        relative_paths = os.path.normcase(relative_paths)
        sname = os.path.normcase(os.path.abspath(sname))
        spath = ',\n  '.join(
            [_relativitize(os.path.normcase(path_item), sname, relative_paths)
             for path_item in path]
            )
        rpsetup = relative_paths_setup
        for i in range(_relative_depth(relative_paths, sname)):
            rpsetup += "base = os.path.dirname(base)\n"
    else:
        spath = repr(path)[1:-1].replace(', ', ',\n  ')
        rpsetup = ''
    return spath, rpsetup


def _relative_depth(common, path):
    n = 0
    while 1:
        dirname = os.path.dirname(path)
        if dirname == path:
            raise AssertionError("dirname of %s is the same" % dirname)
        if dirname == common:
            break
        n += 1
        path = dirname
    return n


def _relative_path(common, path):
    r = []
    while 1:
        dirname, basename = os.path.split(path)
        r.append(basename)
        if dirname == common:
            break
        if dirname == path:
            raise AssertionError("dirname of %s is the same" % dirname)
        path = dirname
    r.reverse()
    return os.path.join(*r)


def _relativitize(path, script, relative_paths):
    if path == script:
        raise AssertionError("path == script")
    if path == relative_paths:
        return "base"
    common = os.path.dirname(os.path.commonprefix([path, script]))
    if (common == relative_paths or
        common.startswith(os.path.join(relative_paths, ''))
        ):
        return "join(base, %r)" % _relative_path(common, path)
    else:
        return repr(path)


relative_paths_setup = """
import os

join = os.path.join
base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
"""

def _script(module_name, attrs, path, dest, arguments, initialization, rsetup):
    if is_win32:
        dest += '-script.py'

    python = _safe_arg(sys.executable)

    contents = script_template % dict(
        python = python,
        path = path,
        module_name = module_name,
        attrs = attrs,
        arguments = arguments,
        initialization = initialization,
        relative_paths_setup = rsetup,
        )
    return _create_script(contents, dest)


def _distutils_script(path, dest, script_content, initialization, rsetup):
    if is_win32:
        dest += '-script.py'

    lines = script_content.splitlines(True)
    if not ('#!' in lines[0]) and ('python' in lines[0]):
        # The script doesn't follow distutil's rules.  Ignore it.
        return []
    lines = lines[1:]  # Strip off the first hashbang line.
    line_with_first_import = len(lines)
    for line_number, line in enumerate(lines):
        if not 'import' in line:
            continue
        if not (line.startswith('import') or line.startswith('from')):
            continue
        if '__future__' in line:
            continue
        line_with_first_import = line_number
        break

    before = ''.join(lines[:line_with_first_import])
    after = ''.join(lines[line_with_first_import:])

    python = _safe_arg(sys.executable)

    contents = distutils_script_template % dict(
        python = python,
        path = path,
        initialization = initialization,
        relative_paths_setup = rsetup,
        before = before,
        after = after
        )
    return _create_script(contents, dest)

def _file_changed(filename, old_contents, mode='r'):
    try:
        with open(filename, mode) as f:
            return f.read() != old_contents
    except EnvironmentError as e:
        if e.errno == errno.ENOENT:
            return True
        else:
            raise

def _create_script(contents, dest):
    generated = []
    script = dest

    changed = _file_changed(dest, contents)

    if is_win32:
        # generate exe file and give the script a magic name:
        win32_exe = os.path.splitext(dest)[0] # remove ".py"
        if win32_exe.endswith('-script'):
            win32_exe = win32_exe[:-7] # remove "-script"
        win32_exe = win32_exe + '.exe' # add ".exe"
        new_data = get_win_launcher('cli')

        if _file_changed(win32_exe, new_data, 'rb'):
            # Only write it if it's different.
            with open(win32_exe, 'wb') as f:
                f.write(new_data)
        generated.append(win32_exe)

    if changed:
        with open(dest, 'w') as f:
            f.write(contents)
        logger.info(
            "Generated script %r.",
            # Normalize for windows
            script.endswith('-script.py') and script[:-10] or script)

        try:
            os.chmod(dest, _execute_permission())
        except (AttributeError, os.error):
            pass

    generated.append(dest)
    return generated


if is_jython and jython_os_name == 'linux':
    script_header = '#!/usr/bin/env %(python)s'
else:
    script_header = '#!%(python)s'


script_template = script_header + '''\

%(relative_paths_setup)s
import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s
import %(module_name)s

if __name__ == '__main__':
    sys.exit(%(module_name)s.%(attrs)s(%(arguments)s))
'''

distutils_script_template = script_header + '''
%(before)s
%(relative_paths_setup)s
import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s

%(after)s'''


def _pyscript(path, dest, rsetup, initialization=''):
    generated = []
    script = dest
    if is_win32:
        dest += '-script.py'

    python = _safe_arg(sys.executable)
    if path:
        path += ','  # Courtesy comma at the end of the list.

    contents = py_script_template % dict(
        python = python,
        path = path,
        relative_paths_setup = rsetup,
        initialization=initialization,
        )
    changed = _file_changed(dest, contents)

    if is_win32:
        # generate exe file and give the script a magic name:
        exe = script + '.exe'
        with open(exe, 'wb') as f:
            f.write(
                pkg_resources.resource_string('setuptools', 'cli.exe')
            )
        generated.append(exe)

    if changed:
        with open(dest, 'w') as f:
            f.write(contents)
        try:
            os.chmod(dest, _execute_permission())
        except (AttributeError, os.error):
            pass
        logger.info("Generated interpreter %r.", script)

    generated.append(dest)
    return generated

py_script_template = script_header + '''\

%(relative_paths_setup)s
import sys

sys.path[0:0] = [
  %(path)s
  ]
%(initialization)s

_interactive = True
if len(sys.argv) > 1:
    # The Python interpreter wrapper allows only some of the options that a
    # "regular" Python interpreter accepts.
    _options, _args = __import__("getopt").getopt(sys.argv[1:], 'Iic:m:')
    _interactive = False
    for (_opt, _val) in _options:
        if _opt == '-i':
            _interactive = True
        elif _opt == '-c':
            exec(_val)
        elif _opt == '-m':
            sys.argv[1:] = _args
            _args = []
            __import__("runpy").run_module(
                 _val, {}, "__main__", alter_sys=True)
        elif _opt == '-I':
            # Allow yet silently ignore the `-I` option. The original behaviour
            # for this option is to create an isolated Python runtime. It was
            # deemed acceptable to allow the option here as this Python wrapper
            # is isolated from the system Python already anyway.
            # The specific use-case that led to this change is how the Python
            # language extension for Visual Studio Code calls the Python
            # interpreter when initializing the extension.
            pass

    if _args:
        sys.argv[:] = _args
        __file__ = _args[0]
        del _options, _args
        with open(__file__) as __file__f:
            exec(compile(__file__f.read(), __file__, "exec"))

if _interactive:
    del _interactive
    __import__("code").interact(banner="", local=globals())
'''

runsetup_template = """
import sys
sys.path.insert(0, %%(setupdir)r)
sys.path[0:0] = %r

import os, setuptools

%%(extra)s

__file__ = %%(__file__)r

os.chdir(%%(setupdir)r)
sys.argv[0] = %%(setup)r

with open(%%(setup)r) as f:
    exec(compile(f.read(), %%(setup)r, 'exec'))
""" % setuptools_path

disable_root_logger = """
import logging
root_logger = logging.getLogger()
handler = logging.NullHandler()
root_logger.addHandler(handler)
"""


class VersionConflict(zc.buildout.UserError):

    def __init__(self, err, ws):
        ws = list(ws)
        ws.sort()
        self.err, self.ws = err, ws

    def __str__(self):
        result = ["There is a version conflict."]
        if len(self.err.args) == 2:
            existing_dist, req = self.err.args
            result.append("We already have: %s" % existing_dist)
            for dist in self.ws:
                if req in dist.requires():
                    result.append("but %s requires %r." % (dist, str(req)))
        else:
            # The error argument is already a nice error string.
            result.append(self.err.args[0])
        return '\n'.join(result)


class MissingDistribution(zc.buildout.UserError):

    def __init__(self, req, ws):
        ws = list(ws)
        ws.sort()
        self.data = req, ws

    def __str__(self):
        req, ws = self.data
        return "Couldn't find a distribution for %r." % str(req)

def _constrained_requirement(constraint, requirement):
    assert isinstance(requirement, pkg_resources.Requirement)
    if constraint[0] not in '<>':
        if constraint.startswith('='):
            assert constraint.startswith('==')
            version = constraint[2:]
        else:
            version = constraint
            constraint = '==' + constraint
        if version not in requirement:
            msg = ("The requirement (%r) is not allowed by your [versions] "
                   "constraint (%s)" % (str(requirement), version))
            raise IncompatibleConstraintError(msg)
        specifier = specifiers.SpecifierSet(constraint)
    else:
        specifier = requirement.specifier & constraint
    constrained = copy.deepcopy(requirement)
    constrained.specifier = specifier
    return pkg_resources.Requirement.parse(str(constrained))


class IncompatibleConstraintError(zc.buildout.UserError):
    """A specified version is incompatible with a given requirement.
    """

IncompatibleVersionError = IncompatibleConstraintError # Backward compatibility


def call_pip_install(spec, dest):
    """
    Call `pip install` from a subprocess to install a
    distribution specified by `spec` into `dest`.
    Returns all the paths inside `dest` created by the above.
    """
    args = [sys.executable, '-m', 'pip', 'install', '--no-deps', '-t', dest]
    level = logger.getEffectiveLevel()
    if level >= logging.INFO:
        args.append('-q')
    else:
        args.append('-v')

    args.append(spec)

    try:
        from pip._internal.cli.cmdoptions import no_python_version_warning
        HAS_WARNING_OPTION = True
    except ImportError:
        HAS_WARNING_OPTION = False
    if HAS_WARNING_OPTION:
        if not hasattr(call_pip_install, 'displayed'):
            call_pip_install.displayed = True
        else:
            args.append('--no-python-version-warning')

    env = os.environ.copy()
    python_path = pip_path[:]
    python_path.append(env.get('PYTHONPATH', ''))
    env['PYTHONPATH'] = os.pathsep.join(python_path)

    if level <= logging.DEBUG:
        logger.debug('Running pip install:\n"%s"\npath=%s\n',
                        '" "'.join(args), pip_path)

    sys.stdout.flush() # We want any pending output first

    exit_code = subprocess.call(list(args), env=env)

    if exit_code:
        logger.error(
            "An error occurred when trying to install %s. "
            "Look above this message for any errors that "
            "were output by pip install.",
            spec)
        sys.exit(1)

    split_entries = [os.path.splitext(entry) for entry in os.listdir(dest)]
    try:
        distinfo_dir = [
            base + ext for base, ext in split_entries if ext == ".dist-info"
        ][0]
    except IndexError:
        logger.error(
            "No .dist-info directory after successful pip install of %s",
            spec)
        raise

    return make_egg_after_pip_install(dest, distinfo_dir)


def make_egg_after_pip_install(dest, distinfo_dir):
    """build properly named egg directory"""

    # `pip install` does not build the namespace aware __init__.py files
    # but they are needed in egg directories.
    # Add them before moving files setup by pip
    namespace_packages_file = os.path.join(
        dest, distinfo_dir,
        'namespace_packages.txt'
    )
    if os.path.isfile(namespace_packages_file):
        with open(namespace_packages_file) as f:
            namespace_packages = [
                line.strip().replace('.', os.path.sep)
                for line in f.readlines()
            ]

        for namespace_package in namespace_packages:
            namespace_package_dir = os.path.join(dest, namespace_package)
            if os.path.isdir(namespace_package_dir):
                init_py_file = os.path.join(
                    namespace_package_dir, '__init__.py')
                with open(init_py_file, 'w') as f:
                    f.write(
                        "__import__('pkg_resources')."
                        "declare_namespace(__name__)"
                    )

    # Remove `bin` directory if needed
    # as there is no way to avoid script installation
    # when running `pip install`
    entry_points_file = os.path.join(dest, distinfo_dir, 'entry_points.txt')
    if os.path.isfile(entry_points_file):
        with open(entry_points_file) as f:
            content = f.read()
            if "console_scripts" in content or "gui_scripts" in content:
                bin_dir = os.path.join(dest, BIN_SCRIPTS)
                if os.path.exists(bin_dir):
                    shutil.rmtree(bin_dir)

    # Get actual project name from dist-info directory.
    with open(posixpath.join(dest, distinfo_dir, "METADATA")) as fp:
        value = fp.read()
    metadata = email.parser.Parser().parsestr(value)
    project_name = metadata.get("Name")

    # Make properly named new egg dir
    distro = list(pkg_resources.find_distributions(dest))[0]
    if project_name:
        distro.project_name = project_name
    base = "{}-{}".format(
        distro.egg_name(), pkg_resources.get_supported_platform()
    )
    egg_name = base + '.egg'
    new_distinfo_dir = base + '.dist-info'
    egg_dir = os.path.join(dest, egg_name)
    os.mkdir(egg_dir)

    # Move ".dist-info" dir into new egg dir
    os.rename(
        os.path.join(dest, distinfo_dir),
        os.path.join(egg_dir, new_distinfo_dir)
    )

    top_level_file = os.path.join(egg_dir, new_distinfo_dir, 'top_level.txt')
    if os.path.isfile(top_level_file):
        with open(top_level_file) as f:
            top_levels = filter(
                (lambda x: len(x) != 0),
                [line.strip() for line in f.readlines()]
                )
    else:
        top_levels = ()

    # Move all top_level modules or packages
    for top_level in top_levels:
        # as package
        top_level_dir = os.path.join(dest, top_level)
        if os.path.exists(top_level_dir):
            shutil.move(top_level_dir, egg_dir)
            continue
        # as module
        top_level_py = top_level_dir + '.py'
        if os.path.exists(top_level_py):
            shutil.move(top_level_py, egg_dir)
            top_level_pyc = top_level_dir + '.pyc'
            if os.path.exists(top_level_pyc):
                shutil.move(top_level_pyc, egg_dir)
            continue

    record_file = os.path.join(egg_dir, new_distinfo_dir, 'RECORD')
    if os.path.isfile(record_file):
        with open(record_file, newline='') as f:
            all_files = [row[0] for row in csv.reader(f)]

    # There might be some c extensions left over
    for entry in all_files:
        if entry.endswith(('.pyc', '.pyo')):
            continue
        dest_entry = os.path.join(dest, entry)
        # work around pip install -t bug that leaves entries in RECORD
        # that starts with '../../'
        if not os.path.abspath(dest_entry).startswith(dest):
            continue
        egg_entry = os.path.join(egg_dir, entry)
        if os.path.exists(dest_entry) and not os.path.exists(egg_entry):
            egg_entry_dir = os.path.dirname(egg_entry)
            if not os.path.exists(egg_entry_dir):
                os.makedirs(egg_entry_dir)
            os.rename(dest_entry, egg_entry)

    return [egg_dir]


def unpack_egg(location, dest):
    # Buildout 2 no longer installs zipped eggs,
    # so we always want to unpack it.
    dest = os.path.join(dest, os.path.basename(location))
    setuptools.archive_util.unpack_archive(location, dest)


def unpack_wheel(location, dest):
    wheel = Wheel(location)
    # The egg_name method returns a string that includes:
    # platform = None if self.platform == 'any' else get_platform()
    # get_platform is imported from distutils.util, vendorized
    # by setuptools, but this is really just: sysconfig.get_platform()
    # This is the platform where Python got compiled.  This may differ
    # from the current platform, and this trips up the logic in
    # pkg_resources.compatible_platforms.  We have a patch for that.
    # See the docstring of the Environment class above.
    wheel.install_as_egg(os.path.join(dest, wheel.egg_name()))


UNPACKERS = {
    '.egg': unpack_egg,
    '.whl': unpack_wheel,
}


def _get_matching_dist_in_location(dist, location):
    """
    Check if `locations` contain only the one intended dist.
    Return the dist with metadata in the new location.
    """
    # Getting the dist from the environment causes the distribution
    # meta data to be read. Cloning isn't good enough. We must compare
    # dist.parsed_version, not dist.version, because one or the other
    # may be normalized (e.g., 3.3 becomes 3.3.0 when downloaded from
    # PyPI.)

    env = Environment([location])
    dists = [ d for project_name in env for d in env[project_name] ]
    dist_infos = [ (normalize_name(d.project_name), d.parsed_version) for d in dists ]
    if dist_infos == [(normalize_name(dist.project_name), dist.parsed_version)]:
        return dists.pop()


class BuildoutWheel(Wheel):
    """Extension for Wheel class to get the actual project name."""

    def get_project_name(self):
        """Get project name by looking in the .dist-info of the wheel.

        This is adapted from the Wheel.install_as_egg method and the methods
        it calls.

        Ideally, this would be the same as self.project_name.
        """
        with zipfile.ZipFile(self.filename) as zf:
            dist_info = self.get_dist_info(zf)

            with zf.open(posixpath.join(dist_info, 'METADATA')) as fp:
                value = fp.read().decode('utf-8')
                metadata = email.parser.Parser().parsestr(value)

            return metadata.get("Name")


def _maybe_copy_and_rename_wheel(dist, dest):
    """Maybe copy and rename wheel.

    Return the new dist or None.

    So why do we do this?  We need to check a special case:

    - zest_releaser-9.4.0-py3-none-any.whl with an underscore results in:
      zest_releaser-9.4.0-py3.13.egg
      In the resulting `bin/fullrease` script the zest.releaser distribution
      is not found.
    - So in this function we copy and rename the wheel to:
      zest.releaser-9.4.0-py3-none-any.whl with a dot, which results in:
      zest.releaser-9.4.0-py3.13.egg
      The resulting `bin/fullrease` script works fine.

    See https://github.com/buildout/buildout/issues/686
    So check if we should rename the wheel before handling it.

    At first, source dists seemed to not have this problem.  Or not anymore,
    after some fixes in Buildout last year:

    - zest_releaser-9.4.0.tar.gz with an underscore results in (in my case):
      zest_releaser-9.4.0-py3.13-macosx-14.7-x86_64.egg
      And this works fine, despite having an underscore.
    - But: products_cmfplone-6.1.1.tar.gz with an underscore leads to
      products_cmfplone-6.1.1-py3.13-macosx-14.7-x86_64.egg
      and with this, a Plone instance totally fails to start.
      Ah, but this is only because the generated zope.conf contains a
      temporarystorage option which is added because plone.recipe.zope2instance
      could not determine the Products.CMFPlone version.  If I work around that,
      the instance actually starts.

    The zest.releaser egg generated from the source dist has a dist-info directory:
    zest_releaser-9.4.0-py3.13-macosx-14.7-x86_64.dist-info
    The egg generated from any of the two wheels only has an EGG-INFO directory.
    I guess the dist-info directory somehow helps.
    It is there because our make_egg_after_pip_install function, which only
    gets called after installing a source dist, has its own home grown way
    of creating an egg.
    """
    wheel = BuildoutWheel(dist.location)
    actual_project_name = wheel.get_project_name()
    if actual_project_name and wheel.project_name == actual_project_name:
        return
    filename = os.path.basename(dist.location)
    new_filename = filename.replace(wheel.project_name, actual_project_name)
    if filename == new_filename:
        return
    logger.debug("Renaming wheel %s to %s", dist.location, new_filename)
    tmp_wheeldir = tempfile.mkdtemp()
    try:
        new_location = os.path.join(tmp_wheeldir, new_filename)
        shutil.copy(dist.location, new_location)
        # Now we create a clone of the original distribution,
        # but with the new location and the wanted project name.
        new_dist = Distribution(
            new_location,
            project_name=actual_project_name,
            version=dist.version,
            py_version=dist.py_version,
            platform=dist.platform,
            precedence=dist.precedence,
        )
        # We were called by _move_to_eggs_dir_and_compile.
        # Now we call it again with the new dist.
        # I tried simply returning new_dist, but then it immediately
        # got removed because we remove its temporary directory.
        return _move_to_eggs_dir_and_compile(new_dist, dest)

    finally:
        # Remember that temporary directories must be removed
        zc.buildout.rmtree.rmtree(tmp_wheeldir)


def _move_to_eggs_dir_and_compile(dist, dest):
    """Move distribution to the eggs destination directory.

    Originally we compiled the py files if we actually moved the dist.
    But this was never updated for Python 3, so it had no effect.
    So we removed this part.  See
    https://github.com/buildout/buildout/issues/699

    Its new location is expected not to exist there yet, otherwise we
    would not be calling this function: the egg is already there.  But
    the new location might exist at this point if another buildout is
    running in parallel.  So we copy to a temporary directory first.
    See discussion at https://github.com/buildout/buildout/issues/307

    We return the new distribution with properly loaded metadata.
    """
    # First make sure the destination directory exists.  This could suffer from
    # the same kind of race condition as the rest: if we check that it does not
    # exist, and we then create it, it will fail when a second buildout is
    # doing the same thing.
    try:
        os.makedirs(dest)
    except OSError:
        if not os.path.isdir(dest):
            # Unknown reason.  Reraise original error.
            raise
    logger.debug(
        "Turning dist %s (%s) into egg, and moving to eggs dir (%s).",
        dist, dist.location, dest,
    )
    tmp_dest = tempfile.mkdtemp(dir=dest)
    try:
        installed_with_pip = False
        if (os.path.isdir(dist.location) and
                dist.precedence >= pkg_resources.BINARY_DIST):
            # We got a pre-built directory. It must have been obtained locally.
            # Just copy it.
            logger.debug("dist is pre-built directory.")
            tmp_loc = os.path.join(tmp_dest, os.path.basename(dist.location))
            shutil.copytree(dist.location, tmp_loc)
        else:
            # It is an archive of some sort.
            # Figure out how to unpack it, or fall back to easy_install.
            _, ext = os.path.splitext(dist.location)
            if ext in UNPACKERS:
                if ext == '.whl':
                    logger.debug("Checking if wheel needs to be renamed.")
                    new_dist = _maybe_copy_and_rename_wheel(dist, dest)
                    if new_dist is not None:
                        logger.debug("Found dist after renaming wheel: %s", new_dist)
                        return new_dist
                    logger.debug("Renaming wheel was not needed or did not help.")
                unpacker = UNPACKERS[ext]
                logger.debug("Calling unpacker for %s on %s", ext, dist.location)
                unpacker(dist.location, tmp_dest)
                [tmp_loc] = glob.glob(os.path.join(tmp_dest, '*'))
            else:
                logger.debug("Calling pip install for %s on %s", ext, dist.location)
                [tmp_loc] = call_pip_install(dist.location, tmp_dest)
                installed_with_pip = True

        # We have installed the dist. Now try to rename/move it.
        logger.debug("Egg for %s installed at %s", dist, tmp_loc)
        newloc = os.path.join(dest, os.path.basename(tmp_loc))
        try:
            os.rename(tmp_loc, newloc)
        except OSError:
            logger.error(
                "Moving/renaming egg for %s (%s) to %s failed.",
                dist, dist.location, newloc,
            )
            # Might be for various reasons.  If it is because newloc already
            # exists, we can investigate.
            if not os.path.exists(newloc):
                # No, it is a different reason.  Give up.
                logger.error("New location %s does not exist.", newloc)
                raise
            # Try to use it as environment and check if our project is in it.
            newdist = _get_matching_dist_in_location(dist, newloc)
            if newdist is None:
                # Path exists, but is not our package.  We could
                # try something, but it seems safer to bail out
                # with the original error.
                logger.error(
                    "New location %s exists, but has no distribution for %s",
                    newloc, dist)
                raise
            # newloc looks okay to use.
            # This may happen more often on Mac, and is the reason why we
            # override Environment.can_add, see above.
            # Do print a warning.
            logger.warning(
                "Path %s unexpectedly already exists.\n"
                "It contains the expected distribution for %s.\n"
                "Maybe a buildout running in parallel has added it. "
                "We will accept it.\n"
                "If this contains a wrong package, please remove it yourself.",
                newloc, dist)
        else:
            # There were no problems during the rename.
            newdist = _get_matching_dist_in_location(dist, newloc)
            if newdist is None:
                raise AssertionError(f"{newloc} has no distribution for {dist}")
    finally:
        # Remember that temporary directories must be removed
        zc.buildout.rmtree.rmtree(tmp_dest)
    if installed_with_pip:
        newdist.precedence = pkg_resources.EGG_DIST
    return newdist


def sort_working_set(ws, eggs_dir, develop_eggs_dir):
    develop_paths = set()
    pattern = os.path.join(develop_eggs_dir, '*.egg-link')
    for egg_link in glob.glob(pattern):
        with open(egg_link, 'rt') as f:
            path = f.readline().strip()
            if path:
                develop_paths.add(path)

    sorted_paths = []
    egg_paths = []
    other_paths = []
    for dist in ws:
        path = dist.location
        if path in develop_paths:
            sorted_paths.append(path)
        elif os.path.commonprefix([path, eggs_dir]) == eggs_dir:
            egg_paths.append(path)
        else:
            other_paths.append(path)
    sorted_paths.extend(egg_paths)
    sorted_paths.extend(other_paths)
    return pkg_resources.WorkingSet(sorted_paths)


NOT_PICKED_AND_NOT_ALLOWED = """\
Picked: {name} = {version}

The `{name}` egg does not have a version pin and `allow-picked-versions = false`.

To resolve this, add

    {name} = {version}

to the [versions] section,

OR set `allow-picked-versions = true`."""
