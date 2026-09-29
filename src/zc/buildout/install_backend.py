##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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

"""pip/uv install backend and the post-install egg reconstruction layer.

Everything here moved out of ``zc.buildout.easy_install`` unchanged; that
module re-exports these names so existing import paths keep working.  The
logger name stays the historical ``zc.buildout.easy_install`` so doctest
transcripts that assert it keep matching.  Names whose documented patch
point lives on ``zc.buildout.easy_install`` (``_run_pip``,
``_uv_executable``, ``call_pip_install``) are resolved through the facade
at call time; ``Installer`` and the settings accessors are imported lazily
for the same cycle reason.
"""

from __future__ import annotations

import csv
import email.parser
import glob
import logging
import os
import posixpath
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from collections.abc import Iterable, Sequence
from functools import lru_cache
from importlib import metadata
from pathlib import Path

import pkg_resources
import setuptools.archive_util
from packaging.utils import canonicalize_name
from pkg_resources import Distribution
from setuptools.wheel import Wheel

import zc.buildout
import zc.buildout.rmtree
from zc.buildout import uv_resolve
from zc.buildout.utils import normalize_name

logger = logging.getLogger('zc.buildout.easy_install')


def _is_url(value: str) -> bool:
    """True when ``value`` carries a real URL scheme.

    A Windows drive path such as ``C:\\index`` parses with the
    one-letter scheme ``c``. Real index schemes (http, https, file)
    are longer than one character.
    """
    return len(urllib.parse.urlsplit(value).scheme) > 1


def _extra_index_url(package_index_url: str | None) -> str | None:
    """Return the configured package index as an installer-usable URL.

    pip 25+ and uv do not accept a bare directory as index, which
    buildout does support, so a scheme-less value is converted to a
    ``file://`` URI when the directory exists and dropped otherwise.
    """
    if not package_index_url:
        return None
    if _is_url(package_index_url):
        return package_index_url
    index_path = Path(package_index_url)
    if index_path.exists():
        return index_path.expanduser().resolve().as_uri()
    return None


def _pip_install_args(spec: str, dest: str, editable: bool,
                      package_index_url: str | None,
                      log_level: int) -> list[str]:
    """Assemble the ``pip install`` argument list for ``call_pip_install``.

    ``package_index_url`` is the configured package index, normalized by
    ``_extra_index_url``. ``log_level`` selects the pip verbosity flag.
    """
    args = [sys.executable, '-m', 'pip', 'install', '--no-deps', '-t', dest]
    url = _extra_index_url(package_index_url)
    if url:
        # We could pass the index in the '--index-url' parameter.
        # But then some of our tests start failing when we pass an index
        # with only a few zc.buildout distributions.  Reason is that pip
        # will try to find setuptools there as well, as this is needed as
        # build-system for most packages.  And this fails.
        # So we pass the index as *extra* url.
        args.extend(["--extra-index-url", url])
    if log_level >= logging.INFO:
        args.append('-q')
    else:
        args.append('-v')
    if editable:
        args.append('-e')
    args.append(spec)
    return args


def _uv_sibling_executable() -> str | None:
    """A ``uv`` executable next to ``sys.executable``, when one is there.

    Pip lays the console script down as ``uv.exe`` on Windows, so the
    bare name alone misses the pip-installed binary there.
    """
    names = ['uv']
    if sys.platform == 'win32':
        names.append('uv.exe')
    for name in names:
        candidate = os.path.join(os.path.dirname(sys.executable), name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


@lru_cache(maxsize=None)
def _uv_version(uv: str) -> str:
    """The ``uv --version`` output for ``uv``, for debug logging."""
    try:
        return subprocess.check_output(
            [uv, '--version'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'uv (unknown version)'


def _uv_executable() -> str:
    """Resolve the ``uv`` binary, on PATH or next to ``sys.executable``."""
    uv = shutil.which('uv') or _uv_sibling_executable()
    if uv is None:
        raise zc.buildout.UserError(
            "The 'installer' option is set to 'uv', but no 'uv' executable"
            " was found on PATH or next to the Python executable"
            f" ({sys.executable}).")
    logger.debug('Using %s (%s)', _uv_version(uv), uv)
    return uv


def _uv_install_args(uv: str, spec: str, dest: str, editable: bool,
                     package_index_url: str | None,
                     log_level: int) -> list[str]:
    """Assemble the ``uv pip install`` argument list for ``call_pip_install``.

    Mirrors ``_pip_install_args`` (same verbosity selection and index
    handling), but uv is a standalone binary: it installs for the
    interpreter named by ``--python`` and has no pip-style
    ``--no-python-version-warning`` flag to add.
    """
    args = [uv, 'pip', 'install', '--no-deps', '-t', dest,
            '--python', sys.executable]
    if log_level >= logging.INFO:
        args.append('-q')
    else:
        args.append('-v')
    url = _extra_index_url(package_index_url)
    if url:
        # Passed as *extra* url for the same reason as in
        # _pip_install_args.
        args.extend(['--extra-index-url', url])
    if editable:
        args.append('-e')
    args.append(spec)
    return args


def _pip_install_env() -> dict[str, str]:
    """Subprocess environment for ``python -m pip``.

    ``pip_path`` goes on PYTHONPATH so the subprocess can import pip.
    """
    from zc.buildout.easy_install import pip_path

    env = os.environ.copy()
    python_path = pip_path[:]
    python_path.append(env.get('PYTHONPATH', ''))
    env['PYTHONPATH'] = os.pathsep.join(python_path)
    return env


def _run_pip(args: list[str], env: dict[str, str], dest: str, level: int) -> str:
    from zc.buildout.easy_install import get_subprocess_output
    """Run ``pip install`` and return its output, with debug logging."""
    if level <= logging.DEBUG:
        logger.debug('Running pip install:\n"%s"\nPYTHONPATH=%s\n',
                        '" "'.join(args), env.get('PYTHONPATH', ''))

    sys.stdout.flush() # We want any pending output first

    # This will quit the buildout process if there is an error.
    output = get_subprocess_output(list(args), env=env)
    if level <= logging.DEBUG:
        if output:
            logger.debug(output)
        logger.debug("Pip install completed successfully.")
        logger.debug("Contents of %s:", dest)
        for entry in os.listdir(dest):
            logger.debug("- %s", entry)
    return output


def _scan_editable_install(
        split_entries: list[tuple[str, str]]) -> tuple[str, str | None]:
    """Scan pip install output entries for egg-link / nspkg.pth markers.

    ``split_entries`` holds ``os.path.splitext`` results for the files pip
    created.  Return ``(package_name, namespaces)``: ``package_name`` is the
    base name of the ``.egg-link`` file ('' when there is none), and
    ``namespaces`` the guessed old-style namespace list (None unless a
    ``-nspkg.pth`` file accompanies the egg-link).
    """
    package_name = ""
    for base, ext in split_entries:
        if ext == ".egg-link":
            package_name = base
            break
    if not package_name:
        return "", None
    # For pkg_resources style namespaces a .pth file is created,
    # for example `plone.app.something-nspkg.pth`.
    for base, ext in split_entries:
        if ext != ".pth" or not base.endswith("-nspkg"):
            continue
        # We don't want to analyze this file, so we can only make an
        # educated guess about the namespaces.
        # Assume at most two dots, that is enough info for our warning.
        # `a.b` -> `a`
        # `a.b.c` -> `a\na.b`
        # `a.b.c.d` -> `a\na.b`
        # Get all names except the last one, and then keep the first two:
        names = package_name.split(".")[:-1][:2]
        if len(names) > 1:
            names[1] = ".".join(names)
        return package_name, "\n".join(names)
    return package_name, None


def _dist_info_dirname(split_entries: list[tuple[str, str]]) -> str:
    """Return the ``.dist-info`` directory name among pip's output entries."""
    # IndexError on no match is the tested contract
    # (test_dist_info_dirname_raises_without_match):
    return [  # noqa: RUF015
        base + ext for base, ext in split_entries if ext == ".dist-info"
    ][0]


def _installed_dist_name(full_distinfo_dir: str) -> str | None:
    """Read the package name from an installed ``.dist-info`` directory."""
    distrib = metadata.Distribution.at(full_distinfo_dir)
    # On Python 3.10 we could use `distrib.name`.
    return distrib.metadata['Name']


def _maybe_add_no_python_version_warning(args: list[str]) -> None:
    """Append pip's ``--no-python-version-warning`` flag when pip
    supports it.

    Quirk preserved: the flag is only appended from the second call
    on; the first call just records a one-shot ``displayed`` attribute
    on ``call_pip_install``.
    """
    from zc.buildout.easy_install import call_pip_install

    try:
        from pip._internal.cli.cmdoptions import no_python_version_warning
        HAS_WARNING_OPTION = True
    except ImportError:
        HAS_WARNING_OPTION = False
    if HAS_WARNING_OPTION:
        if not hasattr(call_pip_install, 'displayed'):
            # One-shot flag stored as a function attribute; dynamic attribute
            # creation is invisible to static analysis.
            call_pip_install.displayed = True  # ty: ignore[unresolved-attribute]
        else:
            args.append('--no-python-version-warning')


def _editable_scan_result(
        split_entries: list[tuple[str, str]], spec: str) -> str | None:
    """Handle an editable install's egg-link / -nspkg.pth scan results.

    Return the package name when an egg-link file was created
    (setuptools 79 and earlier); when a -nspkg.pth file accompanies
    it, register the guessed old-style namespaces and warn.
    """
    from zc.buildout.easy_install import Installer

    # On setuptools 79 and earlier, the egg-link file is created.
    package_name, namespaces = _scan_editable_install(split_entries)
    if package_name:
        logger.debug(
            "Found .egg-link file after successful pip install of %s",
            spec,
        )
    if namespaces is not None:
        # We only need this if the name was found.  If name was not
        # found, the namespaces will be checked in a different way
        # further on.
        logger.debug(
            "Found -nspkg.pth file after successful pip install of %s",
            spec,
        )
        logger.warning(
            "WARNING: Package %s at %s is using old style namespace packages. "
            "You should switch to native namespaces (PEP 420).",
            package_name,
            spec,
        )
        Installer._namespace_packages[package_name] = namespaces
    if package_name:
        return package_name
    return None


def call_pip_install(spec: str, dest: str, editable: bool=False) -> str | list[str]:
    """
    Call `pip install` from a subprocess to install a
    distribution specified by `spec` into `dest`.

    When the `installer` option is 'uv', the subprocess is a
    `uv pip install` invocation instead of `python -m pip`.

    For normal (non-editable) installs, returns all the paths inside `dest`
    created by the above.  For editable installs, it returns the package name.
    These very different return values may seem strange, but it is because
    what needs to happen afterwards is very different for the two cases.
    """
    from zc.buildout import easy_install
    from zc.buildout.easy_install import Installer, index_url, installer

    level = logger.getEffectiveLevel()
    if installer() == 'uv':
        args = _uv_install_args(
            easy_install._uv_executable(), spec, dest, editable, index_url(), level)
        env = os.environ.copy()
    else:
        args = _pip_install_args(spec, dest, editable, index_url(), level)

        _maybe_add_no_python_version_warning(args)

        env = _pip_install_env()

    easy_install._run_pip(args, env, dest, level)

    split_entries = [os.path.splitext(entry) for entry in os.listdir(dest)]
    if editable:
        package_name = _editable_scan_result(split_entries, spec)
        if package_name:
            return package_name

    # With normal (non-editable) installs, there won't be an egg-link file created.
    # The same is true for editable installs with setuptools 80+.
    # In both cases, we need to look for the .dist-info directory.
    try:
        distinfo_dir = _dist_info_dirname(split_entries)
    except IndexError:
        logger.error(
            "No .dist-info directory after successful pip install of %s",
            spec)
        raise

    full_distinfo_dir = os.path.join(dest, distinfo_dir)
    name = _installed_dist_name(full_distinfo_dir)
    if not name:
        logger.error(
            "Could not find package name in metadata after installing %s.",
            spec,
        )
        sys.exit(1)
    if editable:
        namespaces_file = os.path.join(full_distinfo_dir, "namespace_packages.txt")
        if os.path.exists(namespaces_file):
            logger.warning(
                "WARNING: Package %s at %s is using old style namespace packages. "
                "You should switch to native namespaces (PEP 420).",
                name,
                spec,
            )
            with open(namespaces_file) as myfile:
                Installer._namespace_packages[name] = myfile.read()

    if not editable:
        # TODO: we should no longer make an egg, but we still need some of this.
        return make_egg_after_pip_install(dest, distinfo_dir)
    return name


def _namespace_candidate_lines(ns_file: str | Path) -> list[str]:
    """Return the non-empty, non-comment lines of ``ns_file``."""
    with open(ns_file, 'r') as myfile:
        return [line for line in myfile if line.strip() and not line.strip().startswith('#')]


def _lines_declare_namespace(contents: list[str]) -> bool:
    """Whether ``contents`` hold a pkg_resources or pkgutil namespace."""
    for combo in [
        ("pkg_resources", "declare_namespace"),
        ("pkgutil", "extend_path"),
    ]:
        found_first = False
        for line in contents:
            if combo[0] in line:
                found_first = True
            if found_first and combo[1] in line:
                return True
    return False


def check_namespace_init_file(ns_file: str | Path) -> bool:
    """Look for namespace declaration in file.

    This can be spelled in different ways.  It can be a one-liner:

    __import__('pkg_resources').declare_namespace(__name__)

    Or it can be a multi-line declaration, including comments, like this:

    # See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
    try:
        __import__("pkg_resources").declare_namespace(__name__)
    except ImportError:
        from pkgutil import extend_path

        __path__ = extend_path(__path__, __name__)
    """
    logger.debug("Checking namespace __init__.py file: %s", ns_file)
    contents = _namespace_candidate_lines(ns_file)
    if len(contents) == 0:
        logger.debug("Found too few lines to be a namespace declaration.")
        return False
    if len(contents) > 6:
        logger.debug("Found too many lines to be a namespace declaration.")
        return False
    # Debug log and return stay here so the log sequence is unchanged.
    if _lines_declare_namespace(contents):
        logger.debug("Found namespace declaration in %s", ns_file)
        return True
    logger.debug("No namespace declaration found in %s", ns_file)
    return False


def find_namespace_init_files(directory: str | Path) -> list[str]:
    logger.debug("Searching for namespace __init__.py files in %s", directory)
    found_files = []
    for root, dirs, files in os.walk(directory):
        if root.endswith('__pycache__'):
            continue
        if len(files) != 1 or '__init__.py' not in files:
            continue
        ns_file = os.path.join(root, '__init__.py')
        logger.debug('Found possible namespace __init__.py file: %s', ns_file)
        if check_namespace_init_file(ns_file):
            found_files.append(ns_file)
    if found_files:
        logger.debug("Found namespace __init__.py files: %s", found_files)
    else:
        logger.debug("No namespace __init__.py files found.")
    return found_files


def _remove_namespace_init_files(dest: str) -> None:
    # Resolve through the facade at call time: the patch point for
    # find_namespace_init_files lives on zc.buildout.easy_install.
    from zc.buildout import easy_install

    # `pip install` does not build the namespace aware __init__.py files.
    # In the new situation we are happy with that.  But actually, for some
    # packages, pip *does* include these files, so we need to remove them.
    # For example try `pip install zope.interface==4.1.3`.  You get a warning:
    # "DEPRECATION: zope.interface is being installed using the legacy
    # 'setup.py install' method, because it does not have a 'pyproject.toml'""
    # Apparently this has the side effect that the namespace files get installed.
    # zope.interface 7.0.3 does not have this problem.
    for ns_file in easy_install.find_namespace_init_files(dest):
        os.remove(ns_file)
        logger.debug("Removed namespace __init__.py file: %s", ns_file)


def _remove_pip_bin_dir(dest: str, distinfo_dir: str) -> None:
    from zc.buildout.easy_install import BIN_SCRIPTS

    # Remove `bin` directory if needed
    # as there is no way to avoid script installation
    # when running `pip install`
    entry_points_file = os.path.join(dest, distinfo_dir, 'entry_points.txt')
    if os.path.isfile(entry_points_file):
        with open(entry_points_file, encoding='utf-8', errors="replace") as f:
            content = f.read()
            if "console_scripts" in content or "gui_scripts" in content:
                bin_dir = os.path.join(dest, BIN_SCRIPTS)
                if os.path.exists(bin_dir):
                    shutil.rmtree(bin_dir)


def _read_project_name(dest: str, distinfo_dir: str) -> str | None:
    # Get actual project name from dist-info directory.
    metadata_path = posixpath.join(dest, distinfo_dir, "METADATA")
    # The encoding and errors arguments can be needed on Windows.
    # See https://github.com/buildout/buildout/issues/722
    with open(metadata_path, encoding='utf-8', errors="replace") as fp:
        value = fp.read()
    metadata = email.parser.Parser().parsestr(value)
    return metadata.get("Name")


def _read_top_levels(
        egg_dir: str,
        new_distinfo_dir: str,
        ) -> Iterable[str]:
    top_level_file = os.path.join(egg_dir, new_distinfo_dir, 'top_level.txt')
    if os.path.isfile(top_level_file):
        with open(top_level_file, encoding='utf-8', errors="replace") as f:
            top_levels: Iterable[str] = filter(
                (lambda x: len(x) != 0),
                [line.strip() for line in f]
                )
    else:
        top_levels = ()
    return top_levels


def _move_top_levels(
        dest: str,
        egg_dir: str,
        top_levels: Iterable[str],
        ) -> None:
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


def _read_record_entries(record_file: str) -> list[str]:
    with open(record_file, newline='', encoding='utf-8', errors="replace") as f:
        return [row[0] for row in csv.reader(f)]


def _read_record_or_raise(
        record_file: str,
        batched: bool,
        project_name: str,
        distinfo_dir: str,
        ) -> list[str]:
    """Read the freshly installed dist's RECORD entries.

    A batched install shares its destination between distributions, so
    without RECORD there is no safe way to pick this dist's own files;
    that must fail loudly instead of producing a metadata-only egg.
    """
    if os.path.isfile(record_file):
        return _read_record_entries(record_file)
    if batched:
        raise zc.buildout.UserError(
            f"Cannot reconstruct an egg for {project_name}:"
            f" no RECORD file in {distinfo_dir} after installation.")
    return []


def _move_record_leftovers(
        dest: str,
        egg_dir: str,
        all_files: Iterable[str],
        ) -> None:
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


def make_egg_after_pip_install(
        dest: str,
        distinfo_dir: str,
        distro: pkg_resources.Distribution | None = None,
        ) -> list[str]:
    """build properly named egg directory

    ``distro`` is the distribution the egg is named after.  When it is
    omitted, the first distribution found in ``dest`` is picked — the
    historical behavior, unambiguous as long as ``dest`` holds a single
    install.  Callers that installed several distributions into ``dest``
    with one subprocess pass the one matching ``distinfo_dir``; the egg
    is then reconstructed file-precise from the dist's RECORD entries,
    because the shared ``dest`` makes whole-directory moves ambiguous;
    a batched dist without RECORD is reported as a user error.
    """
    logger.debug('Making egg in %s from pip installation in %s', dest, distinfo_dir)

    _remove_namespace_init_files(dest)

    _remove_pip_bin_dir(dest, distinfo_dir)

    project_name = _read_project_name(dest, distinfo_dir)

    # Make properly named new egg dir
    batched = distro is not None
    if distro is None:
        distro = next(iter(pkg_resources.find_distributions(dest)))
    if project_name:
        distro.project_name = project_name
    base = f"{distro.egg_name()}-{pkg_resources.get_supported_platform()}"
    egg_name = base + '.egg'
    new_distinfo_dir = base + '.dist-info'
    egg_dir = os.path.join(dest, egg_name)
    os.mkdir(egg_dir)

    # Move ".dist-info" dir into new egg dir
    os.rename(
        os.path.join(dest, distinfo_dir),
        os.path.join(egg_dir, new_distinfo_dir)
    )

    record_file = os.path.join(egg_dir, new_distinfo_dir, 'RECORD')
    all_files = _read_record_or_raise(
        record_file, batched, distro.project_name, distinfo_dir)

    if not batched:
        # ``dest`` holds this single install, so moving the whole
        # top-level modules and packages named by top_level.txt is
        # unambiguous.  Batched callers share ``dest`` between
        # distributions, where grabbing a whole top-level directory
        # would move a sibling's files into this egg; only this dist's
        # RECORD entries belong in it.
        top_levels = _read_top_levels(egg_dir, new_distinfo_dir)
        _move_top_levels(dest, egg_dir, top_levels)

    _move_record_leftovers(dest, egg_dir, all_files)

    return [egg_dir]


def unpack_egg(location: str, dest: str) -> None:
    # Buildout 2 no longer installs zipped eggs,
    # so we always want to unpack it.
    # XXX The next line seems double now.
    # dest = os.path.join(dest, os.path.basename(location))
    setuptools.archive_util.unpack_archive(location, dest)


def unpack_wheel(location: str, dest: str) -> None:
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
    # '.whl': setuptools.archive_util.unpack_zipfile,
}


def _get_matching_dist_in_location(dist: pkg_resources.DistInfoDistribution | pkg_resources.Distribution, location: str) -> pkg_resources.Distribution | pkg_resources.DistInfoDistribution | None:
    """
    Check if `locations` contain only the one intended dist.
    Return the dist with metadata in the new location.
    """
    from zc.buildout.easy_install import Environment

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

    # setuptools.wheel.Wheel.__init__ sets this dynamically via setattr
    # from the wheel filename, which is invisible to static analysis.
    project_name: str

    def get_project_name(self) -> str | None:
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


def _maybe_copy_and_rename_wheel(dist: pkg_resources.DistInfoDistribution | pkg_resources.Distribution, dest: str) -> pkg_resources.Distribution | pkg_resources.DistInfoDistribution | None:
    from zc.buildout.easy_install import _dist_location
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
    # The dists handled in this module are installed or downloadable dists,
    # which always live on disk and thus have a location (see _dist_location).
    location = _dist_location(dist)
    wheel = BuildoutWheel(location)
    actual_project_name = wheel.get_project_name()
    if actual_project_name and wheel.project_name == actual_project_name:
        return
    # A valid wheel always has a Name in its METADATA, so at this point we
    # know the actual project name (otherwise there is nothing to rename to).
    assert actual_project_name is not None
    filename = os.path.basename(location)
    new_filename = filename.replace(wheel.project_name, actual_project_name)
    if filename == new_filename:
        return
    logger.debug("Renaming wheel %s to %s", location, new_filename)
    tmp_wheeldir = tempfile.mkdtemp()
    try:
        new_location = os.path.join(tmp_wheeldir, new_filename)
        shutil.copy(location, new_location)
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


def _ensure_dest_dir(dest: str) -> None:
    """Make sure the destination directory exists.

    This could suffer from a race condition: if we check that it does
    not exist, and we then create it, it will fail when a second
    buildout is doing the same thing.  So we create it unconditionally
    and only propagate the error when the directory is still missing.
    """
    try:
        os.makedirs(dest)
    except OSError:
        if not os.path.isdir(dest):
            # Unknown reason.  Reraise original error.
            raise


def _unpack_dist_to_tmp(dist: pkg_resources.DistInfoDistribution | pkg_resources.Distribution, tmp_dest: str) -> str:
    from zc.buildout import easy_install
    from zc.buildout.easy_install import _dist_location
    """Copy or unpack ``dist`` into ``tmp_dest``; return its location there.

    A pre-built directory is copied as-is.  An archive is unpacked with
    the registered unpacker for its extension, or installed by pip.
    """
    if (os.path.isdir(_dist_location(dist)) and
            dist.precedence >= pkg_resources.BINARY_DIST):
        # We got a pre-built directory. It must have been obtained locally.
        # Just copy it.
        logger.debug("dist is pre-built directory.")
        # TODO Can we still support this?  Do we need to?  Maybe warn, or let pip install this.
        tmp_loc = os.path.join(tmp_dest, os.path.basename(_dist_location(dist)))
        shutil.copytree(_dist_location(dist), tmp_loc)
    else:
        # It is an archive of some sort.
        # Figure out how to unpack it, or fall back to easy_install.
        basename, ext = os.path.splitext(_dist_location(dist))
        if ext == ".gz" and basename.endswith(".tar"):
            basename = basename[:-4]
        # Set new location with name ending in '.experimental'.
        # XXX TODO some our code or tests expects '.egg' at the end.
        # tmp_loc = os.path.join(tmp_dest, os.path.basename(basename) + ".experimental")
        tmp_loc = os.path.join(tmp_dest, os.path.basename(basename) + ".egg")
        if ext in UNPACKERS:
            # TODO Maybe simply always call pip install for all dists, without
            # checking for unpackers.
            # TODO Maybe never rename a wheel or other dist anymore.
            # if ext == '.whl':
            #     logger.debug("Checking if wheel needs to be renamed.")
            #     new_dist = _maybe_copy_and_rename_wheel(dist, dest)
            #     if new_dist is not None:
            #         logger.debug("Found dist after renaming wheel: %s", new_dist)
            #         return new_dist
            #     logger.debug("Renaming wheel was not needed or did not help.")
            unpacker = UNPACKERS[ext]
            logger.debug("Calling unpacker for %s on %s", ext, dist.location)
            unpacker(_dist_location(dist), tmp_loc)
        else:
            logger.debug("Calling pip install for %s on %s", ext, dist.location)
            [tmp_loc] = easy_install.call_pip_install(_dist_location(dist), tmp_dest)
    return tmp_loc


def _move_dist_into_place(dist: pkg_resources.DistInfoDistribution | pkg_resources.Distribution, tmp_loc: str, dest: str) -> pkg_resources.Distribution | pkg_resources.DistInfoDistribution:
    from zc.buildout import easy_install
    """Rename the unpacked dist into ``dest``; return the new dist.

    The rename can lose a race against a buildout running in parallel:
    when the new location already exists and contains the distribution,
    accept it with a warning.
    """
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
        newdist = easy_install._get_matching_dist_in_location(dist, newloc)
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
        newdist = easy_install._get_matching_dist_in_location(dist, newloc)
        if newdist is None:
            raise AssertionError(f"{newloc} has no distribution for {dist}")
    return newdist


def _move_to_eggs_dir_and_compile(dist: pkg_resources.DistInfoDistribution | pkg_resources.Distribution, dest: str) -> pkg_resources.Distribution | pkg_resources.DistInfoDistribution:
    from zc.buildout import easy_install
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
    _ensure_dest_dir(dest)
    logger.debug(
        "Turning dist %s (%s) into egg, and moving to eggs dir (%s).",
        dist, dist.location, dest,
    )
    tmp_dest = tempfile.mkdtemp(dir=dest)
    try:
        tmp_loc = _unpack_dist_to_tmp(dist, tmp_dest)

        # We have installed the dist. Now try to rename/move it.
        logger.debug("Egg for %s installed at %s", dist, tmp_loc)
        newdist = _move_dist_into_place(dist, tmp_loc, dest)
        # The new dist automatically has precedence DEVELOP_DIST, which sounds
        # wrong.  And this interferes with a check for printing picked versions.
        # So set it to EGG_DIST.  We already did this for a long time, then I
        # removed it because I thought it would no longer be needed, but it is.
        # Also, we used to do this only when the dist was installed by pip,
        # but it seems needed always, otherwise dists installed from eggs won't
        # be reported in picked versions either.  It could be that we report
        # too much then, but we will see.
        newdist.precedence = pkg_resources.EGG_DIST
    finally:
        # Remember that temporary directories must be removed
        zc.buildout.rmtree.rmtree(tmp_dest)
    return newdist


def _dist_for_pin(dest: str, pin: uv_resolve.PinnedDist
                  ) -> pkg_resources.Distribution | None:
    """The distribution installed in ``dest`` that ``pin`` names.

    ``pkg_resources.find_distributions`` follows ``os.listdir`` order,
    so picking its first hit is ambiguous once a batched install leaves
    several ``.dist-info`` dirs in one directory; match the pin's
    canonicalized name and parsed version instead.
    """
    wanted = canonicalize_name(pin.name)
    version = pkg_resources.parse_version(pin.version)
    for distro in pkg_resources.find_distributions(dest):
        if (canonicalize_name(distro.project_name) == wanted
                and distro.parsed_version == version):
            return distro
    return None


def install_pinned_dists(pinned: Sequence[uv_resolve.PinnedDist],
                         dest: str) -> list[pkg_resources.Distribution]:
    """Install a pinned set into ``dest`` with one uv subprocess.

    Batched counterpart of ``_move_to_eggs_dir_and_compile`` for uv
    full-resolution mode: ``uv pip install`` accepts N positional
    specs, so the whole set lands in one shared temporary directory and
    each distribution is then turned into an egg and moved into place.
    Returns the new dists in pin order.
    """
    if not pinned:
        # No pinned distributions, no subprocess.
        return []
    from zc.buildout import easy_install
    from zc.buildout.easy_install import index_url

    level = logger.getEffectiveLevel()
    # Same parallel-buildout race contract as
    # _move_to_eggs_dir_and_compile: the egg's final location may appear
    # while we work, so install into a temporary sibling inside ``dest``
    # first and move the eggs over afterwards.
    _ensure_dest_dir(dest)
    tmp_dest = tempfile.mkdtemp(dir=dest)
    try:
        args = _uv_install_args(
            easy_install._uv_executable(), pinned[0].url, tmp_dest, False,
            index_url(), level)
        args.extend(p.url for p in pinned[1:])
        easy_install._run_pip(args, os.environ.copy(), tmp_dest, level)
        newdists = []
        for pin in pinned:
            distro = _dist_for_pin(tmp_dest, pin)
            if distro is None:
                logger.error(
                    "Could not find installed distribution for %s after"
                    " successful uv pip install.",
                    pin.name)
                raise zc.buildout.UserError(
                    f"Could not find installed distribution for {pin.name}"
                    f" {pin.version} after successful uv pip install.")
            # The dist-info dirname comes from the installed dist, not
            # from an escaping rule: old-style wheels carry the raw
            # project name verbatim (``zc.recipe.egg-4.0.1.dist-info``,
            # dots included), which uv unpacks as-is (GH run
            # 35850441994).
            distinfo_dirname = os.path.basename(distro.egg_info)
            [egg_dir] = make_egg_after_pip_install(
                tmp_dest, distinfo_dirname, distro)
            newdist = _move_dist_into_place(distro, egg_dir, dest)
            # The new dist automatically has precedence DEVELOP_DIST,
            # which interferes with the check for printing picked
            # versions, so set it to EGG_DIST.  See
            # _move_to_eggs_dir_and_compile for the long story.
            newdist.precedence = pkg_resources.EGG_DIST
            newdists.append(newdist)
    finally:
        # Remember that temporary directories must be removed
        zc.buildout.rmtree.rmtree(tmp_dest)
    return newdists


def sort_working_set(ws: pkg_resources.WorkingSet, eggs_dir: str, develop_eggs_dir: str) -> pkg_resources.WorkingSet:
    from zc.buildout.easy_install import _dist_location
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
        path = _dist_location(dist)
        if path in develop_paths:
            sorted_paths.append(path)
        elif os.path.commonprefix([path, eggs_dir]) == eggs_dir:
            egg_paths.append(path)
        else:
            other_paths.append(path)
    sorted_paths.extend(egg_paths)
    sorted_paths.extend(other_paths)
    return pkg_resources.WorkingSet(sorted_paths)


