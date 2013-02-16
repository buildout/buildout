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
It doesn't install scripts.  It uses distribute and requires it to be
installed.
"""

import distutils.errors
import glob
import logging
import os
import pkg_resources
import py_compile
import re
import setuptools.archive_util
import setuptools.command.setopt
import setuptools.package_index
import shutil
import subprocess
import sys
import tempfile
import zc.buildout

_oprp = getattr(os.path, 'realpath', lambda path: path)
def realpath(path):
    return os.path.normcase(os.path.abspath(_oprp(path)))

default_index_url = os.environ.get(
    'buildout-testing-index-url',
    'http://pypi.python.org/simple',
    )

logger = logging.getLogger('zc.buildout.easy_install')

url_match = re.compile('[a-z0-9+.-]+://').match
is_source_encoding_line = re.compile('coding[:=]\s*([-\w.]+)').search
# Source encoding regex from http://www.python.org/dev/peps/pep-0263/

is_win32 = sys.platform == 'win32'
is_jython = sys.platform.startswith('java')

if is_jython:
    import java.lang.System
    jython_os_name = (java.lang.System.getProperties()['os.name']).lower()


distribute_loc = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('distribute')
    ).location

# Include buildout and distribute eggs in paths
buildout_and_distribute_path = [
    distribute_loc,
    pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('zc.buildout')).location,
    ]

FILE_SCHEME = re.compile('file://', re.I).match


class AllowHostsPackageIndex(setuptools.package_index.PackageIndex):
    """Will allow urls that are local to the system.

    No matter what is allow_hosts.
    """
    def url_ok(self, url, fatal=False):
        if FILE_SCHEME(url):
            return True
        return setuptools.package_index.PackageIndex.url_ok(self, url, False)


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

class Installer:

    _versions = {}
    _required_by = {}
    _picked_versions = {}
    _download_cache = None
    _install_from_cache = False
    _prefer_final = True
    _use_dependency_links = True
    _allow_picked_versions = True
    _store_picked_versions = False

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
                 allow_hosts=('*',)
                 ):
        assert executable == sys.executable, (executable, sys.executable)
        self._dest = dest
        self._allow_hosts = allow_hosts

        if self._install_from_cache:
            if not self._download_cache:
                raise ValueError("install_from_cache set to true with no"
                                 " download cache")
            links = ()
            index = 'file://' + self._download_cache

        if use_dependency_links is not None:
            self._use_dependency_links = use_dependency_links
        self._links = links = list(_fix_file_links(links))
        if self._download_cache and (self._download_cache not in links):
            links.insert(0, self._download_cache)

        self._index_url = index
        path = (path and path[:] or []) + buildout_and_distribute_path
        if dest is not None and dest not in path:
            path.insert(0, dest)
        self._path = path
        if self._dest is None:
            newest = False
        self._newest = newest
        self._env = pkg_resources.Environment(path)
        self._index = _get_index(index, links, self._allow_hosts)

        if versions is not None:
            self._versions = normalize_versions(versions)

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
                      if _final_version(dist.parsed_version)
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
            if _final_version(best_available.parsed_version):
                if _final_version(best_we_have.parsed_version):
                    if (best_we_have.parsed_version
                        <
                        best_available.parsed_version
                        ):
                        return None, best_available
                else:
                    return None, best_available
            else:
                if (not _final_version(best_we_have.parsed_version)
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

    def _load_dist(self, dist):
        dists = pkg_resources.Environment(dist.location)[dist.project_name]
        assert len(dists) == 1
        return dists[0]

    def _call_easy_install(self, spec, ws, dest, dist):

        tmp = tempfile.mkdtemp(dir=dest)
        try:
            path = distribute_loc

            args = [sys.executable, '-c', _easy_install_cmd, '-mZUNxd', tmp]
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

            exit_code = subprocess.call(
                list(args),
                env=dict(os.environ, PYTHONPATH=path))

            dists = []
            env = pkg_resources.Environment([tmp])
            for project in env:
                dists.extend(env[project])

            if exit_code:
                logger.error(
                    "An error occured when trying to install %s. "
                    "Look above this message for any errors that "
                    "were output by easy_install.",
                    dist)

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
                newloc = os.path.join(dest, os.path.basename(d.location))
                if os.path.exists(newloc):
                    if os.path.isdir(newloc):
                        shutil.rmtree(newloc)
                    else:
                        os.remove(newloc)
                os.rename(d.location, newloc)

                [d] = pkg_resources.Environment([newloc])[d.project_name]

                result.append(d)

            return result

        finally:
            shutil.rmtree(tmp)

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
                      if _final_version(dist.parsed_version)
                      ]
            if fdists:
                # There are final dists, so only use those
                dists = fdists

        # Now find the best one:
        best = []
        bestv = ()
        for dist in dists:
            distv = dist.parsed_version
            if distv > bestv:
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
            return dist

        new_location = self._index.download(dist.location, tmp)
        if (download_cache
            and (realpath(new_location) == realpath(dist.location))
            and os.path.isfile(new_location)
            ):
            # distribute avoids making extra copies, but we want to copy
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
                        "Couln't download distribution %s." % avail)

                if dist.precedence == pkg_resources.EGG_DIST:
                    # It's already an egg, just fetch it into the dest

                    newloc = os.path.join(
                        self._dest, os.path.basename(dist.location))

                    if os.path.isdir(dist.location):
                        # we got a directory. It must have been
                        # obtained locally.  Just copy it.
                        shutil.copytree(dist.location, newloc)
                    else:


                        setuptools.archive_util.unpack_archive(
                            dist.location, newloc)

                    redo_pyc(newloc)

                    # Getting the dist from the environment causes the
                    # distribution meta data to be read.  Cloning isn't
                    # good enough.
                    dists = pkg_resources.Environment([newloc])[
                        dist.project_name]
                else:
                    # It's some other kind of dist.  We'll let easy_install
                    # deal with it:
                    dists = self._call_easy_install(
                        dist.location, ws, self._dest, dist)
                    for dist in dists:
                        redo_pyc(dist.location)

            finally:
                if tmp != self._download_cache:
                    shutil.rmtree(tmp)

            self._env.scan([self._dest])
            dist = self._env.best_match(requirement, ws)
            logger.info("Got %s.", dist)

        else:
            dists = [dist]

        for dist in dists:
            if (dist.has_metadata('dependency_links.txt')
                and not self._install_from_cache
                and self._use_dependency_links
                ):
                for link in dist.get_metadata_lines('dependency_links.txt'):
                    link = link.strip()
                    if link not in self._links:
                        logger.debug('Adding find link %r from %s', link, dist)
                        self._links.append(link)
                        self._index = _get_index(self._index_url, self._links,
                                                 self._allow_hosts)

        for dist in dists:
            # Check whether we picked a version and, if we did, report it:
            if not (
                dist.precedence == pkg_resources.DEVELOP_DIST
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
                        'Picked: %s = %s' % (dist.project_name, dist.version)
                        )

        return dists

    def _maybe_add_distribute(self, ws, dist):
        if dist.has_metadata('namespace_packages.txt'):
            for r in dist.requires():
                if r.project_name in ('setuptools', 'distribute'):
                    break
            else:
                # We have a namespace package but no requirement for distribute
                if dist.precedence == pkg_resources.DEVELOP_DIST:
                    logger.warn(
                        "Develop distribution: %s\n"
                        "uses namespace packages but the distribution "
                        "does not require distribute.",
                        dist)
                requirement = self._constrain(
                    pkg_resources.Requirement.parse('distribute')
                    )
                if ws.find(requirement) is None:
                    for dist in self._get_dist(requirement, ws):
                        ws.add(dist)


    def _constrain(self, requirement):
        constraint = self._versions.get(requirement.project_name.lower())
        if constraint:
            requirement = _constrained_requirement(constraint, requirement)
        return requirement

    def install(self, specs, working_set=None):

        logger.debug('Installing %s.', repr(specs)[1:-1])

        path = self._path
        dest = self._dest
        if dest is not None and dest not in path:
            path.insert(0, dest)

        requirements = [self._constrain(pkg_resources.Requirement.parse(spec))
                        for spec in specs]



        if working_set is None:
            ws = pkg_resources.WorkingSet([])
        else:
            ws = working_set

        for requirement in requirements:
            for dist in self._get_dist(requirement, ws):
                ws.add(dist)
                self._maybe_add_distribute(ws, dist)

        # OK, we have the requested distributions and they're in the working
        # set, but they may have unmet requirements.  We'll simply keep
        # trying to resolve requirements, adding missing requirements as they
        # are reported.
        #
        # Note that we don't pass in the environment, because we want
        # to look for new eggs unless what we have is the best that
        # matches the requirement.
        while 1:
            try:
                ws.resolve(requirements)
            except pkg_resources.DistributionNotFound:
                err = sys.exc_info()[1]
                [requirement] = err.args
                requirement = self._constrain(requirement)
                if dest:
                    logger.debug('Getting required %r', str(requirement))
                else:
                    logger.debug('Adding required %r', str(requirement))
                _log_requirement(ws, requirement)

                for dist in self._get_dist(requirement, ws):
                    ws.add(dist)
                    self._maybe_add_distribute(ws, dist)
            except pkg_resources.VersionConflict:
                err = sys.exc_info()[1]
                raise VersionConflict(err, ws)
            else:
                break

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

                dists = self._call_easy_install(
                    base, pkg_resources.WorkingSet(),
                    self._dest, dist)

                for dist in dists:
                    redo_pyc(dist.location)

                return [dist.location for dist in dists]
            finally:
                shutil.rmtree(build_tmp)

        finally:
            if tmp != self._download_cache:
                shutil.rmtree(tmp)


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

def store_picked_versions(setting=None):
    old = Installer._store_picked_versions
    if setting is not None:
        Installer._store_picked_versions = bool(setting)
    return old


def install(specs, dest,
            links=(), index=None,
            executable=sys.executable,
            always_unzip=None, # Backward compat :/
            path=None, working_set=None, newest=True, versions=None,
            use_dependency_links=None, allow_hosts=('*',),
            include_site_packages=None,
            allowed_eggs_from_site_packages=None,
            ):
    assert executable == sys.executable, (executable, sys.executable)
    assert include_site_packages is None
    assert allowed_eggs_from_site_packages is None

    installer = Installer(dest, links, index, sys.executable,
                          always_unzip, path,
                          newest, versions, use_dependency_links,
                          allow_hosts=allow_hosts)
    return installer.install(specs, working_set)


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
            shutil.rmtree(path)
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
                open(setup_cfg, 'w')
                undo.append(lambda: os.remove(setup_cfg))
            setuptools.command.setopt.edit_config(
                setup_cfg, dict(build_ext=build_ext))

        fd, tsetup = tempfile.mkstemp()
        undo.append(lambda: os.remove(tsetup))
        undo.append(lambda: os.close(fd))

        os.write(fd, (runsetup_template % dict(
            distribute=distribute_loc,
            setupdir=directory,
            setup=setup,
            __file__ = setup,
            )).encode())

        tmp3 = tempfile.mkdtemp('build', dir=dest)
        undo.append(lambda : shutil.rmtree(tmp3))

        args = [executable,  tsetup, '-q', 'develop', '-mxN', '-d', tmp3]

        log_level = logger.getEffectiveLevel()
        if log_level <= 0:
            if log_level == 0:
                del args[2]
            else:
                args[2] == '-v'
        if log_level < logging.DEBUG:
            logger.debug("in: %r\n%s", directory, ' '.join(args))

        call_subprocess(args)

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
                for name in dist.metadata_listdir('scripts'):
                    if dist.metadata_isdir('scripts/' + name):
                        # Probably Python 3 __pycache__ directory.
                        continue
                    contents = dist.get_metadata('scripts/' + name)
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
    source_encoding_line = ''
    original_content = ''.join(lines[1:])
    if (len(lines) > 1) and is_source_encoding_line(lines[1]):
        # The second line contains a source encoding line. Copy it verbatim.
        source_encoding_line = lines[1].rstrip()
        original_content = ''.join(lines[2:])

    python = _safe_arg(sys.executable)

    contents = distutils_script_template % dict(
        python = python,
        source_encoding_line = source_encoding_line,
        path = path,
        initialization = initialization,
        relative_paths_setup = rsetup,
        original_content = original_content
        )
    return _create_script(contents, dest)


def _create_script(contents, dest):
    generated = []
    script = dest

    changed = not (os.path.exists(dest) and open(dest).read() == contents)

    if is_win32:
        # generate exe file and give the script a magic name:
        win32_exe = os.path.splitext(dest)[0] # remove ".py"
        if win32_exe.endswith('-script'):
            win32_exe = win32_exe[:-7] # remove "-script"
        win32_exe = win32_exe + '.exe' # add ".exe"
        new_data = pkg_resources.resource_string('setuptools', 'cli.exe')
        if (not os.path.exists(win32_exe) or
            (open(win32_exe, 'rb').read() != new_data)
            ):
            # Only write it if it's different.
            open(win32_exe, 'wb').write(new_data)
        generated.append(win32_exe)

    if changed:
        open(dest, 'w').write(contents)
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

distutils_script_template = script_header + '''\

%(source_encoding_line)s
%(relative_paths_setup)s
import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s

%(original_content)s'''


def _pyscript(path, dest, rsetup, initialization=''):
    generated = []
    script = dest
    if is_win32:
        dest += '-script.py'

    python = _safe_arg(sys.executable)

    contents = py_script_template % dict(
        python = python,
        path = path,
        relative_paths_setup = rsetup,
        initialization=initialization,
        )
    changed = not (os.path.exists(dest) and open(dest).read() == contents)

    if is_win32:
        # generate exe file and give the script a magic name:
        exe = script + '.exe'
        open(exe, 'wb').write(
            pkg_resources.resource_string('setuptools', 'cli.exe')
            )
        generated.append(exe)

    if changed:
        open(dest, 'w').write(contents)
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
  %(path)s,
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
        __file__f = open(__file__)
        exec(compile(__file__f.read(), __file__, "exec"))
        __file__f.close(); del __file__f

if _interactive:
    del _interactive
    __import__("code").interact(banner="", local=globals())
'''

runsetup_template = """
import sys
sys.path.insert(0, %(setupdir)r)
sys.path.insert(0, %(distribute)r)

import os, setuptools

__file__ = %(__file__)r

os.chdir(%(setupdir)r)
sys.argv[0] = %(setup)r

exec(compile(open(%(setup)r).read(), %(setup)r, 'exec'))
"""


class VersionConflict(zc.buildout.UserError):

    def __init__(self, err, ws):
        ws = list(ws)
        ws.sort()
        self.err, self.ws = err, ws

    def __str__(self):
        existing_dist, req = self.err.args
        result = ["There is a version conflict.",
                  "We already have: %s" % existing_dist,
                  ]
        for dist in self.ws:
            if req in dist.requires():
                result.append("but %s requires %r." % (dist, str(req)))
        return '\n'.join(result)


class MissingDistribution(zc.buildout.UserError):

    def __init__(self, req, ws):
        ws = list(ws)
        ws.sort()
        self.data = req, ws

    def __str__(self):
        req, ws = self.data
        return "Couldn't find a distribution for %r." % str(req)

def _log_requirement(ws, req):
    if (not logger.isEnabledFor(logging.DEBUG) and
        not Installer._store_picked_versions):
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

def _fix_file_links(links):
    for link in links:
        if link.startswith('file://') and link[-1] != '/':
            if os.path.isdir(link[7:]):
                # work around excessive restriction in setuptools:
                link += '/'
        yield link

_final_parts = '*final-', '*final'
def _final_version(parsed_version):
    for part in parsed_version:
        if (part[:1] == '*') and (part not in _final_parts):
            return False
    return True

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
    return pkg_resources.Requirement.parse(
        "%s[%s]%s" % (
            requirement.project_name,
            ','.join(requirement.extras),
            _constrained_requirement_constraint(constraint, requirement)
            )
        )

class IncompatibleConstraintError(zc.buildout.UserError):
    """A specified version is incompatible with a given requirement.
    """

IncompatibleVersionError = IncompatibleConstraintError # Backward compatibility

def bad_constraint(constraint, requirement):
    logger.error("The constraint, %s, is not consistent with the "
                 "requirement, %r.", constraint, str(requirement))
    raise IncompatibleConstraintError("Bad constraint", constraint, requirement)

_parse_constraint = re.compile(r'([<>]=?)\s*(\S+)').match
_comparef = {
    '>' : lambda x, y: x >  y,
    '>=': lambda x, y: x >= y,
    '<' : lambda x, y: x <  y,
    '<=': lambda x, y: x <= y,
    }
_opop = {'<': '>', '>': '<'}
_opeqop = {'<': '>=', '>': '<='}
def _constrained_requirement_constraint(constraint, requirement):

    # Simple cases:

    # No specs tp merge with:
    if not requirement.specs:
        if not constraint[0] in '<=>':
            constraint = '==' + constraint
        return constraint

    # Simple single-version constraint:
    if constraint[0] not in '<>':
        if constraint.startswith('='):
            assert constraint.startswith('==')
            constraint = constraint[2:]
        if constraint in requirement:
            return '=='+constraint
        bad_constraint(constraint, requirement)


    # OK, we have a complex constraint (<. <=, >=, or >) and specs.
    # In many cases, the spec needs to filter constraints.
    # In other cases, the constraints need to limit the constraint.

    specs = requirement.specs
    cop, cv = _parse_constraint(constraint).group(1, 2)
    pcv = pkg_resources.parse_version(cv)

    # Special case, all of the specs are == specs:
    if not [op for (op, v) in specs if op != '==']:
        # There aren't any non-== specs.

        # See if any of the specs satisfy the constraint:
        specs = [op+v for (op, v) in specs
                 if _comparef[cop](pkg_resources.parse_version(v), pcv)]
        if specs:
            return ','.join(specs)

        bad_constraint(constraint, requirement)

    cop0 = cop[0]

    # Normalize specs by splitting >= and <= specs. We meed tp do this
    # becaise these have really weird semantics. Also cache parsed
    # versions, which we'll need for comparisons:
    specs = []
    for op, v in requirement.specs:
        pv = pkg_resources.parse_version(v)
        if op == _opeqop[cop0]:
            specs.append((op[0], v, pv))
            specs.append(('==', v, pv))
        else:
            specs.append((op, v, pv))

    # Error if there are opposite specs that conflict with the constraint
    # and there are no equal specs that satisfy the constraint:
    if [v for (op, v, pv) in specs
        if op == _opop[cop0] and _comparef[_opop[cop0]](pv, pcv)
        ]:
        eqspecs = [op+v for (op, v, pv) in specs
                   if _comparef[cop](pv, pcv)]
        if eqspecs:
            # OK, we do, use these:
            return ','.join(eqspecs)

        bad_constraint(constraint, requirement)

    # We have a combination of range constraints and eq specs that
    # satisfy the requirement.

    # Return the constraint + the filtered specs
    return ','.join(
        op+v
        for (op, v) in (
            [(cop, cv)] +
            [(op, v) for (op, v, pv) in specs if _comparef[cop](pv, pcv)]
            )
        )
