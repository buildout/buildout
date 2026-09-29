"""Pytest fixtures and helpers for the buildout integration test suite."""
import inspect
import io
import os
import re
import shutil
import sys
from pathlib import Path

import pkg_resources
import pytest

import zc.buildout.easy_install  # ensure submodule is loaded before tests/__init__.py runs
import zc.buildout.testing
from zc.buildout.tests import add_source_dist, create_sample_eggs, normalize_bang

_TESTS_DIR = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Normalizer sets (mirroring what test_all.py's test_suite() passes)
# ---------------------------------------------------------------------------

NORMALIZERS_EASY_INSTALL = [
    (re.compile(r'http://localhost:[0-9]{4,5}/'), 'http://localhost/'),
    (re.compile(r'[0-9a-f]{32}'), '<MD5 CHECKSUM>'),
    zc.buildout.testing.normalize_path,
    zc.buildout.testing.normalize_endings,
    zc.buildout.testing.normalize_script,
    zc.buildout.testing.normalize_egg_py,
    zc.buildout.testing.drop_tomli_egg_link,
    zc.buildout.testing.normalize___pycache__,
    zc.buildout.testing.not_found,
    zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
    zc.buildout.testing.adding_find_link,
    zc.buildout.testing.easyinstall_deprecated,
    zc.buildout.testing.setuptools_deprecated,
    zc.buildout.testing.pkg_resources_deprecated,
    zc.buildout.testing.warnings_warn,
    zc.buildout.testing.ignore_root_logger,
    zc.buildout.testing.ignore_native_namespace_warning_1,
    zc.buildout.testing.ignore_native_namespace_warning_2,
    zc.buildout.testing.ignore_native_namespace_warning_3,
    zc.buildout.testing.ignore_native_namespace_warning_4,
    zc.buildout.testing.ignore_native_namespace_warning_5,
    zc.buildout.testing.drop_uv_getting_got_lines,
    zc.buildout.testing.drop_uv_install_debug_chatter,
    zc.buildout.testing.drop_uv_resolution_narrative,
    normalize_bang,
    (re.compile(r'^(\w+\.)*(Missing\w+: )'), r'\2'),
    (re.compile(r"buildout: Running \S*setup.py"), 'buildout: Running setup.py'),
    (re.compile(r'pip-\S+-'), 'pip.egg'),
    (re.compile(r'setuptools-\S+-'), 'setuptools.egg'),
    (re.compile(r'zc.buildout-\S+-'), 'zc.buildout.egg'),
    # uv's console script is uv.exe on Windows; fold argv[0] to bare uv.
    (re.compile(r'uv\.exe"'), 'uv"'),
    (re.compile(r'pip = \S+'), 'pip = 20.0.0'),
    (re.compile(r'setuptools = \S+'), 'setuptools = 0.7.99'),
    (re.compile(r'File "\S+one.py"'), 'File "one.py"'),
    (re.compile(r'We have a develop egg: (\S+) (\S+)'), r'We have a develop egg: \1 V'),
    (re.compile(r'Picked: setuptools = \S+'), 'Picked: setuptools = V'),
    (re.compile('[-d]  pip'), '-  pip'),
    (re.compile('[-d]  setuptools'), '-  setuptools'),
    (re.compile(r'\\[\\]?'), '/'),
    (re.compile(r'-q develop -mxN -d "/sample-buildout/develop-eggs'),
     '-q develop -mxN -d /sample-buildout/develop-eggs'),
    (re.compile(r'^[*]...'), '...'),
    (re.compile(r"Unused options for buildout: 'eggs' 'scripts'\."),
     "Unused options for buildout: 'scripts' 'eggs'."),
    (re.compile('NameError: global name'), 'NameError: name'),
    (re.compile('#!"python"'), '#!python'),
]

NORMALIZERS_BUILDOUT = [
    (re.compile(r'http://localhost:[0-9]{4,5}/'), 'http://localhost/'),
    zc.buildout.testing.normalize_path,
    zc.buildout.testing.normalize_endings,
    zc.buildout.testing.normalize_script,
    zc.buildout.testing.normalize_egg_py,
    zc.buildout.testing.drop_tomli_egg_link,
    zc.buildout.testing.normalize___pycache__,
    zc.buildout.testing.not_found,
    zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
    zc.buildout.testing.adding_find_link,
    zc.buildout.testing.easyinstall_deprecated,
    zc.buildout.testing.setuptools_deprecated,
    zc.buildout.testing.pkg_resources_deprecated,
    zc.buildout.testing.warnings_warn,
    zc.buildout.testing.ignore_root_logger,
    zc.buildout.testing.ignore_native_namespace_warning_1,
    zc.buildout.testing.ignore_native_namespace_warning_2,
    zc.buildout.testing.ignore_native_namespace_warning_3,
    zc.buildout.testing.ignore_native_namespace_warning_4,
    zc.buildout.testing.ignore_native_namespace_warning_5,
    zc.buildout.testing.drop_uv_getting_got_lines,
    zc.buildout.testing.drop_uv_install_debug_chatter,
    zc.buildout.testing.drop_uv_resolution_narrative,
    normalize_bang,
    (re.compile(r'__buildout_signature__ = recipes-\S+'),
     '__buildout_signature__ = recipes-SSSSSSSSSSS'),
    (re.compile(r'[-d]  setuptools-\S+[.]egg'), 'setuptools.egg'),
    (re.compile(r'zc\.buildout(-\S+)?\.egg(-link)?'), 'zc.buildout.egg'),
    (re.compile(r'creating \S*setup\.cfg'), 'creating setup.cfg'),
    (re.compile(rf'hello{os.path.sep}setup'), 'hello/setup'),
    (re.compile(r'Picked: (\S+) = \S+'), r'Picked: \1 = V.V'),
    (re.compile(r'We have a develop egg: zc\.buildout (\S+)'),
     'We have a develop egg: zc.buildout X.X.'),
    (re.compile(r'\\[\\]?'), '/'),
    (re.compile(r'WindowsError'), 'OSError'),
    (re.compile(r'pip = \S+'), 'pip = 20.0.1'),
    (re.compile(r'setuptools = \S+'), 'setuptools = 46.1.3'),
    (re.compile(r'pip-\S+-'), 'pip.egg'),
    (re.compile(r'setuptools-\S+-'), 'setuptools.egg'),
    (re.compile(r'zc\.buildout-\S+-'), 'zc.buildout.egg'),
    # Loosely match any interpreter path, like the doctest suite does:
    # the exact sys.executable string need not appear in subprocess output
    # (on Windows e.g. python3.exe vs python.exe).
    (re.compile(r'executable = [\S ]+python\S*', re.IGNORECASE),
     'executable = python'),
    (re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}'),
     'YYYY-MM-DD hh:mm:ss.dddddd'),
    (re.compile(r'\[Error 17\] Cannot create a file when that file already exists: '),
     '[Errno 17] File exists: '),
    (re.compile(r'zc\.buildout\.buildout\.MissingOption'), 'MissingOption'),
    (re.compile(r'\S+buildout\.py'), 'buildout.py'),
    (re.compile(r'line \d+'), 'line NNN'),
    (re.compile(r'\((\d+)\)(__\w+__)'), r'(NNN)\2'),
    (re.compile(r'Got zc\.recipe\.egg \S+'), 'Got zc.recipe.egg'),
    (re.compile(r'We have a develop egg: (\S+) (\S+)'), r'We have a develop egg: \1 V'),
]

# buildout_txt_env uses the same normalizers as buildout_env plus a few extras
NORMALIZERS_BUILDOUT_TXT = NORMALIZERS_BUILDOUT + [
    (re.compile(r'zc\.(buildout|recipe\.egg)\s*= >=\S+'), r'zc.\1 = >=1.99'),
]

NORMALIZERS_INCREMENT = [
    zc.buildout.testing.normalize_path,
    zc.buildout.testing.normalize_endings,
    zc.buildout.testing.normalize_script,
    zc.buildout.testing.normalize_egg_py,
    zc.buildout.testing.normalize___pycache__,
    zc.buildout.testing.not_found,
    zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
    zc.buildout.testing.adding_find_link,
    zc.buildout.testing.easyinstall_deprecated,
    zc.buildout.testing.setuptools_deprecated,
    zc.buildout.testing.pkg_resources_deprecated,
    zc.buildout.testing.warnings_warn,
    normalize_bang,
    (re.compile(r'^(\w+\.)*(Missing\w+: )'), r'\2'),
    (re.compile(r"buildout: Running \S*setup.py"), 'buildout: Running setup.py'),
    (re.compile(r'pip-\S+-'), 'pip.egg'),
    (re.compile(r'setuptools-\S+-'), 'setuptools.egg'),
    (re.compile(r'zc.buildout-\S+-'), 'zc.buildout.egg'),
    (re.compile(r'pip = \S+'), 'pip = 20.0.0'),
    (re.compile(r'setuptools = \S+'), 'setuptools = 0.7.99'),
    (re.compile(r'File "\S+one.py"'), 'File "one.py"'),
    (re.compile(r'We have a develop egg: (\S+) (\S+)'), r'We have a develop egg: \1 V'),
    (re.compile(r'Picked: setuptools = \S+'), 'Picked: setuptools = V'),
    (re.compile('[-d]  pip'), '-  pip'),
    (re.compile('[-d]  setuptools'), '-  setuptools'),
    (re.compile(r'\\[\\]?'), '/'),
    (re.compile(r'-q develop -mxN -d "/sample-buildout/develop-eggs'),
     '-q develop -mxN -d /sample-buildout/develop-eggs'),
    (re.compile(r'^[*]...'), '...'),
    (re.compile(r"Unused options for buildout: 'eggs' 'scripts'\."),
     "Unused options for buildout: 'scripts' 'eggs'."),
    (re.compile('NameError: global name'), 'NameError: name'),
    (re.compile('#!"python"'), '#!python'),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _FakeTest:
    """Minimal test object compatible with buildoutSetUp / easy_install_SetUp."""
    def __init__(self):
        self.globs = {}


@pytest.fixture(autouse=True)
def reset_easy_install_globals():
    """Reset easy_install module-level globals and tempfile.tempdir before each test."""
    import tempfile

    import zc.buildout.easy_install as _ei
    old_prefer_final = _ei.Installer._prefer_final
    old_dep_links = _ei.Installer._use_dependency_links
    old_installer = _ei.Installer._installer
    old_tempdir = tempfile.tempdir
    yield
    _ei.Installer._prefer_final = old_prefer_final
    _ei.Installer._use_dependency_links = old_dep_links
    _ei.Installer._installer = old_installer
    tempfile.tempdir = old_tempdir


@pytest.fixture(autouse=True)
def reset_zc_buildout_logger_propagation():
    """Force propagate=True on zc.buildout loggers before each test.

    Buildout._setup_logging sets propagate=False on the 'zc.buildout'
    logger, and a few ported doctests do the same on
    'zc.buildout.easy_install'; the flag then leaks across the xdist
    worker and starves every later caplog capture under the namespace:
    pytest < 9 attaches its capture handler only to the root logger, so
    records emitted behind a False flag never reach it (they surface on
    stderr via logging.lastResort instead).  The 3.9 CI leg runs pytest
    8.4.2, the newest pytest that still supports 3.9.

    Force the default at setup rather than snapshot-and-restore: the
    session-scoped sample-eggs cache runs a Buildout before the first
    function-scoped fixture of its test, so a snapshot can capture an
    already-polluted flag and would restore the pollution forever.
    """
    import logging

    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger) and (
                logger.name == 'zc.buildout'
                or logger.name.startswith('zc.buildout.')):
            logger.propagate = True
    yield


@pytest.fixture(scope='session')
def _sample_eggs_cache(tmp_path_factory):
    """Sample-eggs tree built once per test-run process (xdist worker).

    Building the sample dists (demo, demoneeded, MIXEDCASE, other,
    du_zipped, extdemo, ...) costs ~1.5-2.4s; the dists are immutable
    inputs, so they are built once and the function-scoped fixtures below
    hand each test a private copy.
    """
    cache = tmp_path_factory.mktemp('sample-eggs-cache')
    fake = _FakeTest()
    zc.buildout.testing.buildoutSetUp(fake)
    dest = str(cache / 'sample_eggs')
    os.mkdir(dest)
    os.mkdir(os.path.join(dest, 'index'))
    fake.globs['sample_eggs'] = dest
    create_sample_eggs(fake)
    add_source_dist(fake)
    # Keep the extdemo staging dir too: tests reference the 'extdemo' glob
    # (and update_extdemo rewrites it) — it lives in the fake test's tmpdir,
    # which buildoutTearDown removes, so stash a copy in the cache.
    extdemo_src = str(cache / 'extdemo-src')
    shutil.copytree(fake.globs['extdemo'], extdemo_src)
    # Restore process state (cwd, HOME, tempfile.tempdir, loggers) right
    # away; the cache tree lives outside the fake test's tmpdirs.
    zc.buildout.testing.buildoutTearDown(fake)
    return dest, extdemo_src


@pytest.fixture
def easy_install_env(_sample_eggs_cache):
    """Full sandbox: sample eggs + link server + buildout bootstrap.

    Same result as easy_install_SetUp, but the sample-eggs tree is copied
    from the per-worker session cache instead of being rebuilt per test.
    """
    fake = _FakeTest()
    zc.buildout.testing.buildoutSetUp(fake)
    sample_eggs_cache, extdemo_src = _sample_eggs_cache
    sample_eggs = fake.globs['tmpdir']('sample_eggs')
    fake.globs['sample_eggs'] = sample_eggs
    shutil.copytree(sample_eggs_cache, sample_eggs, dirs_exist_ok=True)
    extdemo = fake.globs['tmpdir']('extdemo')
    shutil.copytree(extdemo_src, extdemo, dirs_exist_ok=True)
    fake.globs['extdemo'] = extdemo
    fake.globs['link_server'] = fake.globs['start_server'](sample_eggs)
    fake.globs['update_extdemo'] = lambda: add_source_dist(fake, 1.5)
    zc.buildout.testing.install_develop('zc.recipe.egg', fake)
    fake.globs['write'] = _dedenting_write(fake.globs['write'])
    yield fake.globs
    zc.buildout.testing.buildoutTearDown(fake)


def _dedenting_write(write_fn):
    """Wrap the testing write() helper to auto-dedent multi-line string content."""
    import textwrap

    def _write(*args):
        if args and isinstance(args[-1], str) and '\n' in args[-1]:
            args = args[:-1] + (textwrap.dedent(args[-1]),)
        return write_fn(*args)

    return _write


@pytest.fixture
def buildout_env():
    """Basic buildout sandbox without sample eggs."""
    fake = _FakeTest()
    zc.buildout.testing.buildoutSetUp(fake)
    fake.globs['write'] = _dedenting_write(fake.globs['write'])
    yield fake.globs
    zc.buildout.testing.buildoutTearDown(fake)


@pytest.fixture(scope='session')
def _buildout_txt_index_cache(_sample_eggs_cache, tmp_path_factory):
    """PyPI-layout index with the zc.recipe.egg wheel, once per process.

    Contents match what buildout_txt_env used to build per test: the
    sample eggs (without the easy_install-specific 'index' subdir and
    without the extdemo sdist), reorganised into per-project directories,
    plus a freshly built zc.recipe.egg wheel.
    """
    import tempfile

    cache = tmp_path_factory.mktemp('buildout-txt-index-cache')
    index = cache / 'index'
    shutil.copytree(
        _sample_eggs_cache[0],
        str(index),
        ignore=shutil.ignore_patterns('index', 'extdemo*'),
    )

    for name in os.listdir(index):
        if '-' in name:
            pname = name.split('-')[0]
            pkg_dir = index / pname
            if not pkg_dir.exists():
                pkg_dir.mkdir()
            shutil.move(str(index / name), str(pkg_dir / name))

    dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('zc.recipe.egg'))
    assert dist is not None
    assert dist.location is not None
    (index / 'zc.recipe.egg').mkdir(exist_ok=True)
    # Build the wheel from a private copy of the source tree: running
    # ``setup.py bdist_wheel`` in the shared checkout would collide when
    # tests run in parallel (pytest-xdist workers share the filesystem).
    recipe_src = Path(tempfile.mkdtemp(prefix='zc.recipe.egg-src')) / 'src'
    shutil.copytree(
        os.path.dirname(dist.location),
        str(recipe_src),
        ignore=shutil.ignore_patterns(
            'build', 'dist', '*.egg-info', '__pycache__', '*.pyc'),
    )
    zc.buildout.testing.bdist_wheel(
        str(recipe_src),
        str(index / 'zc.recipe.egg'),
    )
    shutil.rmtree(str(recipe_src.parent))
    return str(index)


@pytest.fixture
def buildout_txt_env(_buildout_txt_index_cache):
    """Sandbox for buildout.txt / configuration.txt / etc.

    Mirrors buildout_txt_setup from test_all.py, but the index content
    (sample eggs in PyPI layout + zc.recipe.egg wheel) is copied from the
    per-worker session cache instead of being rebuilt per test.
    """
    fake = _FakeTest()
    zc.buildout.testing.buildoutSetUp(fake)

    index_url = os.environ['buildout_testing_index_url']
    index = Path(index_url[len('file://'):])
    for name in os.listdir(_buildout_txt_index_cache):
        src = Path(_buildout_txt_index_cache) / name
        if src.is_dir():
            shutil.copytree(str(src), str(index / name))
        else:
            shutil.copy2(str(src), str(index / name))
    fake.globs['sample_eggs'] = str(index)

    fake.globs['write'] = _dedenting_write(fake.globs['write'])
    sample_buildout = fake.globs['sample_buildout']
    recipes_dir = _TESTS_DIR / 'recipes'
    shutil.copytree(
        str(recipes_dir), str(Path(sample_buildout) / 'recipes'),
        # Don't let generated state from the checkout (e.g. a stray
        # egg-info from a local `pip install -e` experiment) leak
        # into the sandbox: the tests expect a pristine source tree.
        ignore=shutil.ignore_patterns('*.egg-info', '__pycache__'),
    )

    yield fake.globs
    zc.buildout.testing.buildoutTearDown(fake)


def _build_new_release(location, original_ver, version, new_releases):
    """Build one fake zc.buildout release wheel into new_releases.

    The sdist is built from a private copy of the source tree: building
    in the shared checkout rewrites src/zc.buildout.egg-info in place,
    which flips the zc.buildout develop-dist hash that part signatures
    pick up via _dists_sig in every concurrently running sample-buildout
    subprocess (pytest-xdist workers share the filesystem).  That flip
    is the intermittent test_dependencylinks_option failure.
    """
    import subprocess as _sp
    import tarfile
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        build_src = tmpdir / 'checkout'
        shutil.copytree(
            location, build_src,
            ignore=shutil.ignore_patterns(
                '.git', '.devenv', '.direnv', '.pytest_cache', '.ruff_cache',
                '.tox', '.venv', '__pycache__', '*.pyc', '*.egg-info',
                '.coverage', '.coverage.*', '.installed.cfg', 'htmlcov',
                'bin', 'build', 'dagger', 'develop-eggs', 'dist', 'doc',
                'downloads', 'eggs', 'include', 'lib', 'mutation-testing',
                'news', 'old-tutorial', 'parts', 'python_builds', 'pythons',
                'venvs', 'zc_buildout-*',
            ),
        )
        _sp.check_output(
            [sys.executable, '-m', 'build', '--sdist', str(build_src), '--outdir', str(tmpdir)],
            stderr=_sp.STDOUT,
        )
        tarball = os.listdir(tmpdir)[0]
        with tarfile.open(tmpdir / tarball) as tar:
            tar.extractall(path=tmpdir)
        os.remove(tmpdir / tarball)
        extracted = tmpdir / os.listdir(tmpdir)[0]
        setup_py = extracted / 'setup.py'
        info = setup_py.read_text()
        old_line = f'version = "{original_ver}"'
        new_line = f'version = "{version}"'
        if old_line in info:
            info = info.replace(old_line, new_line)
        setup_py.write_text(info)
        _sp.check_output(
            [sys.executable, '-m', 'build', '--wheel', str(extracted), '--outdir', new_releases],
            stderr=_sp.STDOUT,
        )


@pytest.fixture
def update_env():
    """Sandbox for update.txt: buildoutSetUp + new zc.buildout releases."""
    fake = _FakeTest()
    zc.buildout.testing.buildoutSetUp(fake)

    new_releases = fake.globs['tmpdir']('new_releases')
    fake.globs['new_releases'] = new_releases

    ws = pkg_resources.working_set
    dist = ws.find(pkg_resources.Requirement.parse('zc.buildout'))
    assert dist is not None
    assert dist.location is not None
    old_ver = dist.version
    location = Path(dist.location)
    if location.name == 'src':
        location = location.parent

    for version in ['91.0', '99.99']:
        _build_new_release(location, old_ver, version, new_releases)

    fake.globs['write'] = _dedenting_write(fake.globs['write'])
    yield fake.globs
    zc.buildout.testing.buildoutTearDown(fake)


# ---------------------------------------------------------------------------
# Output assertion helpers
# ---------------------------------------------------------------------------

def apply_normalizers(text, normalizers):
    """Apply a list of normalizers to text.

    Each item is either a (pattern, replacement) pair or a callable
    taking and returning the text (the ``drop_uv_*`` family in
    zc.buildout.testing).  Callables ran as no-ops here until the uv
    normalizers joined the lists.
    """
    for item in normalizers:
        if callable(item):
            text = item(text)
            continue
        if not isinstance(item, tuple):
            continue
        pattern, replacement = item
        text = pattern.sub(replacement, text)
    return text


def assert_output(actual, expected, normalizers=None):
    """Assert that actual output matches expected, after normalization.

    Expected may contain '...' on its own line as a wildcard matching any
    number of lines, or inline '...' matching any text on a single line.
    Uses a sequential chunk-search algorithm — no backtracking.
    """
    if normalizers:
        actual = apply_normalizers(actual, normalizers)
        expected = apply_normalizers(expected, normalizers)

    def _norm_ws(s):
        # Collapse and strip horizontal whitespace per line.
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in s.split('\n')]
        # Remove blank lines (mirrors doctest NORMALIZE_WHITESPACE: any whitespace
        # sequence in expected matches any whitespace sequence in actual).
        return '\n'.join(line for line in lines if line != '')

    actual = _norm_ws(actual).strip('\n')
    expected = _norm_ws(expected).strip('\n')

    # Split expected on standalone '...' lines (multi-line wildcards).
    # Each resulting chunk is a fixed block that must appear in order.
    chunks = re.split(r'(?m)^\.\.\.\s*$', expected)

    pos = 0
    for chunk in chunks:
        chunk = chunk.strip('\n')
        if not chunk:
            continue
        # Inline '...' within a line becomes a per-line pattern that
        # matches anything on that line but does NOT cross newlines.
        # Use [^\n]* so the match stays within a single line even with re.DOTALL.
        chunk_pattern = '\n'.join(
            re.escape(line).replace(r'\.\.\.', r'[^\n]*')
            for line in chunk.split('\n')
        )
        # re.DOTALL so '.' in escaped content matches any char; [^\n]* for
        # inline '...' already prevents newline crossing.
        m = re.search(chunk_pattern, actual[pos:], re.DOTALL)
        if not m:
            raise AssertionError(
                f"Expected chunk not found in output after position {pos}:\n"
                f"--- chunk ---\n{chunk}\n"
                f"--- actual (from pos {pos}) ---\n{actual[pos:pos+300]}\n"
                f"--- full actual ---\n{actual}"
            )
        pos += m.end()


def capture_print(fn, *args, **kwargs):
    """Call fn(*args, **kwargs), capture anything it prints, return as string."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Unit-test-only selection (--unittests-only, used by make coverage-unittests)
# ---------------------------------------------------------------------------
# The ported doctests drive buildout through the integration fixtures of
# this conftest (buildout_env, update_env, easy_install_env, ...). The unit
# tests are the tests that take no such fixture as an argument: they call
# the library directly. Builtin fixtures (tmp_path and friends) keep a test
# in the unit set, and autouse fixtures (reset_easy_install_globals) are
# not arguments, so they do not affect the selection either.


def pytest_addoption(parser):
    parser.addoption(
        "--unittests-only",
        action="store_true",
        help=(
            "deselect tests that take a fixture defined in a conftest.py "
            "as an argument; keeps the unit tests only"
        ),
    )


def _defined_in_conftest(fixturedef):
    func = getattr(fixturedef, "func", None)
    if func is None:
        return False
    source = inspect.getsourcefile(func)
    return source is not None and os.path.basename(source) == "conftest.py"


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--unittests-only"):
        return
    selected = []
    deselected = []
    for item in items:
        fixtureinfo = getattr(item, "_fixtureinfo", None)
        argnames = getattr(fixtureinfo, "argnames", ())
        fixturedefs = getattr(fixtureinfo, "name2fixturedefs", {})
        is_unittest = not any(
            _defined_in_conftest(fixturedefs[name][-1])
            for name in argnames
            if name in fixturedefs
        )
        (selected if is_unittest else deselected).append(item)
    config.hook.pytest_deselected(items=deselected)
    items[:] = selected


