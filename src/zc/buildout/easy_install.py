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

# Include buildout and setuptools eggs in paths
buildout_and_setuptools_path = [
    pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('setuptools')).location,
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
        version = re.match('(\d[.]\d)[.]\d$', version).group(1)
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

def _satisfied(req, env, dest, executable, index, links):
    dists = [dist for dist in env[req.project_name] if dist in req]
    if not dists:
        logger.debug('We have no distributions for %s', req.project_name)
        return None

    # Note that dists are sorted from best to worst, as promised by
    # env.__getitem__

    for dist in dists:
        if (dist.precedence == pkg_resources.DEVELOP_DIST):
            logger.debug('We have a develop egg for %s', req)
            return dist

    # Find an upprt limit in the specs, if there is one:
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

    if dest is not None:
        best_available = _get_index(executable, index, links).obtain(req)
    else:
        best_available = None

    if best_available is None:
        # That's a bit odd.  There aren't any distros available.
        # We should use the best one we have that meets the requirement.
        logger.debug(
            'There are no distros available that meet %s. Using our best.', req)
        return best_we_have
    else:
        # Let's find out if we already have the best available:
        if best_we_have.parsed_version >= best_available.parsed_version:
            # Yup. Use it.
            logger.debug('We have the best distribution that satisfies\n%s', req)
            return best_we_have

    return None


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

def _call_easy_install(spec, env, ws, dest, links, index,
                       executable, always_unzip):

    path = _get_dist(pkg_resources.Requirement.parse('setuptools'),
                     env, ws, dest, links, index, executable, False).location
 
    args = ('-c', _easy_install_cmd, '-mUNxd', _safe_arg(dest))
    if always_unzip:
        args += ('-Z', )
    level = logger.getEffectiveLevel()
    if level > logging.DEBUG:
        args += ('-q', )
    elif level < logging.DEBUG:
        args += ('-v', )
    
    args += (spec, )

    if level <= logging.DEBUG:
        logger.debug('Running easy_install:\n%s "%s"\npath=%s\n',
                     executable, '" "'.join(args), path)

    args += (dict(os.environ, PYTHONPATH=path), )
    sys.stdout.flush() # We want any pending output first
    exit_code = os.spawnle(os.P_WAIT, executable, executable, *args)
    assert exit_code == 0


def _get_dist(requirement, env, ws,
              dest, links, index_url, executable, always_unzip):
    
    # Maybe an existing dist is already the best dist that satisfies the
    # requirement
    dist = _satisfied(requirement, env, dest, executable, index_url, links)

    if dist is None:
        if dest is not None:
            logger.info("Getting new distribution for %s", requirement)

            # Retrieve the dist:
            index = _get_index(executable, index_url, links)
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

                    if always_unzip:
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
                            dist.location,
                            os.path.join(dest, os.path.basename(dist.location)
                                         ),
                            )
                    else:
                        shutil.move(
                            dist.location,
                            os.path.join(dest, os.path.basename(dist.location)
                                         ),
                            )
                        
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
                    _call_easy_install(
                        dist.location, env, ws, dest, links, index_url,
                        executable, always_unzip)
                finally:
                    shutil.rmtree(tmp)


            # Because we have added a new egg, we need to rescan
            # the destination directory.

            # We may overwrite distributions, so clear importer
            # cache.
            sys.path_importer_cache.clear()

            env.scan([dest])
            dist = env.best_match(requirement, ws)
            logger.info("Got %s", dist)            
        else:
            dist = env.best_match(requirement, ws)

    if dist is None:
        raise ValueError("Couldn't find", requirement)

    # XXX Need test for this
    if dist.has_metadata('dependency_links.txt'):
        for link in dist.get_metadata_lines('dependency_links.txt'):
            link = link.strip()
            if link not in links:
                links.append(link)
                
    return dist
    
def install(specs, dest,
            links=(), index=None,
            executable=sys.executable, always_unzip=False,
            path=None, working_set=None):

    logger.debug('Installing %r', specs)

    path = path and path[:] or []
    if dest is not None and dest not in path:
        path.insert(0, dest)

    path += buildout_and_setuptools_path

    links = list(links) # make copy, because we may need to mutate
    

    # For each spec, see if it is already installed.  We create a working
    # set to keep track of what we've collected and to make sue than the
    # distributions assembled are consistent.
    env = pkg_resources.Environment(path, python=_get_version(executable))
    requirements = [pkg_resources.Requirement.parse(spec) for spec in specs]

    if working_set is None:
        ws = pkg_resources.WorkingSet([])
    else:
        ws = working_set

    for requirement in requirements:
        dist = _get_dist(requirement, env, ws,
                         dest, links, index, executable, always_unzip)
        ws.add(dist)
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
                    dist = _get_dist(requirement, env, ws,
                                     dest, links, index, executable,
                                     False)
                    ws.add(dist)
                    

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
            ws.add(_get_dist(requirement, env, ws,
                             dest, links, index, executable, always_unzip)
                   )
        else:
            break
            
    return ws

def build(spec, dest, build_ext,
          links=(), index=None,
          executable=sys.executable,
          path=None):

    index_url = index

    logger.debug('Building %r', spec)

    path = path and path[:] or []
    if dest is not None:
        path.insert(0, dest)

    path += buildout_and_setuptools_path

    links = list(links) # make copy, because we may need to mutate
    
    # For each spec, see if it is already installed.  We create a working
    # set to keep track of what we've collected and to make sue than the
    # distributions assembled are consistent.
    env = pkg_resources.Environment(path, python=_get_version(executable))
    requirement = pkg_resources.Requirement.parse(spec)

    dist = _satisfied(requirement, env, dest, executable, index_url, links)
    if dist is not None:
        return dist

    # Get an editable version of the package to a temporary directory:
    tmp = tempfile.mkdtemp('editable')
    tmp2 = tempfile.mkdtemp('editable')
    try:
        index = _get_index(executable, index_url, links)
        dist = index.fetch_distribution(requirement, tmp2, False, True)
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

        # Now run easy_install for real:
        _call_easy_install(base, env, pkg_resources.WorkingSet(),
                           dest, links, index_url, executable, True)
    finally:
        shutil.rmtree(tmp)
        shutil.rmtree(tmp2)

def working_set(specs, executable, path):
    return install(specs, None, executable=executable, path=path)

def scripts(reqs, working_set, executable, dest,
            scripts=None,
            extra_paths=(),
            arguments='',
            interpreter=None,
            ):
    
    path = [dist.location for dist in working_set]
    path.extend(extra_paths)
    path = repr(path)[1:-1].replace(', ', ',\n  ')
    generated = []

    if isinstance(reqs, str):
        raise TypeError('Expected iterable of requirements or entry points,'
                        ' got string.')

    entry_points = []
    for req in reqs:
        if isinstance(req, str):
            req = pkg_resources.Requirement.parse(req)
            dist = working_set.find(req)
            for name in pkg_resources.get_entry_map(dist, 'console_scripts'):
                entry_point = dist.get_entry_info('console_scripts', name)
                entry_points.append(
                    (name, entry_point.module_name, '.'.join(entry_point.attrs))
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
            _script(module_name, attrs, path, sname, executable, arguments)
            )

    if interpreter:
        sname = os.path.join(dest, interpreter)
        generated.extend(_pyscript(path, sname, executable))

    return generated

def _script(module_name, attrs, path, dest, executable, arguments):
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



