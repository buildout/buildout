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

from __future__ import annotations

import copy
import csv
import distutils.errors  # ty: ignore[unresolved-import]  # runtime: setuptools distutils-precedence hook
import email
import email.parser
import errno
import glob
import logging
import operator
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import warnings
import zipfile
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from functools import cached_property, lru_cache
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import pkg_resources
import setuptools.archive_util
import setuptools.command.setopt
from packaging import specifiers
from packaging.utils import canonicalize_name, is_normalized_name
from packaging.version import Version
from pkg_resources import Distribution
from setuptools.wheel import Wheel

import zc.buildout
import zc.buildout.rmtree
from zc.buildout import WINDOWS
from zc.buildout.develop import (
    _collect_distutils_dev_scripts,
    _copyeggs,
    _create_egg_link,
    _detect_distutils_scripts,
    _develop_distutils_scripts,
    _rm,
    develop,
)
from zc.buildout.errors import (
    IncompatibleConstraintError,
    IncompatibleVersionError,
    MissingDistribution,
    VersionConflict,
)
from zc.buildout.install_backend import (
    UNPACKERS,
    BuildoutWheel,
    _dist_info_dirname,
    _editable_scan_result,
    _ensure_dest_dir,
    _extra_index_url,
    _get_matching_dist_in_location,
    _installed_dist_name,
    _is_url,
    _lines_declare_namespace,
    _maybe_add_no_python_version_warning,
    _maybe_copy_and_rename_wheel,
    _move_dist_into_place,
    _move_record_leftovers,
    _move_to_eggs_dir_and_compile,
    _move_top_levels,
    _namespace_candidate_lines,
    _pip_install_args,
    _pip_install_env,
    _read_project_name,
    _read_record_entries,
    _read_top_levels,
    _remove_namespace_init_files,
    _remove_pip_bin_dir,
    _run_pip,
    _scan_editable_install,
    _unpack_dist_to_tmp,
    _uv_executable,
    _uv_install_args,
    _uv_sibling_executable,
    _uv_version,
    call_pip_install,
    check_namespace_init_file,
    find_namespace_init_files,
    install_pinned_dists,
    make_egg_after_pip_install,
    sort_working_set,
    unpack_egg,
    unpack_wheel,
)
from zc.buildout.scripts import (
    _collect_req_scripts,
    _create_script,
    _dist_distutils_scripts,
    _dist_entry_points,
    _distutils_script,
    _file_changed,
    _find_req_dist,
    _pyscript,
    _relative_depth,
    _relative_path,
    _relative_path_and_setup,
    _relativitize,
    _runsetup_template,
    _script,
    _script_paths,
    _script_target,
    _warn_missing_scripts,
    disable_root_logger,
    distutils_script_template,
    py_script_template,
    relative_paths_setup,
    script_header,
    script_template,
    scripts,
)
from zc.buildout.scripts import (
    working_set as _scripts_working_set,
)
from zc.buildout.utils import normalize_name

from . import _package_index, uv_resolve

# Aliased in the import above and bound here: the ``working_set``
# parameters of _working_set_or_default and Installer.install would
# shadow an unused import (ruff F811).
working_set = _scripts_working_set

BIN_SCRIPTS = 'Scripts' if WINDOWS else 'bin'

warnings.filterwarnings(
    'ignore', '.+is being parsed as a legacy, non PEP 440, version')

_oprp = getattr(os.path, 'realpath', lambda path: path)
def realpath(path: str) -> str:
    return os.path.normcase(os.path.abspath(_oprp(path)))

def _dist_location(dist: pkg_resources.Distribution) -> str:
    """The location of a distribution that is known to live on disk.

    pkg_resources types ``Distribution.location`` as optional, but the
    dists handled in this module are installed or downloadable dists,
    which always have a location.
    """
    location = dist.location
    assert location is not None
    return location

default_index_url = os.environ.get(
    'buildout_testing_index_url',
    'https://pypi.org/simple',
    )
default_installer = os.environ.get(
    'buildout_testing_installer',
    'pip',
    )


def _seam_testing_sources() -> tuple[list[str], str | None]:
    """The find-links and fallback index the harness adds to uv resolves.

    The hermetic harness exports ``buildout_testing_seam_find_links``
    (downloads/test-seam-seed, the seed minus the setuptools floor)
    and ``buildout_testing_seam_index_url`` (a dead index) so corpus
    resolves stay hermetic now that the seam scrubs ambient UV_*
    variables from the child environment it spawns uv with.  The links
    join the configured ones verbatim; the index only fills in when the
    configured sources carry no index, so it never shadows a configured
    or default index.  Both are unset in production, and pip mode never
    consults them.  Read dynamically so the harness covers in-process
    and spawned buildouts alike.
    """
    return (
        os.environ.get('buildout_testing_seam_find_links', '').split(),
        os.environ.get('buildout_testing_seam_index_url') or None,
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
buildout_and_setuptools_path = sorted({_dist_location(d) for d in pkg_resources.working_set})
setuptools_path = buildout_and_setuptools_path
pip_path = buildout_and_setuptools_path
logger.debug('before restricting versions: pip_path %r', pip_path)

FILE_SCHEME = re.compile('file://', re.IGNORECASE).match
DUNDER_FILE_PATTERN = re.compile(r"__file__ = '(?P<filename>.+)'$")


class EnvironmentMixin:
    """Mixin class for Environment and PackageIndex for canonicalized names.

    * pkg_resources defines the Environment class
    * setuptools defines a PackageIndex class that inherits from Environment
    * Buildout needs a few fixes that should be used by both.

    The fixes are needed for this issue, where distributions created by
    setuptools 69.3+ get a different name than with older versions:
    https://github.com/buildout/buildout/issues/647
    """
    if TYPE_CHECKING:
        # Provided by pkg_resources.Environment, which this mixin is always
        # combined with.  Declared here because the mixin itself does not
        # inherit from it.
        _distmap: dict[str, list[pkg_resources.Distribution]]

        def can_add(self, dist: pkg_resources.Distribution) -> bool: ...

    def __getitem__(self, project_name: str) -> list[pkg_resources.Distribution]:
        """Return a newest-to-oldest list of distributions for `project_name`

        Uses case-insensitive `project_name` comparison, assuming all the
        project's distributions use their project's name converted to all
        lowercase as their key.

        """
        distribution_key = normalize_name(project_name)
        return self._distmap.get(distribution_key, [])

    def add(self, dist: pkg_resources.DistInfoDistribution | pkg_resources.EggInfoDistribution | pkg_resources.Distribution) -> None:
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
    def _mac_machine_type(self) -> str:
        """Machine type (architecture) on Mac.

        Adapted from pkg_resources.compatible_platforms.
        If self.platform is something like 'macosx-15.4-arm64', we return 'arm64.
        """
        platform = self.platform
        # This property is only consulted when platform matching failed,
        # which cannot happen with a None platform.
        assert platform is not None
        match = macosVersionString.match(platform)
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
        # compatible_platforms() accepts a None provided platform, so
        # super().can_add() would not have failed and we would not be here.
        dist_platform = dist.platform
        assert dist_platform is not None
        provMac = macosVersionString.match(dist_platform)
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


_indexes = {}
def _get_index(index_url: str | None, find_links: list[str], allow_hosts: tuple[str, ...]=('*',)) -> AllowHostsPackageIndex:
    key = index_url, tuple(find_links)
    index = _indexes.get(key)
    if index is not None:
        return index

    if index_url is None:
        index_url = default_index_url
    index_url = index_url.removeprefix('file://')
    index = AllowHostsPackageIndex(index_url, hosts=allow_hosts)

    if find_links:
        index.add_find_links(find_links)

    _indexes[key] = index
    return index

clear_index_cache = _indexes.clear

if is_win32:
    # work around spawn lamosity on windows
    # XXX need safe quoting (see the subproces.list2cmdline) and test
    def _safe_arg(arg: str) -> str:
        return f'"{arg}"'
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


def call_subprocess(args: Sequence[str | Path], **kw: Any) -> None:  # type: ignore[explicit-any]  # forwarded into subprocess; its kwargs surface is not practically typeable
    if subprocess.call(args, **kw) != 0:
        raise Exception(  # noqa: TRY002 - legacy error contract: callers
            # catch broad Exception; the message text is the pinned surface
            f"Failed to run command:\n{repr(args)[1:-1]}")


def get_subprocess_output(args: list[str], **kw: Any) -> str:  # type: ignore[explicit-any]  # forwarded into subprocess.run; its kwargs surface is not practically typeable
    result = subprocess.run(
        args, **kw,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    stdout = result.stdout.decode("utf-8")
    if result.returncode:
        # A failed install is an environment or dependency problem, not a
        # bug in buildout or a recipe: carry the command's own output in a
        # UserError so the top level prints it in a clean error report
        # instead of the internal-error template and a traceback.
        cmd = repr(args)[1:-1]
        msg = f"Failed to run command:\n{cmd}\nError output follows:\n{stdout}"
        logger.error(msg)
        raise zc.buildout.UserError(msg)
    return stdout


def _execute_permission() -> int:
    current_umask = os.umask(0o022)
    # os.umask only returns the current umask if you also give it one, so we
    # have to give it a dummy one and immediately set it back to the real
    # value...  Distribute does the same.
    os.umask(current_umask)
    return 0o777 - current_umask



def get_namespace_package_paths(dist: pkg_resources.Distribution) -> Iterator[str]:
    """
    Generator of the expected pathname of each __init__.py file of the
    namespaces of a distribution.
    """
    base = [dist.location]
    init = ['__init__.py']
    for namespace in dist.get_metadata_lines('namespace_packages.txt'):
        yield os.path.join(*(base + namespace.split('.') + init))

def namespace_packages_need_pkg_resources(dist: pkg_resources.EggInfoDistribution | pkg_resources.Distribution) -> bool:
    if os.path.isfile(_dist_location(dist)):
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
                        b'pkgutil' not in source):
                    return True
    return False

def dist_needs_pkg_resources(dist: pkg_resources.DistInfoDistribution | pkg_resources.EggInfoDistribution | pkg_resources.Distribution) -> bool:
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


def _raise_if_junk_uv_constraint(
        installer: str,
        constraint: str,
        requirement: pkg_resources.Requirement,
        ) -> None:
    """uv mode reports a junk [versions] pin with the disallowed-pin error.

    ``_constrained_requirement`` lets a value that is no valid specifier
    escape as a bare InvalidSpecifier traceback; under installer = uv the
    parity error is the IncompatibleConstraintError a valid but
    disallowed pin gets.
    """
    if installer == 'uv' and not uv_resolve._is_valid_constraint(constraint):
        raise IncompatibleConstraintError(
            f"The requirement ({str(requirement)!r}) is not allowed "
            f"by your [versions] constraint ({constraint})")


def _constrained_requirement(constraint: str, requirement: pkg_resources.Requirement) -> pkg_resources.Requirement:
    assert isinstance(requirement, pkg_resources.Requirement)
    if constraint[0] not in '<>':
        if constraint.startswith('='):
            assert constraint.startswith('==')
            version = constraint[2:]
        else:
            version = constraint
            constraint = '==' + constraint
        if version not in requirement:
            msg = (f"The requirement ({str(requirement)!r}) is not allowed "
                   f"by your [versions] constraint ({version})")
            raise IncompatibleConstraintError(msg)
        specifier = specifiers.SpecifierSet(constraint)
    else:
        specifier = requirement.specifier & constraint
    constrained = copy.deepcopy(requirement)
    constrained.specifier = specifier
    return pkg_resources.Requirement.parse(str(constrained))


def _parse_requirements(
        specs: tuple[str, ...] | list[str],
        constrain: Callable[[pkg_resources.Requirement],
                            pkg_resources.Requirement],
        ) -> list[pkg_resources.Requirement]:
    """Parse ``specs`` into constrained requirements.

    Requirements whose environment marker does not apply are dropped;
    ``constrain`` applies the installer [versions] constraints.
    """
    requirements = [pkg_resources.Requirement.parse(spec)
                    for spec in specs]
    return [
        constrain(requirement)
        for requirement in requirements
        if not requirement.marker or requirement.marker.evaluate()
    ]


def _working_set_or_default(
        working_set: pkg_resources.WorkingSet | None,
        ) -> pkg_resources.WorkingSet:
    """Return ``working_set``, or a fresh empty one when none was given."""
    if working_set is None:
        return pkg_resources.WorkingSet([])
    return working_set


def _resolve_extra_requirements(
        req: pkg_resources.Requirement,
        dist: pkg_resources.Distribution,
        allow_unknown_extras: bool,
        ) -> list[str] | list[pkg_resources.Requirement]:
    """Return the requirements to follow from ``dist`` for ``req``.

    Extras requested by ``req`` but not provided by ``dist`` are warned
    about; unless ``allow_unknown_extras`` is set, that is a user error.
    With unknown extras, the surviving extras are returned by name.
    """
    missing_requested = sorted(
        set(req.extras) - set(dist.extras)
    )
    for missing in missing_requested:
        logger.warning(
            '%s does not provide the extra \'%s\'',
            dist, missing
        )
    if missing_requested:
        if not allow_unknown_extras:
            raise zc.buildout.UserError(
                "Couldn't find the required extra. "
                "This means the requirement is incorrect. "
                "If the requirement is itself from software you "
                "requested, then there might be a bug in "
                "requested software. You can ignore this by "
                "using 'allow-unknown-extras=true', however "
                "that may simply cause needed software to be omitted."
            )
        return sorted(
            set(dist.extras) & set(req.extras)
        )
    return dist.requires(req.extras)[::-1]


def _matching_dists(
        env: pkg_resources.Environment,
        req: pkg_resources.Requirement) -> list[pkg_resources.Distribution]:
    """Return the distributions in ``env`` for ``req``'s project that match
    ``req``."""
    return [dist for dist in env[req.project_name] if dist in req]


def _develop_dist(
        dists: list[pkg_resources.Distribution],
        ) -> pkg_resources.Distribution | None:
    """Return the first develop dist in ``dists``, if there is one."""
    for dist in dists:
        if dist.precedence == pkg_resources.DEVELOP_DIST:
            logger.debug('We have a develop egg: %s', dist)
            return dist
    return None


def _env_dist_for_pin(
        env: Environment,
        pin: uv_resolve.PinnedDist,
        ) -> pkg_resources.Distribution | None:
    """The environment's dist exactly matching ``pin``, if there is one."""
    wanted = pkg_resources.parse_version(pin.version)
    for dist in env[pin.name]:
        if dist.parsed_version == wanted:
            return dist
    return None


def _project_root(location: str) -> str:
    """The buildable project root for a develop dist's location.

    pkg_resources reports a src-layout develop dist's location as the
    ``src`` directory (the egg-info parent), while uv builds a directory
    requirement from the directory holding ``pyproject.toml`` or
    ``setup.py``.  The only sanctioned climb is that one ``src`` level:
    anything higher risks landing on an unrelated ancestor that happens
    to carry a project file (a develop dist faked onto ``site-packages``
    would otherwise resolve to whatever package owns the tree above).
    Falls back to the location itself, so an unusual layout reaches uv
    unchanged and fails there with uv's own message.
    """
    if (os.path.isfile(os.path.join(location, 'pyproject.toml'))
            or os.path.isfile(os.path.join(location, 'setup.py'))):
        return location
    if os.path.basename(location) == 'src':
        parent = os.path.dirname(location)
        if (os.path.isfile(os.path.join(parent, 'pyproject.toml'))
                or os.path.isfile(os.path.join(parent, 'setup.py'))):
            return parent
    return location


def _pin_beats_env_dist(
        pin: uv_resolve.PinnedDist,
        env_dist: pkg_resources.Distribution,
        prefer_final: bool,
        final_version: Callable[[Version], bool],
        ) -> bool:
    """Whether a lock pin should replace ``env_dist``.

    The compile cannot see the environment, so a requirement that rode
    the compile under ``newest`` comes back with the best *available*
    version even when the environment already holds something better or
    equal.  This is ``_select_newer_dist`` lifted from dists to a pin:
    under prefer-final a final release beats a pre-release regardless
    of the version numbers, and nothing replaces the environment's
    dist without being newer.
    """
    pin_version = pkg_resources.parse_version(pin.version)
    env_version = env_dist.parsed_version
    if prefer_final:
        if final_version(pin_version):
            if final_version(env_version):
                return env_version < pin_version
            return True
        return not final_version(env_version) and env_version < pin_version
    return env_version < pin_version


def _final_dists(
        dists: list[pkg_resources.Distribution],
        prefer_final: bool,
        final_version: Callable[[Version], bool],
        ) -> list[pkg_resources.Distribution]:
    """Filter ``dists`` down to final releases when finals are preferred.

    The input list is returned unchanged when finals are not preferred or
    no dist is final.
    """
    if prefer_final:
        fdists = [dist for dist in dists
                  if final_version(dist.parsed_version)
                  ]
        if fdists:
            # There are final dists, so only use those
            return fdists
    return dists


def _select_newer_dist(
        best_we_have: pkg_resources.Distribution,
        best_available: pkg_resources.Distribution,
        prefer_final: bool,
        final_version: Callable[[Version], bool],
        ) -> pkg_resources.Distribution | None:
    """Return ``best_available`` when it should replace ``best_we_have``.

    ``None`` means ``best_we_have`` stays.  When ``prefer_final`` is set, a
    final release beats a pre-release regardless of the version numbers.
    """
    if prefer_final:
        if final_version(best_available.parsed_version):
            if final_version(best_we_have.parsed_version):
                if (best_we_have.parsed_version
                    <
                    best_available.parsed_version
                    ):
                    return best_available
            else:
                return best_available
        else:
            if (not final_version(best_we_have.parsed_version)
                and
                (best_we_have.parsed_version
                 <
                 best_available.parsed_version
                 )
                ):
                return best_available
    else:
        if (best_we_have.parsed_version
            <
            best_available.parsed_version
            ):
            return best_available
    return None


def _available_dists(
        index: AllowHostsPackageIndex,
        requirement: pkg_resources.Requirement,
        source: int | None,
        ) -> list[pkg_resources.Distribution] | None:
    """Return the dists in ``index`` matching ``requirement`` and ``source``.

    ``None`` means the index has nothing available for the requirement.
    When ``source`` is set, only source dists are kept.
    """
    if index.obtain(requirement) is None:
        # Nothing is available.
        return None

    # Filter the available dists for the requirement and source flag
    return [dist for dist in index[requirement.project_name]
            if ((dist in requirement)
                and
                ((not source) or
                 (dist.precedence == pkg_resources.SOURCE_DIST)
                 )
                )
            ]


def _uv_resolve_requirements(
        requirements: Sequence[pkg_resources.Requirement],
        versions: Mapping[str, str],
        links: list[str],
        index_url: str | None,
        prefer_final: bool,
        uv_stderr: list[str] | None = None,
        offline: bool = False,
        fallback_index_url: str | None = None,
        overrides: Sequence[str] = (),
        ) -> uv_resolve.PinnedSet | None:
    """One ``uv pip compile`` for several requirements.

    Returns the pinned set from the lock; ``None`` means uv could not
    resolve.  The compile resolves the full dependency closure, so the
    set carries the transitive pins alongside the requested ones, and
    ``overrides`` lets the caller steer projects to directories (the
    develop projects of the running buildout).  The remaining arguments
    are forwarded to the seam exactly as ``_uv_available_dists``
    forwards them, and a resolve failure appends the tail of uv's
    stderr to ``uv_stderr`` when a list is passed.
    """
    for requirement in requirements:
        _raise_for_hg_links(requirement, links)
        _raise_for_fragment_links(requirement, links)
    try:
        return uv_resolve.resolve(
            requirements=[_without_extra_marker(requirement)
                          for requirement in requirements],
            constraints=versions,
            links=links,
            index_url=index_url,
            prefer_final=prefer_final,
            offline=offline,
            fallback_index_url=fallback_index_url,
            overrides=overrides,
            uv=_uv_executable(),
            python=sys.executable,
        )
    except uv_resolve.ResolutionError as err:
        logger.debug('uv could not resolve %r:\n%s',
                     ', '.join(str(requirement)
                               for requirement in requirements),
                     err.stderr)
        _note_uv_failure(uv_stderr, err.stderr)
        return None


def _uv_available_dists(
        requirement: pkg_resources.Requirement,
        source: int | None,
        versions: Mapping[str, str],
        links: list[str],
        index_url: str | None,
        prefer_final: bool,
        uv_stderr: list[str] | None = None,
        offline: bool = False,
        fallback_index_url: str | None = None,
        ) -> list[pkg_resources.Distribution] | None:
    """Return what uv resolves for ``requirement`` as a one-dist list.

    ``None`` means uv found nothing satisfying the requirement, matching
    the ``_available_dists`` contract.  The dist carries the resolved
    artifact URL as its location: the install step hands it straight to
    ``uv pip install``, so no separate download happens.  When a list is
    passed as ``uv_stderr``, a resolve failure appends the tail of uv's
    stderr to it, for the MissingDistribution message.  ``offline`` is
    forwarded to the seam: uv then serves the resolve from its own
    cache, without any network access.  ``fallback_index_url`` is
    forwarded likewise: the seam puts it on the argv only when the
    configured sources carry no index of their own.
    """
    pinned = _uv_resolve_requirements(
        [requirement], versions, links, index_url, prefer_final,
        uv_stderr, offline=offline, fallback_index_url=fallback_index_url)
    if pinned is None:
        _raise_if_egg_only(requirement, links, index_url)
        return None
    entry = pinned.for_project(requirement.project_name)
    if entry is None:
        _raise_if_egg_only(requirement, links, index_url)
        return None
    if source:
        if entry.sdist_url is None:
            return None
        url = entry.sdist_url
    else:
        url = entry.url
    return [Distribution(
        location=url, project_name=entry.name, version=entry.version)]


def _stderr_tail(stderr: str) -> list[str]:
    """The last non-empty lines of ``stderr``, at most two.

    uv's own wording explains the cause class (not found, unsatisfiable);
    the tail keeps the user-facing error short while preserving it.
    """
    return [line for line in stderr.splitlines() if line.strip()][-2:]


def _note_uv_failure(note: list[str] | None, stderr: str) -> None:
    """Append the tail of uv's ``stderr`` to ``note`` when collecting."""
    if note is not None:
        note.extend(_stderr_tail(stderr))


def _tail_text(lines: list[str]) -> str | None:
    """Collected uv stderr tail lines as one text, None when empty."""
    if not lines:
        return None
    return '\n'.join(lines)


def _raise_for_hg_links(
        requirement: pkg_resources.Requirement,
        links: list[str],
        ) -> None:
    """Fail clearly when a find-links entry points at Mercurial.

    uv cannot clone Mercurial repositories; without the guard the entry
    surfaces as uv's own requirement-parse error.  Raised before uv is
    spawned, so the message names the entry in buildout's vocabulary.
    """
    for link in links:
        if link.startswith(('hg:', 'hg+')):
            raise zc.buildout.UserError(
                f"Cannot install {requirement} with installer = uv:"
                f" find-links entry {link} points at a Mercurial"
                " repository, and uv cannot install from Mercurial."
                " Provide a wheel or sdist, or use installer = pip.")


def _raise_for_fragment_links(
        requirement: pkg_resources.Requirement,
        links: list[str],
        ) -> None:
    """Fail clearly when a find-links entry carries an URL fragment.

    pip's scraper reads ``#egg=`` and ``#md5=`` fragments; uv rejects
    them at parse time.  Raised before uv is spawned, so the message
    names the fragment in buildout's vocabulary.
    """
    for link in links:
        for fragment in ('#egg=', '#md5='):
            if fragment in link:
                raise zc.buildout.UserError(
                    f"Cannot install {requirement} with installer = uv:"
                    f" find-links entry {link} carries a {fragment}"
                    " fragment, which uv does not support."
                    " Provide a wheel or sdist, or use installer = pip.")


_EXTRA_MARKER_ONLY = re.compile(
    r''';\s*extra == ("[^"]*"|'[^']*')\s*$''')
_EXTRA_MARKER_TAIL = re.compile(
    r'''\s+and\s+extra == ("[^"]*"|'[^']*')\s*$''')


def _without_extra_marker(requirement: pkg_resources.Requirement) -> str:
    """The requirement string without any ``extra == ...`` marker.

    pkg_resources adds ``extra == "..."`` markers to requirements pulled
    from a dist's metadata via extras. The extra is satisfied by
    construction here: we resolve the dependency because the dist
    carrying it was selected with that extra. As a top-level input line
    the marker has no extras context, would evaluate False, and uv
    would silently drop the requirement from the lock. Only the
    extra-only and trailing ``and extra == ...`` shapes are stripped.
    """
    spec = str(requirement)
    if _EXTRA_MARKER_ONLY.search(spec):
        return _EXTRA_MARKER_ONLY.sub('', spec)
    return _EXTRA_MARKER_TAIL.sub('', spec)


def _local_listing(location: str | None) -> list[str]:
    """Filenames in a local find-links directory, [] for remote or missing."""
    if not location:
        return []
    if '://' in location:
        directory = uv_resolve._local_directory(location)
        if directory is None:
            return []
    else:
        directory = Path(location)
        if not directory.is_dir():
            return []
    return os.listdir(directory)


def _raise_if_egg_only(
        requirement: pkg_resources.Requirement,
        links: list[str],
        index_url: str | None,
        ) -> None:
    """Raise a clear error when only legacy eggs offer ``requirement``.

    uv cannot read the legacy .egg format, so a project offered only as
    eggs is invisible to it and would otherwise surface as a bare
    Couldn't-find-a-distribution.  Local find-links directories are
    scanned (remote listings are not cheaply available): a directory
    holding .egg artifacts for the project and no wheel or sdist
    explains the failure.
    """
    prefix = canonicalize_name(requirement.project_name).replace('-', '_') + '-'
    for location in [*links, index_url]:
        artifacts = [
            name for name in _local_listing(location)
            if name.startswith(prefix)
            # The character after the name- prefix starts the version,
            # which keeps related projects (demo-extra) out of a
            # listing consulted for demo.
            and name[len(prefix):len(prefix)+1].isdigit()]
        if (artifacts
                and any(name.endswith('.egg') for name in artifacts)
                and not any(name.endswith(('.whl', '.tar.gz', '.zip'))
                            for name in artifacts)):
            raise zc.buildout.UserError(
                f"Cannot install {requirement} with installer = uv:"
                f" found only legacy .egg distributions in"
                f" {location}, and uv cannot install eggs."
                " Provide a wheel or sdist, or use installer = pip.")


def _best_version_dists(
        dists: list[pkg_resources.Distribution],
        ) -> list[pkg_resources.Distribution]:
    """Return the dists in ``dists`` tied for the highest parsed version."""
    best = []
    bestv = None
    for dist in dists:
        distv = dist.parsed_version
        if bestv is None or distv > bestv:
            best = [dist]
            bestv = distv
        elif distv == bestv:
            best.append(dist)
    return best


def _select_from_best(
        best: list[pkg_resources.Distribution],
        download_cache: str | None,
        ) -> pkg_resources.Distribution:
    """Return one of the ``best`` dists, all tied for the highest version.

    A dist already in ``download_cache`` wins; otherwise the last dist
    after sorting.
    """
    if download_cache:
        for dist in best:
            if (realpath(os.path.dirname(_dist_location(dist)))
                ==
                download_cache
                ):
                return dist

    best.sort()
    return best[-1]


def _fetch_requested_dists(
        requirements: list[pkg_resources.Requirement],
        ws: pkg_resources.WorkingSet,
        get_dist: Callable,
        maybe_add_setuptools: Callable,
        ) -> None:
    """Fetch the dists of the initially requested requirements into the
    working set."""
    for requirement in requirements:
        for dist in get_dist(requirement, ws):
            maybe_add_setuptools(ws, dist)


def _best_matching_dist(
        best: dict[str, pkg_resources.Distribution],
        env: pkg_resources.Environment,
        req: pkg_resources.Requirement,
        ws: pkg_resources.WorkingSet,
        current_requirement: pkg_resources.Requirement,
        for_buildout_run: bool,
        ) -> pkg_resources.Distribution | None:
    """Return the best dist picked so far for ``req``, or the
    environment's best match.

    A version conflict is fatal, except during a buildout run: the
    active global ``pkg_resources.working_set`` includes all system
    packages, so conflicts can be fine to ignore — the correct version
    is picked up a few lines down.
    """
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
            # recipes requires the global ``pkg_resources.working_set``
            # to be active, which also includes all system packages.
            # So there might be conflicts, which are fine to ignore.
            # We'll grab the correct version a few lines down.
            if not for_buildout_run:
                raise VersionConflict(err, ws)
    return dist


def _fetch_new_dists(
        requirement: pkg_resources.Requirement,
        avail: pkg_resources.Distribution | None,
        ws: pkg_resources.WorkingSet,
        dest: str | None,
        download_cache: str | None,
        fetch: Callable[
            [pkg_resources.Distribution, str, str | None],
            pkg_resources.Distribution | None],
        env: pkg_resources.Environment,
        rescan_dest: Callable[[], None],
        detail: str | None = None,
        ) -> list[pkg_resources.Distribution | pkg_resources.DistInfoDistribution | pkg_resources.EggInfoDistribution]:
    """Download, install and register a distribution for ``requirement``.

    Called when no installed dist satisfies the requirement: fetches
    ``avail`` into the download cache or a fresh temporary directory,
    moves the result into the eggs destination directory ``dest``, adds
    it to the working set and rescans the destination.  ``detail`` is
    extra context for the MissingDistribution error (the tail of uv's
    stderr in uv mode).
    """
    if dest is None:
        raise zc.buildout.UserError(
            f"We don't have a distribution for {requirement}\n"
            "and can't install one in offline (no-install) mode.\n")

    logger.info('Getting distribution for %r.', str(requirement))

    if avail is None:
        # We have no existing dist, and none is available for download.
        raise MissingDistribution(requirement, ws, detail)

    # We may overwrite distributions, so clear importer
    # cache.
    sys.path_importer_cache.clear()

    tmp = download_cache
    if tmp is None:
        tmp = tempfile.mkdtemp('get_dist')

    try:
        dist = fetch(avail, tmp, download_cache)

        if dist is None:
            raise zc.buildout.UserError(
                f"Couldn't download distribution {avail}.")

        dists = [_move_to_eggs_dir_and_compile(dist, dest)]
        for _d in dists:
            if _d not in ws:
                ws.add(_d, replace=True)

    finally:
        if tmp != download_cache:
            zc.buildout.rmtree.rmtree(tmp)

    rescan_dest()
    dist = env.best_match(requirement, ws)

    logger.info("Got %s.", dist)

    return dists


def _cache_links_and_index(
        install_from_cache: bool,
        download_cache: str | None,
        links: tuple[str, ...] | list[str],
        index: str | None,
        ) -> tuple[tuple[str, ...] | list[str], str | None]:
    """Return the links and index forced by install-from-cache mode.

    In install-from-cache mode no remote location is consulted: the
    download cache becomes the only index.  A cache must be configured.
    """
    if install_from_cache:
        if not download_cache:
            raise ValueError("install_from_cache set to true with no"
                             " download cache")
        links = ()
        index = 'file://' + download_cache
    return links, index


def _cache_mode_links_and_index(
        installer: str,
        install_from_cache: bool,
        download_cache: str | None,
        links: tuple[str, ...] | list[str],
        index: str | None,
        ) -> tuple[tuple[str, ...] | list[str], str | None]:
    """Apply the install-from-cache restriction, pip mode only.

    With installer = uv, install-from-cache maps onto uv's own cache
    instead (``Installer._obtain`` resolves with ``--offline``): the
    pip download-cache restriction has no uv equivalent, so the
    configured sources pass through unchanged.
    """
    if installer == 'uv':
        return links, index
    return _cache_links_and_index(
        install_from_cache, download_cache, links, index)


def _prepare_links(
        links: tuple[str, ...] | list[str],
        download_cache: str | None,
        fix_file_links: Callable[
            [tuple[str, ...] | list[str]], Iterator[str]],
        ) -> list[str]:
    """Return the fixed-up find links, with the download cache first."""
    prepared = list(fix_file_links(links))
    if download_cache and (download_cache not in prepared):
        prepared.insert(0, download_cache)
    return prepared


def _initial_path(path: list[str] | None) -> list[str]:
    """Return a copy of ``path`` plus the buildout/setuptools locations."""
    # ``path[:]`` copies: later mutations of the argument must not leak in.
    return (path and path[:] or []) + buildout_and_setuptools_path


def _unpack_dist_for_build(dist: pkg_resources.Distribution, build_tmp: str) -> str:
    """Unpack ``dist`` into ``build_tmp`` and return its setup base dir."""
    setuptools.archive_util.unpack_archive(dist.location,
                                           build_tmp)
    base = build_tmp
    if not os.path.exists(os.path.join(build_tmp, 'setup.py')):
        setups = glob.glob(
            os.path.join(build_tmp, '*', 'setup.py'))
        if not setups:
            # We used to raise an error, but now we just log a warning.
            # Maybe there is a pyproject.toml file that pip can use.
            # Otherwise we let pip do the complaining.
            logger.warning(
                "Couldn't find a setup script to build in %s. "
                "Trying pip install anyway.",
                os.path.basename(_dist_location(dist))
            )
        elif len(setups) > 1:
            raise distutils.errors.DistutilsError(
                f"Multiple setup scripts in "
                f"{os.path.basename(_dist_location(dist))}")
        else:
            base = os.path.dirname(setups[0])
    return base


def _write_build_ext_config(base: str, build_ext: dict[str, str]) -> None:
    """Create ``setup.cfg`` in ``base`` if missing and set ``build_ext``."""
    setup_cfg = os.path.join(base, 'setup.cfg')
    if not os.path.exists(setup_cfg):
        with open(setup_cfg, 'w'):
            pass  # create the empty file that edit_config expects
    setuptools.command.setopt.edit_config(
        setup_cfg, {'build_ext': build_ext})


class Installer:

    _versions = {}  # noqa: RUF012 - class-level default, deliberately
    # shadowed per instance in __init__ when versions are given
    _required_by: ClassVar[dict] = {}
    _picked_versions: ClassVar[dict] = {}
    _download_cache = None
    _install_from_cache = False
    _offline = False
    _prefer_final = True
    _use_dependency_links = True
    _allow_picked_versions = True
    _store_required_by = False
    _allow_unknown_extras = False
    _namespace_packages: ClassVar[dict] = {}
    _index_url = None
    _installer = default_installer

    def __init__(self,
                 dest: str | None=None,
                 links: tuple[str, ...] | list[str]=(),
                 index: str | None=None,
                 executable: str=sys.executable,
                 always_unzip: bool | None=None, # Backward compat :/
                 path: list[str] | None=None,
                 newest: bool=True,
                 versions: Mapping[str, str] | None=None,
                 use_dependency_links: bool | None=None,
                 allow_hosts: tuple[str, ...]=('*',),
                 check_picked: bool=True,
                 allow_unknown_extras: bool=False,
                 ) -> None:
        assert executable == sys.executable, (executable, sys.executable)
        self._dest = dest if dest is None else pkg_resources.normalize_path(dest)
        self._allow_hosts = allow_hosts
        self._allow_unknown_extras = allow_unknown_extras

        links, index = _cache_mode_links_and_index(
            self._installer, self._install_from_cache,
            self._download_cache, links, index)

        if use_dependency_links is not None:
            self._use_dependency_links = use_dependency_links
        self._links = links = _prepare_links(
            links, self._download_cache, self._fix_file_links)

        if index:
            self._index_url = index

        path = _initial_path(path)
        self._path = path
        if self._dest is None:
            newest = False
        self._newest = newest
        self._env = self._make_env()
        self._index = _get_index(index, links, self._allow_hosts)
        self._requirements_and_constraints = []
        self._check_picked = check_picked
        self._uv_stderr_tail: str | None = None

        if versions is not None:
            self._versions = normalize_versions(versions)

    def _make_env(self) -> Environment:
        dist_paths = self._get_dest_dist_paths()
        full_path = dist_paths + self._path
        env = Environment(full_path)
        # this needs to be called whenever self._env is modified (or we could
        # make an Environment subclass):
        self._eggify_env_dist_dists(env, dist_paths)
        return env

    def _env_rescan_dest(self) -> None:
        dist_paths = self._get_dest_dist_paths()
        self._env.scan(dist_paths)
        self._eggify_env_dist_dists(self._env, dist_paths)

    def _get_dest_dist_paths(self) -> list[str]:
        dest = self._dest
        if dest is None:
            # Offline mode: there is no destination directory, but the
            # eggs directory is on the path.  A plain Environment scan
            # of it only recognizes the classic EGG-INFO layout, while
            # wheels installed by pip or uv keep their dist-info inside
            # the .egg directory.  Find those explicitly so offline
            # runs can reuse what is already installed.
            return list(set(
                os.path.dirname(dist_info)
                for entry in self._path
                for dist_info in glob.glob(
                    os.path.join(entry, '*.egg', '*.dist-info'))))
        eggs = glob.glob(os.path.join(dest, '*.egg'))
        dists = [os.path.dirname(dist_info) for dist_info in
                 glob.glob(os.path.join(dest, '*', '*.dist-info'))]
        return list(set(eggs + dists))

    @staticmethod
    def _eggify_env_dist_dists(
            env: Environment, dist_paths: list[str]) -> None:
        """
        Make sure everything found at `dist_paths` is seen as an egg, even if
        it's some other kind of dist.

        Both sides go through pkg_resources.normalize_path: the scan
        normalizes dist locations (realpath, plus normcase case-folding on
        Windows) while dist_paths keep the configured spelling, so raw
        string comparison silently misses — leaving wheel-installed dists
        at DEVELOP_DIST precedence, which flips offline part signatures
        from egg basename to directory hash.
        """
        containers = {pkg_resources.normalize_path(os.path.dirname(path))
                      for path in dist_paths}
        for project_name in env:
            for dist in env[project_name]:
                location = pkg_resources.normalize_path(
                    os.path.dirname(_dist_location(dist)))
                if location in containers:
                    dist.precedence = pkg_resources.EGG_DIST

    def _version_conflict_information(self, name: str) -> str:
        """Return textual requirements/constraint information for debug purposes

        We do a very simple textual search, as that filters out most
        extraneous information without missing anything.

        """
        output = [
            f"Version and requirements information containing {name}:"]
        version_constraint = self._versions.get(canonicalize_name(name))
        if version_constraint:
            output.append(
                f"[versions] constraint on {name}: {version_constraint}")
        output += [line for line in self._requirements_and_constraints
                   if name.lower() in line.lower()]
        return '\n  '.join(output)

    def _satisfied(self, req: pkg_resources.Requirement, source: int | None=None) -> tuple[pkg_resources.Distribution | None, pkg_resources.Distribution | None]:
        dists = _matching_dists(self._env, req)
        if not dists:
            logger.debug('We have no distributions for %s that satisfies %r.',
                         req.project_name, str(req))

            return None, self._obtain(req, source)

        # Note that dists are sorted from best to worst, as promised by
        # env.__getitem__

        develop_dist = _develop_dist(dists)
        if develop_dist is not None:
            return develop_dist, None

        # Special common case, we have a specification for a single version:
        specs = req.specs
        if len(specs) == 1 and specs[0][0] == '==':
            logger.debug('We have the distribution that satisfies %r.',
                         str(req))
            return dists[0], None

        dists = _final_dists(dists, self._prefer_final, self._final_version)

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

        newer = _select_newer_dist(
            best_we_have, best_available,
            self._prefer_final, self._final_version)
        if newer is not None:
            return None, newer

        logger.debug(
            'We have the best distribution that satisfies %r.',
            str(req))
        return best_we_have, None

    def _satisfied_uv(self, req: pkg_resources.Requirement) -> pkg_resources.Distribution | None:
        """The environment's dist for ``req`` when no compile is needed.

        ``_satisfied`` without the availability lookup: develop
        distributions and exact pins always settle the requirement, and
        without newest any matching dist does.  Under newest a matching
        dist stays unsettled here; it rides the single compile so a
        newer available version wins.  The debug notes are the ones
        ``_satisfied`` leaves at the same decision points.
        """
        dists = _matching_dists(self._env, req)
        if not dists:
            logger.debug('We have no distributions for %s that satisfies %r.',
                         req.project_name, str(req))
            return None
        develop_dist = _develop_dist(dists)
        if develop_dist is not None:
            return develop_dist
        specs = req.specs
        if len(specs) == 1 and specs[0][0] == '==':
            logger.debug('We have the distribution that satisfies %r.',
                         str(req))
            return dists[0]
        if self._newest:
            return None
        return _final_dists(dists, self._prefer_final, self._final_version)[0]

    def _develop_overrides(
            self,
            requirements: list[pkg_resources.Requirement],
            ) -> list[str]:
        """The environment's develop dists as uv override lines.

        Each line pins the project to its project root in pip's
        ``name @ url`` form, so a compile whose closure references the
        project resolves it from its sources; an unreferenced override
        is inert and can neither fail nor skew the resolution.  Dists
        whose directory vanished are left out: their egg-link is stale
        and the configured sources get their chance instead.

        Develop precedence mirrors ``_satisfied``: a develop dist wins
        only when it satisfies every spec the batch and the [versions]
        constraints place on its project.  A dist that fails one — an
        exact pin at another version, say — keeps its configured
        sources reachable, so the pin resolves the way the resolution
        loop resolved it.
        """
        by_project: dict[str, list[pkg_resources.Requirement]] = {}
        for requirement in requirements:
            by_project.setdefault(
                str(canonicalize_name(requirement.project_name)),
                []).append(requirement)
        overrides = set()
        for project_name in self._env:
            for dist in self._env[project_name]:
                if dist.precedence != pkg_resources.DEVELOP_DIST:
                    continue
                name = str(canonicalize_name(dist.project_name))
                if any(dist not in req
                       for req in by_project.get(name, [])):
                    continue
                constraint = self._versions.get(name)
                if constraint:
                    spec = (constraint if constraint[0] in '<>='
                            else '==' + constraint)
                    if dist not in pkg_resources.Requirement.parse(
                            name + spec):
                        continue
                root = _project_root(_dist_location(dist))
                # uv reads override metadata even for projects the
                # compile never references, so an override must name a
                # buildable project: a develop egg faked onto
                # site-packages (no pyproject.toml or setup.py) would
                # otherwise fail the whole compile with uv's metadata
                # error.  Such a dist can still settle its requirement
                # from the environment; it just cannot serve a compile.
                if not (os.path.isfile(os.path.join(root, 'pyproject.toml'))
                        or os.path.isfile(os.path.join(root, 'setup.py'))):
                    continue
                overrides.add(
                    f'{dist.project_name} @ {Path(root).as_uri()}')
        return sorted(overrides)

    def _log_uv_using_best(self, requirement: pkg_resources.Requirement) -> None:
        """The debug note ``_satisfied`` leaves when sources run dry."""
        dists = _matching_dists(self._env, requirement)
        if dists:
            logger.debug(
                'There are no distros available that meet %r.\n'
                'Using our best, %s.', str(requirement), dists[0])

    def _uv_resolve_for_install(
            self,
            requirements: list[pkg_resources.Requirement],
            ws: pkg_resources.WorkingSet,
            ) -> uv_resolve.PinnedSet:
        """One compile for the unsatisfied requirements.

        Raises MissingDistribution when uv cannot resolve.  Under
        newest a requirement with an installed match rides the compile
        only to find something newer, so when the compile fails the
        retry keeps those requirements out, matching how the
        per-requirement resolves this replaces degraded to the
        installed dist when sources ran dry.
        """
        seam_links, seam_index = _seam_testing_sources()
        index_url = self._index_url or default_index_url
        links = [*self._links, *seam_links]
        uv_stderr: list[str] = []
        pinned = _uv_resolve_requirements(
            requirements, self._versions, links, index_url,
            self._prefer_final, uv_stderr, offline=self._uv_offline(),
            fallback_index_url=seam_index,
            overrides=self._develop_overrides(requirements))
        self._uv_stderr_tail = _tail_text(uv_stderr)
        attempted = requirements
        if pinned is None and self._newest:
            matched = [bool(_matching_dists(self._env, requirement))
                       for requirement in requirements]
            required = [requirement for requirement, has_installed
                        in zip(requirements, matched) if not has_installed]
            if len(required) < len(requirements):
                degraded = [requirement for requirement, has_installed
                            in zip(requirements, matched) if has_installed]
                if required:
                    pinned = _uv_resolve_requirements(
                        required, self._versions, links, index_url,
                        self._prefer_final, uv_stderr,
                        offline=self._uv_offline(),
                        fallback_index_url=seam_index,
                        overrides=self._develop_overrides(required))
                    self._uv_stderr_tail = _tail_text(uv_stderr)
                    attempted = required
                else:
                    pinned = uv_resolve.PinnedSet(())
                if pinned is not None:
                    for requirement in degraded:
                        self._log_uv_using_best(requirement)
        if pinned is None:
            raise MissingDistribution(attempted[0], ws,
                                      self._uv_stderr_tail)
        return pinned

    def _graft_pinned(
            self,
            pinned: uv_resolve.PinnedSet,
            requirements: list[pkg_resources.Requirement],
            ws: pkg_resources.WorkingSet,
            for_buildout_run: bool,
            ) -> tuple[dict[str, pkg_resources.Distribution], list[pkg_resources.Distribution]]:
        """Install the pinned closure and register it in ``ws``.

        Artifact pins the environment already holds at the pinned
        version graft from there; the rest install in one batch.
        Referenced develop projects graft their develop dists.  Returns
        the grafted distributions by canonical project name and the
        ones the setuptools sweep still owes a look (freshly installed
        or fetched for a requested requirement, the two shapes the
        resolution loop used to sweep).  Picked versions are recorded
        on the way, per the requested requirement when there is one.

        The compile cannot see the environment, so a requirement that
        rode the compile under ``newest`` can come back pinned to the
        best *available* version although the environment holds one at
        least as good: the environment's dist stays then, the way the
        resolution loop kept ``best_we_have``, and its installed
        dependency tree walks in from the environment, vetoing the
        pins of the projects it covers.  (A kept dist whose installed
        tree differs from the replaced pin's tree can leave the pin's
        unused subtree installed; the loop never produced those eggs,
        but a working set entry it never had is the worse deviation.)

        Working-set order mirrors the loop's: freshly installed dists
        front-insert in fetch order (requested requirements first, then
        the remaining pins), which lists the set dependency-first, and
        environment-kept requested dists graft in requirement order,
        their walked dependency trees after them.
        """
        requested = {str(canonicalize_name(requirement.project_name)): requirement
                     for requirement in requirements}
        assert self._dest is not None  # _install_uv raises earlier otherwise

        artifact_pins = [pin for pin in pinned.dists if pin.directory is None]

        vetoed: set[str] = set()
        gated: set[str] = set()
        resolved: dict[str, pkg_resources.Distribution] = {}
        swept: list[pkg_resources.Distribution] = []
        pin_by_name = {str(canonicalize_name(pin.name)): pin
                       for pin in artifact_pins}
        kept: list[tuple[pkg_resources.Requirement,
                         pkg_resources.Distribution]] = []
        for requirement in requirements:
            name = str(canonicalize_name(requirement.project_name))
            pin = pin_by_name.get(name)
            if pin is None:
                continue
            dists = _matching_dists(self._env, requirement)
            if not dists:
                continue
            env_best = _final_dists(
                dists, self._prefer_final, self._final_version)[0]
            if _pin_beats_env_dist(
                    pin, env_best, self._prefer_final, self._final_version):
                continue
            logger.debug(
                'We have the best distribution that satisfies %r.',
                str(requirement))
            if self._check_picked:
                # The loop gated a requested requirement before its
                # dependencies walked: a picked top-level egg reports
                # itself, not the first transitive dep the walk meets.
                self._check_picked_requirement_versions(
                    requirement, [env_best])
                gated.add(name)
            vetoed.add(name)
            resolved[name] = env_best
            swept.append(env_best)
            # The requested dists all join the working set before any
            # dependency walks in: the loop's fetch phase settled every
            # request ahead of its resolution half, so an environment
            # keep that interleaved its own deps between two requested
            # dists inverted the working-set order legacy printed.
            if env_best not in ws:
                ws.add(env_best)
            kept.append((requirement, env_best))
        for requirement, env_best in kept:
            walked = self._walk_installed_deps(
                [(requirement, env_best)], ws, [], for_buildout_run,
                defer=set(requested), pins=pin_by_name)
            vetoed.update(str(canonicalize_name(dist.project_name))
                          for _req, dist in walked)
            swept.extend(dist for _req, dist in walked)

        to_install = []
        waiting = []
        for pin in artifact_pins:
            name = str(canonicalize_name(pin.name))
            if name in vetoed:
                continue
            dist = _env_dist_for_pin(self._env, pin)
            if dist is None:
                to_install.append(pin)
            else:
                waiting.append((pin, dist))
        requested_index = {name: index
                           for index, name in enumerate(requested)}
        to_install.sort(
            key=lambda pin: requested_index.get(
                str(canonicalize_name(pin.name)), len(requested_index)))
        new_dists = install_pinned_dists(to_install, self._dest)
        for dist in new_dists:
            logger.info("Got %s.", dist)
            ws.add(dist, replace=True)
            resolved[str(canonicalize_name(dist.project_name))] = dist
            swept.append(dist)
        if new_dists:
            self._env_rescan_dest()
        for pin, dist in waiting:
            name = str(canonicalize_name(pin.name))
            if dist not in ws:
                if dist.key in ws.by_key:
                    # The working set holds the project at another
                    # version: fetched-dist replace semantics.
                    ws.add(dist, replace=True)
                else:
                    ws.add(dist)
            resolved[name] = dist
            if name in requested:
                swept.append(dist)
                logger.debug(
                    'We have the best distribution that satisfies %r.',
                    str(requested[name]))
        for pin in pinned.dists:
            if pin.directory is None:
                continue
            dist = _develop_dist(self._env[pin.name])
            if dist is not None:
                if dist not in ws:
                    ws.add(dist)
                resolved[str(canonicalize_name(pin.name))] = dist
        unresolved: list[pkg_resources.Requirement] = []
        for requirement in requirements:
            # A requirement that only rode the compile to check for
            # something newer comes back unpinned when a failed first
            # resolve degraded to the installed dist; graft that one
            # and walk its installed dependency tree in, the way the
            # resolution loop's second half would have.
            name = str(canonicalize_name(requirement.project_name))
            if name in resolved:
                continue
            dists = _matching_dists(self._env, requirement)
            if dists:
                dist = _final_dists(
                    dists, self._prefer_final, self._final_version)[0]
                walked = self._walk_installed_deps(
                    [(requirement, dist)], ws, unresolved,
                    for_buildout_run, defer=set(requested))
                for _req, walked_dist in walked:
                    walked_name = str(
                        canonicalize_name(walked_dist.project_name))
                    if walked_name not in resolved:
                        resolved[walked_name] = walked_dist
                        swept.append(walked_dist)
                if dist not in ws:
                    ws.add(dist)
                resolved[name] = dist
                swept.append(dist)
        if unresolved:
            # The degraded graft cannot fetch: the resolve already ran
            # dry.  What the walk could not settle is missing.
            raise MissingDistribution(
                unresolved[0], ws, self._uv_stderr_tail)
        if new_dists:
            # The required-by provenance the loop collected through
            # ``_log_requirement`` for every dependency it fetched,
            # with its ``Getting required`` note ahead of it.
            for dist in new_dists:
                name = str(canonicalize_name(dist.project_name))
                if name not in requested:
                    req = self._constrain(pkg_resources.Requirement.parse(name))
                    logger.debug('Getting required %r', str(req))
                    self._log_requirement(ws, req)
        if self._check_picked:
            new_names = {str(canonicalize_name(dist.project_name))
                         for dist in new_dists}
            for name, dist in resolved.items():
                if name in requested:
                    if name in gated:
                        # An environment-kept requirement reported
                        # itself ahead of its dependency walk, the
                        # loop's order; reporting twice is not.
                        continue
                    self._check_picked_requirement_versions(
                        requested[name], [dist])
                elif name in new_names:
                    self._check_picked_requirement_versions(
                        self._constrain(
                            pkg_resources.Requirement.parse(name)),
                        [dist])
        return resolved, swept

    def _walk_installed_deps(
            self,
            satisfied: list[tuple[pkg_resources.Requirement, pkg_resources.Distribution]],
            ws: pkg_resources.WorkingSet,
            to_resolve: list[pkg_resources.Requirement],
            for_buildout_run: bool,
            defer: set[str] | None = None,
            pins: dict[str, uv_resolve.PinnedDist] | None = None,
            ) -> list[tuple[pkg_resources.Requirement, pkg_resources.Distribution]]:
        """Walk the installed dependency tree of ``satisfied`` into ``ws``.

        The resolution loop's other half for dists the environment
        already holds: every requirement of every selected dist joins
        the working set, walking installed metadata breadth-first in
        the loop's own order (the reversed seed stack, then appended
        requirements).  Requirements the environment cannot satisfy
        collect into ``to_resolve`` for the single compile; the closure
        the compile returns covers their own dependencies.  Returns the
        (requirement, dist) pairs the walk settled from the working set
        or the environment, so callers can tell which projects need no
        resolution decision.

        ``defer`` names projects the batch settles on its own terms —
        the loop reached an explicit requirement before any dependency
        edge walked to its project, so a walked edge must not pre-empt
        an exact pin from the same batch with whatever the environment
        happens to hold.  ``pins`` carries the compile's artifact pins
        when the walk runs after a resolve: a walked dependency settles
        from the environment only when its pin would not beat the
        environment's dist, the same ``_select_newer_dist`` call the
        loop made per dependency under newest.
        """
        dists_by_key = {req.key: dist for req, dist in satisfied}
        queue = [req for req, _dist in reversed(satisfied)]
        processed = set()
        best = {}
        walked = []
        while queue:
            current_requirement = queue.pop(0)
            req = self._constrain(current_requirement)
            if req in processed:
                # Ignore cyclic or redundant dependencies.
                continue
            processed.add(req)
            if (defer and req.key not in dists_by_key
                    and str(canonicalize_name(req.project_name)) in defer):
                continue
            dist = dists_by_key.get(req.key)
            if dist is None:
                dist = best.get(req.key)
            if dist is None:
                try:
                    dist = ws.find(req)
                except pkg_resources.VersionConflict as err:
                    logger.debug(
                        "Version conflict while processing requirement %s "
                        "(constrained to %s)",
                        current_requirement, req)
                    # Tolerated during a buildout run for the reasons
                    # _best_matching_dist documents.
                    if not for_buildout_run:
                        raise VersionConflict(err, ws)
            from_environment = False
            if dist is None:
                dists = _matching_dists(self._env, req)
                if dists:
                    # ``_satisfied`` prefers a develop dist and says
                    # so; the walk settles environment misses the same
                    # way, so the verbose transcript keeps its per-dep
                    # 'We have a develop egg' lines.
                    dist = _develop_dist(dists) or dists[0]
                    from_environment = True
            if dist is not None and from_environment and pins is not None:
                pin = pins.get(str(canonicalize_name(req.project_name)))
                if (pin is not None
                        and _pin_beats_env_dist(
                            pin, dist,
                            self._prefer_final, self._final_version)):
                    # The pin installs something newer; leave the
                    # project to the graft.
                    continue
            if dist is None:
                if self._dest:
                    logger.debug('Getting required %r', str(req))
                else:
                    logger.debug('Adding required %r', str(req))
                self._log_requirement(ws, req)
                logger.debug(
                    'We have no distributions for %s that satisfies %r.',
                    req.project_name, str(req))
                to_resolve.append(req)
                continue
            if from_environment:
                # The loop reached ``_get_dist`` on a working-set miss
                # and settled from the environment: the debug note, the
                # required-by provenance, and the picked-version record
                # (with its allow-picked-versions gate) all ride along.
                if self._dest:
                    logger.debug('Getting required %r', str(req))
                else:
                    logger.debug('Adding required %r', str(req))
                self._log_requirement(ws, req)
                if self._check_picked:
                    self._check_picked_requirement_versions(req, [dist])
            if dist not in req:
                # Oops, the "best" so far conflicts with a dependency.
                logger.info(self._version_conflict_information(req.key))
                raise VersionConflict(
                    pkg_resources.VersionConflict(dist, req), ws)
            best[req.key] = dist
            if dist not in ws:
                ws.add(dist)
            walked.append((req, dist))
            extra_requirements = _resolve_extra_requirements(
                req, dist, self._allow_unknown_extras)
            for extra_requirement in extra_requirements:
                self._requirements_and_constraints.append(
                    f"Requirement of {current_requirement}: "
                    f"{extra_requirement}")
            # Quirk mirrored from the loop: with unknown extras allowed,
            # extra_requirements holds extra *names* (str).
            queue.extend(extra_requirements)  # ty: ignore[invalid-argument-type]
        return walked

    def _install_uv(
            self,
            requirements: list[pkg_resources.Requirement],
            ws: pkg_resources.WorkingSet,
            for_buildout_run: bool,
            ) -> pkg_resources.WorkingSet:
        """Resolve ``requirements`` in one compile and graft the closure.

        The uv-mode install path: requirements already satisfied by the
        environment stay as they are, their installed dependency trees
        walk into the working set, and everything still open resolves
        in a single ``uv pip compile`` that carries the develop
        projects of the running buildout as overrides.  The pinned
        artifacts install in one batch.  Directory pins come back for
        referenced develop projects; their develop dists join the
        working set directly.
        """
        satisfied: list[tuple[pkg_resources.Requirement, pkg_resources.Distribution]] = []
        to_resolve: list[pkg_resources.Requirement] = []
        batch_names = {str(canonicalize_name(requirement.project_name))
                       for requirement in requirements}
        for requirement in requirements:
            dist = self._satisfied_uv(requirement)
            if dist is None:
                to_resolve.append(requirement)
                continue
            if dist not in ws:
                ws.add(dist)
            if self._check_picked:
                self._check_picked_requirement_versions(requirement, [dist])
            satisfied.append((requirement, dist))
        walked = self._walk_installed_deps(
            satisfied, ws, to_resolve, for_buildout_run, defer=batch_names)
        settled = [dist for _req, dist in satisfied]
        settled.extend(dist for _req, dist in walked)
        if not to_resolve:
            for dist in settled:
                self._maybe_add_setuptools(ws, dist)
            return ws
        with zc.buildout._activity('Getting distribution for %r.',
                                   str(to_resolve[0])):
            if self._dest is None:
                raise zc.buildout.UserError(
                    f"We don't have a distribution for {to_resolve[0]}\n"
                    "and can't install one in offline (no-install) mode.\n")
            for requirement in to_resolve:
                # The resolution loop announced a fetch only when the
                # environment could not satisfy the requirement at
                # all; a requirement that rides the compile only to
                # check for something newer under ``newest`` stays
                # quiet until a ``Got`` line reports a real install.
                if not _matching_dists(self._env, requirement):
                    logger.info(
                        'Getting distribution for %r.', str(requirement))
            pinned = self._uv_resolve_for_install(to_resolve, ws)
            resolved, swept = self._graft_pinned(
                pinned, to_resolve, ws, for_buildout_run)
        for requirement in to_resolve:
            # The closure covers the dependencies of compiled
            # requirements; the unknown-extra validation still belongs
            # to the requested requirement and the selected dist.
            dist = resolved.get(str(canonicalize_name(requirement.project_name)))
            if dist is not None and requirement.extras:
                _resolve_extra_requirements(
                    requirement, dist, self._allow_unknown_extras)
        for dist in settled:
            self._maybe_add_setuptools(ws, dist)
        for dist in swept:
            self._maybe_add_setuptools(ws, dist)
        return ws

    def _call_pip_install(self, spec: str, dest: str, dist: pkg_resources.Distribution) -> list[pkg_resources.Distribution | pkg_resources.DistInfoDistribution]:

        tmp = tempfile.mkdtemp(dir=dest)
        try:
            paths = call_pip_install(spec, tmp)

            dists = []
            env = Environment(paths)
            for project in env:
                dists.extend(env[project])

            if not dists:
                raise zc.buildout.UserError(f"Couldn't install: {dist}")

            if len(dists) > 1:
                logger.warning("Installing %s\n"
                            "caused multiple distributions to be installed:\n"
                            "%s\n",
                            dist, '\n'.join(map(str, dists)))
            else:
                d = dists[0]
                if d.project_name != dist.project_name:
                    logger.warning("Installing %s\n"
                                "Caused installation of a distribution:\n"
                                "%s\n"
                                "with a different project name.",
                                dist, d)
                if d.version != dist.version:
                    logger.warning("Installing %s\n"
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

    def _uv_offline(self) -> bool:
        """True when the uv seam must resolve with ``--offline``.

        The buildout offline option reaches the seam through the class
        flag; install-from-cache maps onto the same path, uv serving
        the resolve from its own cache.  A None destination keeps its
        own no-install semantics and does not imply ``--offline``.
        """
        return self._offline or self._install_from_cache

    def _obtain(self, requirement: pkg_resources.Requirement, source: int | None=None) -> pkg_resources.Distribution | None:
        if self._installer == 'uv':
            # An unset index means the default, the same fallback
            # _get_index applies for the pip index.  The class attribute
            # can hold the empty string here: the buildout entry point
            # forwards the unset option verbatim.  The harness links
            # join the configured ones verbatim, while its index only
            # plugs the PyPI hole left when the configured sources carry
            # no index of their own — both used to leak in through the
            # ambient UV_* variables the seam now scrubs.
            seam_links, seam_index = _seam_testing_sources()
            index_url = self._index_url or default_index_url
            uv_stderr: list[str] = []
            dists = _uv_available_dists(
                requirement, source, self._versions,
                [*self._links, *seam_links],
                index_url, self._prefer_final, uv_stderr,
                offline=self._uv_offline(),
                fallback_index_url=seam_index)
            self._uv_stderr_tail = _tail_text(uv_stderr)
        else:
            dists = _available_dists(self._index, requirement, source)
        if dists is None:
            # Nothing is available.
            return None

        dists = _final_dists(dists, self._prefer_final, self._final_version)

        best = _best_version_dists(dists)

        if not best:
            return None

        if len(best) == 1:
            return best[0]

        return _select_from_best(best, self._download_cache)

    def _fetch(self, dist: pkg_resources.Distribution, tmp: str, download_cache: str | None) -> pkg_resources.Distribution:
        if self._installer == 'uv' and _is_url(_dist_location(dist)):
            # uv fetches the resolved URL through its own cache when the
            # install step hands it to ``uv pip install``.
            logger.debug("Fetching %s from: %s", dist, dist.location)
            return dist
        if (download_cache
            and (realpath(os.path.dirname(_dist_location(dist))) == download_cache)
            ):
            logger.debug("Download cache has %s at: %s", dist, dist.location)
            return dist

        logger.debug("Fetching %s from: %s", dist, dist.location)
        new_location = self._index.download(_dist_location(dist), tmp)
        if (download_cache
            and (realpath(new_location) == realpath(_dist_location(dist)))
            and os.path.isfile(new_location)
            ):
            # setuptools avoids making extra copies, but we want to copy
            # to the download cache
            shutil.copy2(new_location, tmp)
            new_location = os.path.join(tmp, os.path.basename(new_location))

        return dist.clone(location=new_location)

    def _get_dist(self, requirement: pkg_resources.Requirement, ws: pkg_resources.WorkingSet) -> list[pkg_resources.Distribution | pkg_resources.DistInfoDistribution | pkg_resources.EggInfoDistribution]:
        with zc.buildout._activity('Getting distribution for %r.',
                                   str(requirement)):

            # Maybe an existing dist is already the best dist that satisfies the
            # requirement.  If not, get a link to an available distribution that
            # we could download.  The method returns a tuple with an existing
            # dist or an available dist.  Either 'dist' is None, or 'avail'
            # is None, or both are None.
            dist, avail = self._satisfied(requirement)

            if dist is None:
                dists = _fetch_new_dists(
                    requirement, avail, ws, self._dest, self._download_cache,
                    self._fetch, self._env, self._env_rescan_dest,
                    detail=self._uv_stderr_tail)

            else:
                dists = [dist]
                if dist not in ws:
                    ws.add(dist)


            if not self._install_from_cache and self._use_dependency_links:
                self._add_dependency_links_from_dists(dists)

            if self._check_picked:
                self._check_picked_requirement_versions(requirement, dists)

            return dists

    def _add_dependency_links_from_dists(self, dists: list[pkg_resources.Distribution | pkg_resources.DistInfoDistribution | pkg_resources.EggInfoDistribution]) -> None:
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

    def _check_picked_requirement_versions(self, requirement: pkg_resources.Requirement, dists: list[pkg_resources.Distribution | pkg_resources.DistInfoDistribution | pkg_resources.EggInfoDistribution]) -> None:
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

    def _maybe_add_setuptools(self, ws: pkg_resources.WorkingSet, dist: pkg_resources.DistInfoDistribution | pkg_resources.EggInfoDistribution | pkg_resources.Distribution) -> None:
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

    def _constrain(self, requirement: pkg_resources.Requirement) -> pkg_resources.Requirement:
        """Return requirement with optional [versions] constraint added."""
        canonical_name = canonicalize_name(requirement.project_name)
        constraint = self._versions.get(canonical_name)
        if constraint:
            _raise_if_junk_uv_constraint(
                self._installer, constraint, requirement)
            try:
                requirement = _constrained_requirement(constraint,
                                                       requirement)
            except IncompatibleConstraintError:
                logger.info(self._version_conflict_information(canonical_name))
                raise
        elif requirement.project_name == "setuptools":
            # Restrict setuptools to less than 82 if it is not pinned.
            # Especially when zc.buildout checks if it should upgrade itself
            # or setuptools, under some circumstances this could lead to a
            # too new setuptools version getting installed.
            # See https://github.com/buildout/buildout/issues/744
            try:
                requirement = _constrained_requirement('<82',
                                                       requirement)
            except IncompatibleConstraintError:
                logger.info(self._version_conflict_information(canonical_name))
                raise

        return requirement

    def install(self, specs: tuple[str, ...] | list[str], working_set: pkg_resources.WorkingSet | None=None) -> pkg_resources.WorkingSet:

        logger.debug('Installing %s.', repr(specs)[1:-1])
        self._requirements_and_constraints.append(
            f"Base installation request: {repr(specs)[1:-1]}")

        for_buildout_run = bool(working_set)

        requirements = _parse_requirements(specs, self._constrain)

        ws = _working_set_or_default(working_set)

        if self._installer == 'uv':
            return self._install_uv(requirements, ws, for_buildout_run)

        _fetch_requested_dists(
            requirements, ws, self._get_dist, self._maybe_add_setuptools)

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
            dist = _best_matching_dist(
                best, env, req, ws, current_requirement, for_buildout_run)
            if dist is None:
                if self._dest:
                    logger.debug('Getting required %r', str(req))
                else:
                    logger.debug('Adding required %r', str(req))
                self._log_requirement(ws, req)
                for dist in self._get_dist(req, ws):
                    self._maybe_add_setuptools(ws, dist)
            # _get_dist either raises or returns a non-empty list, so dist
            # is always set here.
            assert dist is not None
            if dist not in req:
                # Oops, the "best" so far conflicts with a dependency.
                logger.info(self._version_conflict_information(req.key))
                raise VersionConflict(
                    pkg_resources.VersionConflict(dist, req), ws)

            best[req.key] = dist

            extra_requirements = _resolve_extra_requirements(
                req, dist, self._allow_unknown_extras)

            for extra_requirement in extra_requirements:
                self._requirements_and_constraints.append(
                    f"Requirement of {current_requirement}: "
                    f"{extra_requirement}")
            # Quirk preserved from the original code: when unknown extras are
            # allowed, extra_requirements holds extra *names* (str), not
            # Requirement objects.
            requirements.extend(extra_requirements)  # ty: ignore[invalid-argument-type]

            processed[req] = True
        return ws

    def build(self, spec: str, build_ext: dict[str, str]) -> list[str]:

        requirement = self._constrain(pkg_resources.Requirement.parse(spec))

        dist, avail = self._satisfied(requirement, 1)
        if dist is not None:
            return [_dist_location(dist)]

        # Retrieve the dist:
        if avail is None:
            raise zc.buildout.UserError(
                f"Couldn't find a source distribution for "
                f"{str(requirement)!r}.")

        if self._dest is None:
            raise zc.buildout.UserError(
                f"We don't have a distribution for {requirement}\n"
                "and can't build one in offline (no-install) mode.\n")

        logger.debug('Building %r', spec)

        tmp = self._download_cache
        if tmp is None:
            tmp = tempfile.mkdtemp('get_dist')

        try:
            if self._installer == 'uv':
                # Source builds unpack the archive locally, so unlike the
                # install path the resolved URL must be downloaded first.
                dist = avail.clone(location=self._index.download(
                    _dist_location(avail), tmp))
            else:
                dist = self._fetch(avail, tmp, self._download_cache)

            build_tmp = tempfile.mkdtemp('build')
            try:
                base = _unpack_dist_for_build(dist, build_tmp)
                _write_build_ext_config(base, build_ext)

                dists = self._call_pip_install(base, self._dest, dist)

                return [_dist_location(dist) for dist in dists]
            finally:
                zc.buildout.rmtree.rmtree(build_tmp)

        finally:
            if tmp != self._download_cache:
                zc.buildout.rmtree.rmtree(tmp)

    def _fix_file_links(self, links: tuple[str, ...] | list[str]) -> Iterator[str]:
        for link in links:
            if link.startswith('file://') and link[-1] != '/' and os.path.isdir(
                    link[7:]):
                # work around excessive restriction in setuptools:
                link += '/'
            yield link

    def _log_requirement(self, ws: pkg_resources.WorkingSet, req: pkg_resources.Requirement) -> None:
        if (not logger.isEnabledFor(logging.DEBUG) and
            not Installer._store_required_by):
            # Sorting the working set and iterating over it's requirements
            # is expensive, so short circuit the work if it won't even be
            # logged.  When profiling a simple buildout with 10 parts with
            # identical and large working sets, this resulted in a
            # decrease of run time from 93.411 to 15.068 seconds, about a
            # 6 fold improvement.
            return

        sorted_dists = list(ws)
        sorted_dists.sort()
        for dist in sorted_dists:
            if req in dist.requires():
                logger.debug("  required by %s.", dist)
                req_ = str(req)
                if req_ not in Installer._required_by:
                    Installer._required_by[req_] = set()
                Installer._required_by[req_].add(str(dist.as_requirement()))

    def _final_version(self, parsed_version: Version) -> bool:
        return not parsed_version.is_prerelease


def normalize_versions(versions: Mapping[str, str]) -> dict[str, str]:
    """Return version dict with keys canonicalized.

    PyPI is case-insensitive and not all distributions are consistent in
    their own naming.  Also, there are dashes, underscores, dots...
    """
    return {canonicalize_name(k): v for (k, v) in versions.items()}


def default_versions(versions: Mapping[str, str] | None=None) -> dict[str, str]:
    old = Installer._versions
    if versions is not None:
        Installer._versions = normalize_versions(versions)
    return old

def download_cache(path: str | int | None=-1) -> str | None:
    old = Installer._download_cache
    if path != -1:
        if path:
            # The only supported non-string values are the falsy ones
            # (None/0, meaning "unset") and the -1 sentinel above.
            assert isinstance(path, str)
            path = realpath(path)
            if Installer._installer == 'uv':
                logger.warning(
                    'With installer = uv the download-cache is not'
                    ' populated; the option is deprecated'
                    ' (uv keeps downloads in its own cache).')
        Installer._download_cache = path
    return old

def install_from_cache(setting: bool | None=None) -> bool:
    old = Installer._install_from_cache
    if setting is not None:
        Installer._install_from_cache = bool(setting)
    return old

def offline(setting: bool | None=None) -> bool:
    old = Installer._offline
    if setting is not None:
        Installer._offline = bool(setting)
    return old

def prefer_final(setting: bool | None=None) -> bool:
    old = Installer._prefer_final
    if setting is not None:
        Installer._prefer_final = bool(setting)
    return old

def use_dependency_links(setting: bool | None=None) -> bool:
    old = Installer._use_dependency_links
    if setting is not None:
        Installer._use_dependency_links = bool(setting)
    return old

def index_url(setting: str | None=None) -> str | None:
    old = Installer._index_url
    if setting is not None:
        Installer._index_url = setting
    return old

def installer(setting: str | None=None) -> str:
    old = Installer._installer
    if setting is not None:
        if setting not in ('pip', 'uv'):
            raise zc.buildout.UserError(
                f"Invalid value for 'installer' option: {setting!r}."
                " Valid values are 'pip' and 'uv'.")
        _warn_if_pypirc_with_uv(setting)
        Installer._installer = setting
    return old


def _warn_if_pypirc_with_uv(setting: str) -> None:
    """Advise .netrc when uv mode meets a ~/.pypirc.

    setuptools reads index credentials from ~/.pypirc; uv does not, so a
    config that authenticated through it silently loses its credentials.
    Detection stays an existence check on purpose: no PyPIConfig port.
    """
    if setting == 'uv' and os.path.exists(os.path.expanduser('~/.pypirc')):
        logger.warning(
            'With installer = uv, credentials in ~/.pypirc are not'
            ' used; uv reads them from ~/.netrc instead.')

def allow_picked_versions(setting: bool | None=None) -> bool:
    old = Installer._allow_picked_versions
    if setting is not None:
        Installer._allow_picked_versions = bool(setting)
    return old

def store_required_by(setting: str | bool | None=None) -> bool:
    old = Installer._store_required_by
    if setting is not None:
        Installer._store_required_by = bool(setting)
    return old

def get_picked_versions() -> tuple[list[tuple[str, str]], dict[str, set[str]]]:
    picked_versions = sorted(Installer._picked_versions.items())
    required_by = Installer._required_by
    return (picked_versions, required_by)

def get_namespace_packages() -> list[tuple[str, str]]:
    return sorted(Installer._namespace_packages.items())

def install(specs: tuple[str, ...] | list[str], dest: str | None,
            links: tuple[str, ...] | list[str]=(), index: str | None=None,
            executable: str=sys.executable,
            always_unzip: bool | None=None, # Backward compat :/
            path: list[str] | None=None, working_set: pkg_resources.WorkingSet | None=None, newest: bool=True, versions: Mapping[str, str] | None=None,
            use_dependency_links: bool | None=None, allow_hosts: tuple[str, ...]=('*',),
            check_picked: bool=True,
            allow_unknown_extras: bool=False,
            ) -> pkg_resources.WorkingSet:
    assert executable == sys.executable, (executable, sys.executable)

    installer = Installer(dest, links, index, sys.executable,
                          always_unzip, path,
                          newest, versions, use_dependency_links,
                          allow_hosts=allow_hosts,
                          check_picked=check_picked,
                          allow_unknown_extras=allow_unknown_extras)
    return installer.install(specs, working_set)

buildout_and_setuptools_dists = list(install(['zc.buildout'], None,
                                             check_picked=False))
buildout_and_setuptools_path = sorted({_dist_location(d)
                                for d in buildout_and_setuptools_dists})

pip_dists = [d for d in buildout_and_setuptools_dists if d.project_name != 'zc.buildout']
pip_path = sorted({_dist_location(d) for d in pip_dists})
logger.debug('after restricting versions: pip_path %r', pip_path)
pip_pythonpath = os.pathsep.join(pip_path)

setuptools_path = pip_path
setuptools_pythonpath = pip_pythonpath


def build(spec: str, dest: str | None, build_ext: dict[str, str],
          links: tuple[str, ...] | list[str]=(), index: str | None=None,
          executable: str=sys.executable,
          path: list[str] | None=None, newest: bool=True, versions: dict[str, str] | None=None, allow_hosts: tuple[str, ...]=('*',)) -> list[str]:
    assert executable == sys.executable, (executable, sys.executable)
    installer = Installer(dest, links, index, executable,
                          True, path, newest,
                          versions, allow_hosts=allow_hosts)
    return installer.build(spec, build_ext)


# The template body lives in scripts.py; the substitution happens here,
# after the import-time resolve above defines setuptools_path, where the
# combined statement used to sit.
runsetup_template = _runsetup_template % setuptools_path
# plus deferred %%(...)r escapes consumed by a later printf substitution
# in buildout.py; a one-pass format rewrite would break the second stage.


NOT_PICKED_AND_NOT_ALLOWED = """\
Picked: {name} = {version}

The `{name}` egg does not have a version pin and `allow-picked-versions = false`.

To resolve this, add

    {name} = {version}

to the [versions] section,

OR set `allow-picked-versions = true`."""
