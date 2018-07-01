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

import distutils.errors
import errno
import glob
import logging
import os
import pkg_resources
import py_compile
import re
import setuptools.archive_util
import setuptools.command.easy_install
import setuptools.command.setopt
import setuptools.package_index
import shutil
import subprocess
import sys
import tempfile
import zc.buildout
import zc.buildout.rmtree
import warnings

try:
    from setuptools.wheel import Wheel  # This is the important import
    from setuptools import __version__ as setuptools_version
    # Now we need to check if we have at least 38.2.3 for namespace support.
    SETUPTOOLS_SUPPORTS_WHEELS = (
        pkg_resources.parse_version(setuptools_version) >=
        pkg_resources.parse_version('38.2.3'))
except ImportError:
    SETUPTOOLS_SUPPORTS_WHEELS = False

warnings.filterwarnings(
    'ignore', '.+is being parsed as a legacy, non PEP 440, version')

_oprp = getattr(os.path, 'realpath', lambda path: path)
def realpath(path):
    return os.path.normcase(os.path.abspath(_oprp(path)))

default_index_url = os.environ.get(
    'buildout-testing-index-url',
    'https://pypi.org/simple',
    )

logger = logging.getLogger('zc.buildout.easy_install')

url_match = re.compile('[a-z0-9+.-]+://').match
is_source_encoding_line = re.compile(r'coding[:=]\s*([-\w.]+)').search
# Source encoding regex from http://www.python.org/dev/peps/pep-0263/

is_win32 = sys.platform == 'win32'
is_jython = sys.platform.startswith('java')

if is_jython:
    import java.lang.System
    jython_os_name = (java.lang.System.getProperties()['os.name']).lower()

# Make sure we're not being run with an older bootstrap.py that gives us
# setuptools instead of setuptools
has_distribute = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('distribute')) is not None
has_setuptools = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('setuptools')) is not None
if has_distribute and not has_setuptools:
    sys.exit("zc.buildout 2 needs setuptools, not distribute."
             "  Are you using an outdated bootstrap.py?  Make sure"
             " you have the latest version downloaded from"
             " https://bootstrap.pypa.io/bootstrap-buildout.py")

# Include buildout and setuptools eggs in paths.  We get this
# initially from the entire working set.  Later, we'll use the install
# function to narrow to just the buildout and setuptools paths.
buildout_and_setuptools_path = [d.location for d in pkg_resources.working_set]
setuptools_path = buildout_and_setuptools_path

FILE_SCHEME = re.compile('file://', re.I).match
DUNDER_FILE_PATTERN = re.compile(r"__file__ = '(?P<filename>.+)'$")

class _Monkey(object):
    def __init__(self, module, **kw):
        mdict = self._mdict = module.__dict__
        self._before = mdict.copy()
        self._overrides = kw

    def __enter__(self):
        self._mdict.update(self._overrides)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._mdict.clear()
        self._mdict.update(self._before)

class _NoWarn(object):
    def warn(self, *args, **kw):
        pass

_no_warn = _NoWarn()

class AllowHostsPackageIndex(setuptools.package_index.PackageIndex):
    """Will allow urls that are local to the system.

    No matter what is allow_hosts.
    """
    def url_ok(self, url, fatal=False):
        if FILE_SCHEME(url):
            return True
        # distutils has its own logging, which can't be hooked / suppressed,
        # so we monkey-patch the 'log' submodule to suppress the stupid
        # "Link to <URL> ***BLOCKED*** by --allow-hosts" message.
        with _Monkey(setuptools.package_index, log=_no_warn):
            return setuptools.package_index.PackageIndex.url_ok(
                                                self, url, False)


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

def call_subprocess(args, **kw):
    if subprocess.call(args, **kw) != 0:
        raise Exception(
            "Failed to run command:\n%s"
            % repr(args)[1:-1])


def _execute_permission():
    current_umask = os.umask(0o022)
    # os.umask only returns the current umask if you also give it one, so we
    # have to give it a dummy one and immediately set it back to the real
    # value...  Distribute does the same.
    os.umask(current_umask)
    return 0o777 - current_umask


_easy_install_cmd = 'from setuptools.command.easy_install import main; main()'

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
        env = pkg_resources.Environment(full_path)
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
        extraneous information witout missing anything.

        """
        output = [
            "Version and requirements information containing %s:" % name]
        version_constraint = self._versions.get(name)
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
                str(req), best_available)
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

    def _call_easy_install(self, spec, dest, dist):

        tmp = tempfile.mkdtemp(dir=dest)
        try:
            paths = call_easy_install(spec, tmp)

            dists = []
            env = pkg_resources.Environment(paths)
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
        # requirement
        dist, avail = self._satisfied(requirement)

        if dist is None:
            if self._dest is None:
                raise zc.buildout.UserError(
                    "We don't have a distribution for %s\n"
                    "and can't install one in offline (no-install) mode.\n"
                    % requirement)

            logger.info(*__doing__)

            # Retrieve the dist:
            if avail is None:
                self._index.obtain(requirement)
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
                    raise zc.buildout.UserError(
                        'Picked: %s = %s' % (dist.project_name,
                                             dist.version)
                        )

    def _maybe_add_setuptools(self, ws, dist):
        if dist_needs_pkg_resources(dist):
            # We have a namespace package but no requirement for setuptools
            if dist.precedence == pkg_resources.DEVELOP_DIST:
                logger.warn(
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
        constraint = self._versions.get(requirement.project_name.lower())
        if constraint:
            try:
                requirement = _constrained_requirement(constraint,
                                                       requirement)
            except IncompatibleConstraintError:
                logger.info(self._version_conflict_information(
                    requirement.project_name.lower()))
                raise

        return requirement

    def install(self, specs, working_set=None):

        logger.debug('Installing %s.', repr(specs)[1:-1])
        self._requirements_and_constraints.append(
            "Base installation request: %s" % repr(specs)[1:-1])

        for_buildout_run = bool(working_set)

        requirements = [self._constrain(pkg_resources.Requirement.parse(spec))
                        for spec in specs]

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
        env = pkg_resources.Environment(ws.entries)

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

                dists = self._call_easy_install(base, self._dest, dist)

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
    """Return version dict with keys normalized to lowercase.

    PyPI is case-insensitive and not all distributions are consistent in
    their own naming.
    """
    return dict([(k.lower(), v) for (k, v) in versions.items()])


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
buildout_and_setuptools_path = [d.location
                                for d in buildout_and_setuptools_dists]
setuptools_path = [d.location
                   for d in install(['setuptools'], None, check_picked=False)]
setuptools_pythonpath = os.pathsep.join(setuptools_path)

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


def _copyeggs(src, dest, suffix, undo):
    result = []
    undo.append(lambda : _rm(*result))
    for name in os.listdir(src):
        if name.endswith(suffix):
            new = os.path.join(dest, name)
            _rm(new)
            os.rename(os.path.join(src, name), new)
            result.append(new)

    assert len(result) == 1, str(result)
    undo.pop()

    return result[0]


_develop_distutils_scripts = {}


def _detect_distutils_scripts(directory):
    """Record detected distutils scripts from develop eggs

    ``setup.py develop`` doesn't generate metadata on distutils scripts, in
    contrast to ``setup.py install``. So we have to store the information for
    later.

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
    assert executable == sys.executable, (executable, sys.executable)
    if os.path.isdir(setup):
        directory = setup
        setup = os.path.join(directory, 'setup.py')
    else:
        directory = os.path.dirname(setup)

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

        os.write(fd, (runsetup_template % dict(
            setupdir=directory,
            setup=setup,
            __file__ = setup,
            )).encode())

        tmp3 = tempfile.mkdtemp('build', dir=dest)
        undo.append(lambda : zc.buildout.rmtree.rmtree(tmp3))

        args = [executable,  tsetup, '-q', 'develop', '-mN', '-d', tmp3]

        log_level = logger.getEffectiveLevel()
        if log_level <= 0:
            if log_level == 0:
                del args[2]
            else:
                args[2] == '-v'
        if log_level < logging.DEBUG:
            logger.debug("in: %r\n%s", directory, ' '.join(args))

        call_subprocess(args)
        _detect_distutils_scripts(tmp3)
        return _copyeggs(tmp3, dest, '.egg-link', undo)

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
    path = list(map(realpath, unique_path))

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
            req = pkg_resources.Requirement.parse(req)
            dist = working_set.find(req)
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

    for name, module_name, attrs in entry_points:
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
        try:
            new_data = setuptools.command.easy_install.get_win_launcher('cli')
        except AttributeError:
            # fall back for compatibility with older Distribute versions
            new_data = pkg_resources.resource_string('setuptools', 'cli.exe')

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
    _options, _args = __import__("getopt").getopt(sys.argv[1:], 'ic:m:')
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

    if _args:
        sys.argv[:] = _args
        __file__ = _args[0]
        del _options, _args
        with open(__file__, 'U') as __file__f:
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

__file__ = %%(__file__)r

os.chdir(%%(setupdir)r)
sys.argv[0] = %%(setup)r

with open(%%(setup)r, 'U') as f:
    exec(compile(f.read(), %%(setup)r, 'exec'))
""" % setuptools_path


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

def redo_pyc(egg):
    if not os.path.isdir(egg):
        return
    for dirpath, dirnames, filenames in os.walk(egg):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            filepath = os.path.join(dirpath, filename)
            if not (os.path.exists(filepath+'c')
                    or os.path.exists(filepath+'o')):
                # If it wasn't compiled, it may not be compilable
                continue

            # OK, it looks like we should try to compile.

            # Remove old files.
            for suffix in 'co':
                if os.path.exists(filepath+suffix):
                    os.remove(filepath+suffix)

            # Compile under current optimization
            try:
                py_compile.compile(filepath)
            except py_compile.PyCompileError:
                logger.warning("Couldn't compile %s", filepath)
            else:
                # Recompile under other optimization. :)
                args = [sys.executable]
                if __debug__:
                    args.append('-O')
                args.extend(['-m', 'py_compile', filepath])

                call_subprocess(args)

def _constrained_requirement(constraint, requirement):
    if constraint[0] not in '<>':
        if constraint.startswith('='):
            assert constraint.startswith('==')
            constraint = constraint[2:]
        if constraint not in requirement:
            msg = ("The requirement (%r) is not allowed by your [versions] "
                   "constraint (%s)" % (str(requirement), constraint))
            raise IncompatibleConstraintError(msg)

        # Sigh, copied from Requirement.__str__
        extras = ','.join(requirement.extras)
        if extras:
            extras = '[%s]' % extras
        return pkg_resources.Requirement.parse(
            "%s%s==%s" % (requirement.project_name, extras, constraint))

    if requirement.specs:
        return pkg_resources.Requirement.parse(
            str(requirement) + ',' + constraint
            )
    else:
        return pkg_resources.Requirement.parse(
            str(requirement) + ' ' + constraint
            )

class IncompatibleConstraintError(zc.buildout.UserError):
    """A specified version is incompatible with a given requirement.
    """

IncompatibleVersionError = IncompatibleConstraintError # Backward compatibility


def call_easy_install(spec, dest):
    """
    Call `easy_install` from setuptools as a subprocess to install a
    distribution specified by `spec` into `dest`.
    Returns all the paths inside `dest` created by the above.
    """
    path = setuptools_path

    args = [sys.executable, '-c',
            ('import sys; sys.path[0:0] = %r; ' % path) +
            _easy_install_cmd, '-mZUNxd', dest]
    level = logger.getEffectiveLevel()
    if level > 0:
        args.append('-q')
    elif level < 0:
        args.append('-v')

    args.append(spec)

    if level <= logging.DEBUG:
        logger.debug('Running easy_install:\n"%s"\npath=%s\n',
                        '" "'.join(args), path)

    sys.stdout.flush() # We want any pending output first

    exit_code = subprocess.call(list(args))

    if exit_code:
        logger.error(
            "An error occurred when trying to install %s. "
            "Look above this message for any errors that "
            "were output by easy_install.",
            spec)
    return glob.glob(os.path.join(dest, '*'))


def unpack_egg(location, dest):
    # Buildout 2 no longer installs zipped eggs,
    # so we always want to unpack it.
    dest = os.path.join(dest, os.path.basename(location))
    setuptools.archive_util.unpack_archive(location, dest)


WHEEL_WARNING = """
*.whl file detected (%s), you'll need setuptools >= 38.2.3 for that
or an extension like buildout.wheel > 0.2.0.
"""


def unpack_wheel(location, dest):
    if SETUPTOOLS_SUPPORTS_WHEELS:
        wheel = Wheel(location)
        wheel.install_as_egg(os.path.join(dest, wheel.egg_name()))
    else:
        raise zc.buildout.UserError(WHEEL_WARNING % location)


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

    env = pkg_resources.Environment([location])
    dists = [ d for project_name in env for d in env[project_name] ]
    dist_infos = [ (d.project_name.lower(), d.parsed_version) for d in dists ]
    if dist_infos == [(dist.project_name.lower(), dist.parsed_version)]:
        return dists.pop()

def _move_to_eggs_dir_and_compile(dist, dest):
    """Move distribution to the eggs destination directory.

    And compile the py files, if we have actually moved the dist.

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
    tmp_dest = tempfile.mkdtemp(dir=dest)
    try:
        if (os.path.isdir(dist.location) and
                dist.precedence >= pkg_resources.BINARY_DIST):
            # We got a pre-built directory. It must have been obtained locally.
            # Just copy it.
            tmp_loc = os.path.join(tmp_dest, os.path.basename(dist.location))
            shutil.copytree(dist.location, tmp_loc)
        else:
            # It is an archive of some sort.
            # Figure out how to unpack it, or fall back to easy_install.
            _, ext = os.path.splitext(dist.location)
            unpacker = UNPACKERS.get(ext, call_easy_install)
            unpacker(dist.location, tmp_dest)
            [tmp_loc] = glob.glob(os.path.join(tmp_dest, '*'))

        # We have installed the dist. Now try to rename/move it.
        newloc = os.path.join(dest, os.path.basename(tmp_loc))
        try:
            os.rename(tmp_loc, newloc)
        except OSError:
            # Might be for various reasons.  If it is because newloc already
            # exists, we can investigate.
            if not os.path.exists(newloc):
                # No, it is a different reason.  Give up.
                raise
            # Try to use it as environment and check if our project is in it.
            newdist = _get_matching_dist_in_location(dist, newloc)
            if newdist is None:
                # Path exists, but is not our package.  We could
                # try something, but it seems safer to bail out
                # with the original error.
                raise
            # newloc looks okay to use.  Do print a warning.
            logger.warn(
                "Path %s unexpectedly already exists.\n"
                "Maybe a buildout running in parallel has added it. "
                "We will accept it.\n"
                "If this contains a wrong package, please remove it yourself.",
                newloc)
        else:
            # There were no problems during the rename.
            # Do the compile step.
            redo_pyc(newloc)
            newdist = _get_matching_dist_in_location(dist, newloc)
            assert newdist is not None  # newloc above is missing our dist?!
    finally:
        # Remember that temporary directories must be removed
        zc.buildout.rmtree.rmtree(tmp_dest)
    return newdist
