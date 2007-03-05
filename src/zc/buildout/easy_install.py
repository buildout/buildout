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
"""Python easy_install API

This module provides a high-level Python API for installing packages.
It doesn't install scripts.  It uses setuptools and requires it to be
installed.

$Id$
"""

import glob, logging, os, re, shutil, sys, tempfile, urlparse, zipimport
import distutils.errors
import pkg_resources
import setuptools.command.setopt
import setuptools.package_index
import setuptools.archive_util
import zc.buildout

default_index_url = os.environ.get('buildout-testing-index-url')

logger = logging.getLogger('zc.buildout.easy_install')

url_match = re.compile('[a-z0-9+.-]+://').match

setuptools_loc = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')
    ).location

# Include buildout and setuptools eggs in paths
buildout_and_setuptools_path = [
    setuptools_loc,
    pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('zc.buildout')).location,
    ]

_versions = {sys.executable: '%d.%d' % sys.version_info[:2]}
def _get_version(executable):
    try:
        return _versions[executable]
    except KeyError:
        i, o = os.popen4(executable + ' -V')
        i.close()
        version = o.read().strip()
        o.close()
        pystring, version = version.split()
        assert pystring == 'Python'
        version = re.match('(\d[.]\d)([.]\d)?$', version).group(1)
        _versions[executable] = version
        return version

_indexes = {}
def _get_index(executable, index_url, find_links):
    key = executable, index_url, tuple(find_links)
    index = _indexes.get(key)
    if index is not None:
        return index

    if index_url is None:
        index_url = default_index_url

    if index_url is None:
        index = setuptools.package_index.PackageIndex(
            python=_get_version(executable)
            )
    else:
        index = setuptools.package_index.PackageIndex(
            index_url, python=_get_version(executable)
            )
        
    if find_links:
        index.add_find_links(find_links)

    _indexes[key] = index
    return index

clear_index_cache = _indexes.clear

if sys.platform == 'win32':
    # work around spawn lamosity on windows
    # XXX need safe quoting (see the subproces.list2cmdline) and test
    def _safe_arg(arg):
        return '"%s"' % arg
else:
    _safe_arg = str

_easy_install_cmd = _safe_arg(
    'from setuptools.command.easy_install import main; main()'
    )

class Installer:

    def __init__(self,
                 dest=None,
                 links=(),
                 index=None,
                 executable=sys.executable,
                 always_unzip=False,
                 path=None,
                 newest=True,
                 ):
        self._dest = dest
        self._links = list(links)
        self._index_url = index
        self._executable = executable
        self._always_unzip = always_unzip
        path = (path and path[:] or []) + buildout_and_setuptools_path
        if dest is not None and dest not in path:
            path.insert(0, dest)
        self._path = path
        self._newest = newest
        self._env = pkg_resources.Environment(path,
                                              python=_get_version(executable))
        self._index = _get_index(executable, index, links)

    def _satisfied(self, req):
        dists = [dist for dist in self._env[req.project_name] if dist in req]
        if not dists:
            logger.debug('We have no distributions for %s that satisfies %s.',
                         req.project_name, req)
            return None

        # Note that dists are sorted from best to worst, as promised by
        # env.__getitem__

        for dist in dists:
            if (dist.precedence == pkg_resources.DEVELOP_DIST):
                logger.debug('We have a develop egg for %s', req)
                return dist

        if not self._newest:
            # We don't need the newest, so we'll use the newest one we
            # find, which is the first returned by
            # Environment.__getitem__.
            return dists[0]

        # Find an upper limit in the specs, if there is one:
        specs = [(pkg_resources.parse_version(v), op) for (op, v) in req.specs]
        specs.sort()
        maxv = None
        greater = False
        lastv = None
        for v, op in specs:
            if op == '==' and not greater:
                maxv = v
            elif op in ('>', '>=', '!='):
                maxv = None
                greater == True
            elif op == '<':
                maxv = None
                greater == False
            elif op == '<=':
                maxv = v
                greater == False

            if v == lastv:
                # Repeated versions values are undefined, so
                # all bets are off
                maxv = None
                greater = True
            else:
                lastv = v

        best_we_have = dists[0] # Because dists are sorted from best to worst

        # Check if we have the upper limit
        if maxv is not None and best_we_have.version == maxv:
            logger.debug('We have the best distribution that satisfies\n%s',
                         req)
            return best_we_have

        # We have some installed distros.  There might, theoretically, be
        # newer ones.  Let's find out which ones are available and see if
        # any are newer.  We only do this if we're willing to install
        # something, which is only true if dest is not None:

        
        if self._dest is not None:
            best_available = self._index.obtain(req)
        else:
            best_available = None

        if best_available is None:
            # That's a bit odd.  There aren't any distros available.
            # We should use the best one we have that meets the requirement.
            logger.debug(
                'There are no distros available that meet %s. Using our best.',
                req)
            return best_we_have
        else:
            # Let's find out if we already have the best available:
            if best_we_have.parsed_version >= best_available.parsed_version:
                # Yup. Use it.
                logger.debug(
                    'We have the best distribution that satisfies\n%s',
                    req)
                return best_we_have

        return None

    def _call_easy_install(self, spec, ws, dest):

        path = self._get_dist(pkg_resources.Requirement.parse('setuptools'),
                              ws, False).location

        args = ('-c', _easy_install_cmd, '-mUNxd', _safe_arg(dest))
        if self._always_unzip:
            args += ('-Z', )
        level = logger.getEffectiveLevel()
        if level > 0:
            args += ('-q', )
        elif level < 0:
            args += ('-v', )

        args += (spec, )

        if level <= logging.DEBUG:
            logger.debug('Running easy_install:\n%s "%s"\npath=%s\n',
                         self._executable, '" "'.join(args), path)

        args += (dict(os.environ, PYTHONPATH=path), )
        sys.stdout.flush() # We want any pending output first
        exit_code = os.spawnle(os.P_WAIT, self._executable, self._executable,
                               *args)
        assert exit_code == 0


    def _get_dist(self, requirement, ws, always_unzip):

        # Maybe an existing dist is already the best dist that satisfies the
        # requirement
        dist = self._satisfied(requirement)

        if dist is None:
            if self._dest is not None:
                logger.info("Getting new distribution for %s", requirement)

                # Retrieve the dist:
                index = self._index
                dist = index.obtain(requirement)
                if dist is None:
                    raise zc.buildout.UserError(
                        "Couldn't find a distribution for %s."
                        % requirement)

                fname = dist.location
                if url_match(fname):
                    fname = urlparse.urlparse(fname)[2]

                if fname.endswith('.egg'):
                    # It's already an egg, just fetch it into the dest
                    tmp = tempfile.mkdtemp('get_dist')
                    try:
                        dist = index.fetch_distribution(requirement, tmp)
                        if dist is None:
                            raise zc.buildout.UserError(
                                "Couln't download a distribution for %s."
                                % requirement)

                        newloc = os.path.join(
                            self._dest, os.path.basename(dist.location))

                        if os.path.isdir(dist.location):
                            # we got a directory. It must have been
                            # obtained locally.  Jut copy it.
                            shutil.copytree(dist.location, newloc)
                        else:

                            if self._always_unzip:
                                should_unzip = True
                            else:
                                metadata = pkg_resources.EggMetadata(
                                    zipimport.zipimporter(dist.location)
                                    )
                                should_unzip = (
                                    metadata.has_metadata('not-zip-safe')
                                    or not metadata.has_metadata('zip-safe')
                                    )

                            if should_unzip:
                                setuptools.archive_util.unpack_archive(
                                    dist.location, newloc)
                            else:
                                shutil.copyfile(dist.location, newloc)

                    finally:
                        shutil.rmtree(tmp)

                else:
                    # It's some other kind of dist.  We'll download it to
                    # a temporary directory and let easy_install have it's
                    # way with it:
                    tmp = tempfile.mkdtemp('get_dist')
                    try:
                        dist = index.fetch_distribution(requirement, tmp)

                        # May need a new one.  Call easy_install
                        self._call_easy_install(dist.location, ws, self._dest)
                    finally:
                        shutil.rmtree(tmp)


                # Because we have added a new egg, we need to rescan
                # the destination directory.

                # We may overwrite distributions, so clear importer
                # cache.
                sys.path_importer_cache.clear()

                self._env.scan([self._dest])
                dist = self._env.best_match(requirement, ws)
                logger.info("Got %s", dist)            
            else:
                dist = self._env.best_match(requirement, ws)

        if dist is None:
            raise ValueError("Couldn't find", requirement)

        # XXX Need test for this
        if dist.has_metadata('dependency_links.txt'):
            for link in dist.get_metadata_lines('dependency_links.txt'):
                link = link.strip()
                if link not in self._links:
                    self._links.append(link)
                    self._index = _get_index(self._executable,
                                             self._index_url, self._links)

        return dist

    def _maybe_add_setuptools(self, ws, dist):
        if dist.has_metadata('namespace_packages.txt'):
            for r in dist.requires():
                if r.project_name == 'setuptools':
                    break
            else:
                # We have a namespace package but no requirement for setuptools
                if dist.precedence == pkg_resources.DEVELOP_DIST:
                    logger.warn(
                        "Develop distribution for %s\n"
                        "uses namespace packages but the distribution "
                        "does not require setuptools.",
                        dist)
                requirement = pkg_resources.Requirement.parse('setuptools')
                if ws.find(requirement) is None:
                    dist = self._get_dist(requirement, ws, False)
                    ws.add(dist)


    def install(self, specs, working_set=None):

        logger.debug('Installing %r', specs)

        path = self._path
        dest = self._dest
        if dest is not None and dest not in path:
            path.insert(0, dest)

        requirements = [pkg_resources.Requirement.parse(spec)
                        for spec in specs]

        if working_set is None:
            ws = pkg_resources.WorkingSet([])
        else:
            ws = working_set

        for requirement in requirements:
            dist = self._get_dist(requirement, ws, self._always_unzip)
            ws.add(dist)
            self._maybe_add_setuptools(ws, dist)

        # OK, we have the requested distributions and they're in the working
        # set, but they may have unmet requirements.  We'll simply keep
        # trying to resolve requirements, adding missing requirements as they
        # are reported.
        #
        # Note that we don't pass in the environment, because we
        # want to look for new eggs unless what we have is the best that matches
        # the requirement.
        while 1:
            try:
                ws.resolve(requirements)
            except pkg_resources.DistributionNotFound, err:
                [requirement] = err
                if dest:
                    logger.debug('Getting required %s', requirement)
                dist = self._get_dist(requirement, ws, self._always_unzip)
                ws.add(dist)
                self._maybe_add_setuptools(ws, dist)
            else:
                break

        return ws

    def build(self, spec, build_ext):
        logger.debug('Building %r', spec)

        requirement = pkg_resources.Requirement.parse(spec)

        dist = self._satisfied(requirement)
        if dist is not None:
            return dist.location

        undo = []
        try:
            tmp = tempfile.mkdtemp('build')
            undo.append(lambda : shutil.rmtree(tmp)) 
            tmp2 = tempfile.mkdtemp('build')
            undo.append(lambda : shutil.rmtree(tmp2))

            dist = self._index.fetch_distribution(
                requirement, tmp2, False, True)
            if dist is None:
                raise zc.buildout.UserError(
                    "Couldn't find a source distribution for %s."
                    % requirement)
            setuptools.archive_util.unpack_archive(dist.location, tmp)

            if os.path.exists(os.path.join(tmp, 'setup.py')):
                base = tmp
            else:
                setups = glob.glob(os.path.join(tmp, '*', 'setup.py'))
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

            tmp3 = tempfile.mkdtemp('build', dir=self._dest)
            undo.append(lambda : shutil.rmtree(tmp3)) 

            self._call_easy_install(base, pkg_resources.WorkingSet(), tmp3)

            return _copyeggs(tmp3, self._dest, '.egg', undo)

        finally:
            undo.reverse()
            [f() for f in undo]


def install(specs, dest,
            links=(), index=None,
            executable=sys.executable, always_unzip=False,
            path=None, working_set=None, newest=True):
    installer = Installer(dest, links, index, executable, always_unzip, path,
                          newest)
    return installer.install(specs, working_set)


def build(spec, dest, build_ext,
          links=(), index=None,
          executable=sys.executable,
          path=None, newest=True):
    installer = Installer(dest, links, index, executable, True, path, newest)
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

        os.write(fd, runsetup_template % dict(
            setuptools=setuptools_loc,
            setupdir=directory,
            setup=setup,
            __file__ = setup,
            ))

        tmp3 = tempfile.mkdtemp('build', dir=dest)
        undo.append(lambda : shutil.rmtree(tmp3)) 

        args = [
            zc.buildout.easy_install._safe_arg(tsetup),
            '-q', 'develop', '-mxN',
            '-d', _safe_arg(tmp3),
            ]

        log_level = logger.getEffectiveLevel()
        if log_level <= 0:
            if log_level == 0:
                del args[1]
            else:
                args[1] == '-v'
        logger.debug("in: %s\n%r", directory, args)

        assert os.spawnl(os.P_WAIT, executable, executable, *args) == 0

        return _copyeggs(tmp3, dest, '.egg-link', undo)

    finally:
        undo.reverse()
        [f() for f in undo]
            
            
def working_set(specs, executable, path):
    return install(specs, None, executable=executable, path=path)

def scripts(reqs, working_set, executable, dest,
            scripts=None,
            extra_paths=(),
            arguments='',
            interpreter=None,
            initialization='',
            ):
    
    path = [dist.location for dist in working_set]
    path.extend(extra_paths)
    path = repr(path)[1:-1].replace(', ', ',\n  ')
    generated = []

    if isinstance(reqs, str):
        raise TypeError('Expected iterable of requirements or entry points,'
                        ' got string.')

    if initialization:
        initialization = '\n'+initialization+'\n'

    entry_points = []
    for req in reqs:
        if isinstance(req, str):
            req = pkg_resources.Requirement.parse(req)
            dist = working_set.find(req)
            for name in pkg_resources.get_entry_map(dist, 'console_scripts'):
                entry_point = dist.get_entry_info('console_scripts', name)
                entry_points.append(
                    (name, entry_point.module_name,
                     '.'.join(entry_point.attrs))
                    )
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
        generated.extend(
            _script(module_name, attrs, path, sname, executable, arguments,
                    initialization)
            )

    if interpreter:
        sname = os.path.join(dest, interpreter)
        generated.extend(_pyscript(path, sname, executable))

    return generated

def _script(module_name, attrs, path, dest, executable, arguments,
            initialization):
    generated = []
    if sys.platform == 'win32':
        # generate exe file and give the script a magic name:
        open(dest+'.exe', 'wb').write(
            pkg_resources.resource_string('setuptools', 'cli.exe')
            )
        generated.append(dest+'.exe')
        dest += '-script.py'
        
    open(dest, 'w').write(script_template % dict(
        python = executable,
        path = path,
        module_name = module_name,
        attrs = attrs,
        arguments = arguments,
        initialization = initialization,
        ))
    try:
        os.chmod(dest, 0755)
    except (AttributeError, os.error):
        pass
    generated.append(dest)
    return generated

script_template = '''\
#!%(python)s

import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s
import %(module_name)s

if __name__ == '__main__':
    %(module_name)s.%(attrs)s(%(arguments)s)
'''


def _pyscript(path, dest, executable):
    generated = []
    if sys.platform == 'win32':
        # generate exe file and give the script a magic name:
        open(dest+'.exe', 'wb').write(
            pkg_resources.resource_string('setuptools', 'cli.exe')
            )
        generated.append(dest+'.exe')
        dest += '-script.py'

    open(dest, 'w').write(py_script_template % dict(
        python = executable,
        path = path,
        ))
    try:
        os.chmod(dest,0755)
    except (AttributeError, os.error):
        pass
    generated.append(dest)
    return generated

py_script_template = '''\
#!%(python)s
import sys
    
sys.path[0:0] = [
  %(path)s,
  ]

_interactive = True
if len(sys.argv) > 1:
    import getopt
    _options, _args = getopt.getopt(sys.argv[1:], 'ic:')
    _interactive = False
    for (_opt, _val) in _options:
        if _opt == '-i':
            _interactive = True
        elif _opt == '-c':
            exec _val
            
    if _args:
        sys.argv[:] = _args
        execfile(sys.argv[0])

if _interactive:
    import code
    code.interact(banner="", local=globals())
'''
        
runsetup_template = """
import sys
sys.path.insert(0, %(setuptools)r)
import os, setuptools

__file__ = %(__file__)r

os.chdir(%(setupdir)r)
sys.argv[0] = %(setup)r
execfile(%(setup)r)
"""
