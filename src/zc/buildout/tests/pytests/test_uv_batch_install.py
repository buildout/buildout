"""Unit tests for install_pinned_dists: batched uv installs of a pin set."""
import logging
import os
import sys

import pkg_resources
import pytest

import zc.buildout
from zc.buildout import easy_install
from zc.buildout.easy_install import _uv_install_args
from zc.buildout.install_backend import (
    install_pinned_dists,
    make_egg_after_pip_install,
)
from zc.buildout.uv_resolve import PinnedDist


def _pin(name, version):
    return PinnedDist(
        name=name,
        version=version,
        url=f'https://example.com/packages/{name}-{version}.tar.gz',
        sha256=None,
        sdist_url=None,
        sdist_sha256=None,
    )


def _write_dist_tree(dest, project_name, version, module):
    """Materialize a fake install: a top-level module and its .dist-info.

    ``module`` may name a package inside a shared namespace
    (``zope/annotation``): the namespace directory is then shared with
    the other fake dists, the layout a batched ``uv pip install``
    produces.  METADATA, top_level.txt and RECORD are the minimum
    make_egg_after_pip_install reads; RECORD in particular must exist,
    it is read unconditionally after the dist-info moves into the egg.
    """
    distinfo = os.path.join(
        dest, f"{project_name.replace('-', '_')}-{version}.dist-info")
    os.makedirs(distinfo)
    with open(os.path.join(distinfo, 'METADATA'), 'w') as f:
        f.write('Metadata-Version: 2.1\n'
                f'Name: {project_name}\n'
                f'Version: {version}\n')
    with open(os.path.join(distinfo, 'top_level.txt'), 'w') as f:
        f.write(module.split('/')[0] + '\n')
    if '/' in module:
        entry = module + '/__init__.py'
    else:
        entry = module + '.py'
    with open(os.path.join(distinfo, 'RECORD'), 'w') as f:
        f.write(entry + ',,\n')
    target = os.path.join(dest, entry)
    if '/' in module:
        os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w') as f:
        f.write('# written by the fake uv subprocess\n')


def _record_uv_install(monkeypatch, materialize=()):
    """Stub the uv binary and ``_run_pip``; record (args, env) per call.

    The fake subprocess materializes the fake install trees named by
    ``materialize`` ((project_name, version, module) triples) into the
    tmp dest it is handed.
    """
    calls = []

    def fake_run_pip(args, env, dest, level):
        calls.append((args, env))
        for project_name, version, module in materialize:
            _write_dist_tree(dest, project_name, version, module)
        return ''

    monkeypatch.setattr(easy_install, '_uv_executable', lambda: '/uv')
    monkeypatch.setattr(easy_install, '_run_pip', fake_run_pip)
    return calls


def test_empty_pin_set_spawns_no_subprocess(monkeypatch, tmp_path):
    calls = _record_uv_install(monkeypatch)
    dest = str(tmp_path / 'eggs')
    assert install_pinned_dists([], dest) == []
    assert calls == []
    # Not even the destination directory is created for an empty set.
    assert not os.path.exists(dest)


def test_one_subprocess_with_specs_in_pin_order(monkeypatch, tmp_path):
    pins = [_pin('demo', '1.0'), _pin('other-lib', '2.0')]
    calls = _record_uv_install(monkeypatch, materialize=[
        ('demo', '1.0', 'demo'),
        ('other-lib', '2.0', 'other_lib'),
    ])
    monkeypatch.setattr(easy_install.Installer, '_index_url', None)
    dest = str(tmp_path / 'eggs')
    install_pinned_dists(pins, dest)
    assert len(calls) == 1
    args, env = calls[0]
    assert env is not os.environ
    assert args[-2:] == [pins[0].url, pins[1].url]
    assert '--no-deps' in args
    assert args[args.index('--python') + 1] == sys.executable
    # The install target is a temporary sibling inside dest.
    tmp_dest = args[args.index('-t') + 1]
    assert os.path.dirname(tmp_dest) == dest
    # The batch argv is the unchanged single-spec _uv_install_args
    # output with the remaining urls appended.
    level = logging.getLogger('zc.buildout.easy_install').getEffectiveLevel()
    expected = _uv_install_args(
        '/uv', pins[0].url, tmp_dest, False, easy_install.index_url(), level)
    assert args == expected + [pins[1].url]


def test_eggs_land_in_dest_in_pin_order(monkeypatch, tmp_path):
    pins = [_pin('demo', '1.0'), _pin('other-lib', '2.0')]
    _record_uv_install(monkeypatch, materialize=[
        ('demo', '1.0', 'demo'),
        ('other-lib', '2.0', 'other_lib'),
    ])
    dest = str(tmp_path / 'eggs')
    newdists = install_pinned_dists(pins, dest)
    assert [d.project_name for d in newdists] == ['demo', 'other-lib']
    assert [d.version for d in newdists] == ['1.0', '2.0']
    assert [d.precedence for d in newdists] == [
        pkg_resources.EGG_DIST, pkg_resources.EGG_DIST]
    eggs = sorted(os.listdir(dest))
    assert len(eggs) == 2
    assert any(e.startswith('demo-1.0') and e.endswith('.egg')
               for e in eggs)
    assert any(e.startswith('other_lib-2.0') and e.endswith('.egg')
               for e in eggs)
    # Every entry in dest is a returned egg: the temporary install
    # directory was cleaned up.
    locations = []
    for dist in newdists:
        assert dist.location is not None
        locations.append(os.path.basename(dist.location))
    assert sorted(locations) == eggs


def test_wheel_built_with_unescaped_dist_info_installs(
        monkeypatch, tmp_path):
    """Old-style wheels carry the unescaped project name in dist-info.

    Wheels built before setuptools normalized wheel filenames (or by
    backends that never did) name the dist-info directory after the
    raw project name: ``zc.recipe.egg-4.0.1.dist-info``, dots and all.
    uv unpacks it verbatim, so the install must discover the dist-info
    from the installed distribution rather than guess the escaped
    spelling (GH run 35850441994 dagger uv cells).
    """
    pins = [_pin('zc.recipe.egg', '4.0.1')]
    _record_uv_install(monkeypatch, materialize=[
        ('zc.recipe.egg', '4.0.1', 'zc_recipe_egg'),
    ])
    dest = str(tmp_path / 'eggs')
    newdists = install_pinned_dists(pins, dest)
    assert [d.project_name for d in newdists] == ['zc.recipe.egg']
    assert [d.version for d in newdists] == ['4.0.1']


def test_batched_namespace_dists_reconstruct_their_own_files(
        monkeypatch, tmp_path):
    """Two dists sharing a namespace must each keep only their own files.

    A batched ``uv pip install`` unpacks every wheel into one shared
    directory, so ``zope.annotation`` and ``zope.interface`` both live
    under a single ``zope/`` tree.  Moving the whole top-level
    directory into the first reconstructed egg leaves the second egg
    metadata-only: it cannot be imported from its own egg, the failure
    seen with real Plone pins (zope.interface 8.5 next to
    zope.annotation 6.0).
    """
    pins = [_pin('zope.annotation', '6.0'), _pin('zope.interface', '8.5')]
    _record_uv_install(monkeypatch, materialize=[
        ('zope.annotation', '6.0', 'zope/annotation'),
        ('zope.interface', '8.5', 'zope/interface'),
    ])
    dest = str(tmp_path / 'eggs')
    install_pinned_dists(pins, dest)
    eggs = [e for e in os.listdir(dest) if e.endswith('.egg')]
    assert len(eggs) == 2
    for prefix, subpackage in [('zope.annotation-6.0', 'annotation'),
                               ('zope.interface-8.5', 'interface')]:
        egg = next(e for e in eggs if e.startswith(prefix))
        zope_dir = os.path.join(dest, egg, 'zope')
        assert os.path.isdir(zope_dir)
        assert os.listdir(zope_dir) == [subpackage]
        assert os.path.isfile(
            os.path.join(zope_dir, subpackage, '__init__.py'))


def test_single_install_moves_top_level_files_beyond_record(tmp_path):
    """The single-install path keeps whole top-level moves.

    RECORD can lag the actual tree (a c extension left over, a file
    pip failed to list), so when ``dest`` holds one install the files
    named by top_level.txt move wholesale and RECORD only picks up
    leftovers.  Only batched callers share ``dest`` between dists and
    must reconstruct file-precise.
    """
    dest = tmp_path / 'dest'
    dest.mkdir()
    _write_dist_tree(str(dest), 'demo', '1.0', 'demo')
    # A file present on disk but missing from RECORD.
    (dest / 'demo-1.0.dist-info' / 'RECORD').write_text('')
    [egg_dir] = make_egg_after_pip_install(str(dest), 'demo-1.0.dist-info')
    assert os.path.isfile(os.path.join(egg_dir, 'demo.py'))


def test_batched_reconstruction_requires_record(tmp_path):
    """A batched dist without RECORD must fail loudly.

    The shared install directory leaves no safe way to pick the dist's
    own files without RECORD; a metadata-only egg would be broken at
    import time while pkg_resources still reports it as installed.
    """
    dest = tmp_path / 'dest'
    dest.mkdir()
    _write_dist_tree(str(dest), 'demo', '1.0', 'demo')
    os.remove(str(dest / 'demo-1.0.dist-info' / 'RECORD'))
    distro = next(iter(pkg_resources.find_distributions(str(dest))))
    with pytest.raises(zc.buildout.UserError):
        make_egg_after_pip_install(str(dest), 'demo-1.0.dist-info', distro)


def test_missing_dist_info_raises_user_error_naming_pin(
        monkeypatch, tmp_path):
    pins = [_pin('demo', '1.0'), _pin('other-lib', '2.0')]
    _record_uv_install(monkeypatch, materialize=[('demo', '1.0', 'demo')])
    dest = str(tmp_path / 'eggs')
    with pytest.raises(zc.buildout.UserError) as excinfo:
        install_pinned_dists(pins, dest)
    assert 'other-lib' in str(excinfo.value)
    assert '2.0' in str(excinfo.value)
    # demo was fully processed before the failure; the tmp dir inside
    # dest was still cleaned up.
    assert [e for e in os.listdir(dest) if not e.endswith('.egg')] == []
