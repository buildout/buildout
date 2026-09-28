"""Unit tests for the pure helpers extracted from zc.buildout.easy_install."""
import distutils.errors  # ty: ignore[unresolved-import]  # runtime: setuptools distutils-precedence hook
import logging
import os
import sys
from pathlib import Path

import pkg_resources
import pytest

import zc.buildout
from zc.buildout import easy_install
from zc.buildout.easy_install import (
    BIN_SCRIPTS,
    _available_dists,
    _best_matching_dist,
    _best_version_dists,
    _cache_links_and_index,
    _collect_distutils_dev_scripts,
    _collect_req_scripts,
    _develop_dist,
    _dist_distutils_scripts,
    _dist_entry_points,
    _dist_info_dirname,
    _editable_scan_result,
    _ensure_dest_dir,
    _fetch_new_dists,
    _fetch_requested_dists,
    _final_dists,
    _find_req_dist,
    _initial_path,
    _installed_dist_name,
    _is_url,
    _lines_declare_namespace,
    _matching_dists,
    _maybe_add_no_python_version_warning,
    _move_dist_into_place,
    _move_record_leftovers,
    _move_top_levels,
    _namespace_candidate_lines,
    _parse_requirements,
    _pip_install_args,
    _prepare_links,
    _read_project_name,
    _read_record_entries,
    _read_top_levels,
    _remove_namespace_init_files,
    _remove_pip_bin_dir,
    _resolve_extra_requirements,
    _run_pip,
    _scan_editable_install,
    _script_paths,
    _script_target,
    _select_from_best,
    _select_newer_dist,
    _unpack_dist_for_build,
    _unpack_dist_to_tmp,
    _warn_missing_scripts,
    _working_set_or_default,
    _write_build_ext_config,
)

BASE_ARGS = [sys.executable, '-m', 'pip', 'install', '--no-deps', '-t', '/dest']


def test_no_index_url():
    args = _pip_install_args('demo', '/dest', False, None, logging.INFO)
    assert args == BASE_ARGS + ['-q', 'demo']


def test_remote_index_becomes_extra_index_url():
    args = _pip_install_args(
        'demo', '/dest', False, 'https://example.com/simple', logging.INFO)
    assert args == BASE_ARGS + [
        '--extra-index-url', 'https://example.com/simple', '-q', 'demo']


def test_existing_directory_index_becomes_file_uri(tmp_path):
    args = _pip_install_args('demo', '/dest', False, str(tmp_path), logging.INFO)
    expected = tmp_path.expanduser().resolve().as_uri()
    assert args == BASE_ARGS + ['--extra-index-url', expected, '-q', 'demo']


def test_missing_directory_index_is_dropped():
    args = _pip_install_args(
        'demo', '/dest', False, '/no/such/index-dir', logging.INFO)
    assert '--extra-index-url' not in args
    assert args == BASE_ARGS + ['-q', 'demo']


def test_debug_log_level_selects_verbose():
    args = _pip_install_args('demo', '/dest', False, None, logging.DEBUG)
    assert args == BASE_ARGS + ['-v', 'demo']


def test_editable_flag_goes_before_spec():
    args = _pip_install_args('demo', '/dest', True, None, logging.INFO)
    assert args[-2:] == ['-e', 'demo']


def test_spec_is_always_last():
    args = _pip_install_args(
        'demo', '/dest', True, 'https://example.com/simple', logging.DEBUG)
    assert args[-1] == 'demo'


def test_windows_drive_path_is_not_a_url():
    assert not _is_url('C:\\index')
    assert not _is_url('C:/index')


def test_http_and_file_schemes_are_urls():
    assert _is_url('https://example.com/simple')
    assert _is_url('http://example.com/simple')
    assert _is_url('file:///srv/index')


def test_bare_paths_are_not_urls():
    assert not _is_url('/srv/index')
    assert not _is_url('index')


def test_run_pip_returns_output_and_forwards_call(monkeypatch):
    calls = []

    def fake_output(args, env=None):
        calls.append((args, env))
        return 'PIP OUTPUT'

    monkeypatch.setattr(easy_install, 'get_subprocess_output', fake_output)
    env = {'PYTHONPATH': '/x'}
    assert _run_pip(['pip', 'install'], env, '/dest', logging.INFO) == 'PIP OUTPUT'
    assert calls == [(['pip', 'install'], env)]


def test_run_pip_info_level_logs_nothing(monkeypatch, caplog):
    monkeypatch.setattr(
        easy_install, 'get_subprocess_output', lambda args, env=None: 'OUT')
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _run_pip(['pip'], {}, '/dest', logging.INFO) == 'OUT'
    assert caplog.records == []


def test_run_pip_debug_logs_output_and_dest_contents(
        tmp_path, monkeypatch, caplog):
    (tmp_path / 'demo-1.0.dist-info').mkdir()
    monkeypatch.setattr(
        easy_install, 'get_subprocess_output', lambda args, env=None: 'PIP OUT')
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _run_pip(['pip'], {}, str(tmp_path), logging.DEBUG) == 'PIP OUT'
    assert 'Running pip install' in caplog.text
    assert 'PIP OUT' in caplog.text
    assert 'Pip install completed successfully.' in caplog.text
    assert '- demo-1.0.dist-info' in caplog.text


def test_run_pip_debug_with_empty_output_skips_output_line(
        tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(
        easy_install, 'get_subprocess_output', lambda args, env=None: '')
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _run_pip(['pip'], {}, str(tmp_path), logging.DEBUG) == ''
    messages = [record.getMessage() for record in caplog.records]
    assert 'Pip install completed successfully.' in messages
    assert '' not in messages


def test_scan_editable_install_without_egg_link():
    entries = [('demo', '.dist-info'), ('demo-nspkg', '.pth')]
    assert _scan_editable_install(entries) == ('', None)


def test_scan_editable_install_egg_link_without_nspkg():
    entries = [('demo', '.egg-link'), ('demo-1.0', '.dist-info')]
    assert _scan_editable_install(entries) == ('demo', None)


def test_scan_editable_install_ignores_plain_pth():
    entries = [('demo', '.egg-link'), ('easy-install', '.pth')]
    assert _scan_editable_install(entries) == ('demo', None)


def test_scan_editable_install_first_egg_link_wins():
    entries = [('first', '.egg-link'), ('second', '.egg-link')]
    assert _scan_editable_install(entries) == ('first', None)


def test_scan_editable_install_namespace_single_name():
    entries = [('foo', '.egg-link'), ('foo-nspkg', '.pth')]
    assert _scan_editable_install(entries) == ('foo', '')


def test_scan_editable_install_namespace_one_dot():
    entries = [('a.b', '.egg-link'), ('a.b-nspkg', '.pth')]
    assert _scan_editable_install(entries) == ('a.b', 'a')


def test_scan_editable_install_namespace_two_dots():
    entries = [('a.b.c', '.egg-link'), ('a.b.c-nspkg', '.pth')]
    assert _scan_editable_install(entries) == ('a.b.c', 'a\na.b')


def test_scan_editable_install_namespace_capped_at_two_dots():
    entries = [('a.b.c.d', '.egg-link'), ('a.b.c.d-nspkg', '.pth')]
    assert _scan_editable_install(entries) == ('a.b.c.d', 'a\na.b')


def test_maybe_add_no_python_version_warning_appends_from_second_call(
        monkeypatch):
    monkeypatch.delattr(
        easy_install.call_pip_install, 'displayed', raising=False)
    args = ['install']
    _maybe_add_no_python_version_warning(args)
    assert args == ['install']
    assert hasattr(easy_install.call_pip_install, 'displayed')
    _maybe_add_no_python_version_warning(args)
    assert args == ['install', '--no-python-version-warning']


def test_maybe_add_no_python_version_warning_old_pip(monkeypatch):
    monkeypatch.delattr(
        easy_install.call_pip_install, 'displayed', raising=False)
    # An entry of None in sys.modules makes the import raise ImportError.
    monkeypatch.setitem(
        sys.modules, 'pip._internal.cli.cmdoptions', None)
    args = ['install']
    _maybe_add_no_python_version_warning(args)
    _maybe_add_no_python_version_warning(args)
    assert args == ['install']
    assert not hasattr(easy_install.call_pip_install, 'displayed')


def test_editable_scan_result_without_egg_link_returns_none(caplog):
    entries = [('demo', '.dist-info'), ('demo-nspkg', '.pth')]
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _editable_scan_result(entries, 'demo') is None
    assert caplog.text == ''


def test_editable_scan_result_egg_link_returns_package_name(caplog):
    entries = [('demo', '.egg-link'), ('demo-1.0', '.dist-info')]
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _editable_scan_result(entries, 'demo') == 'demo'
    assert 'Found .egg-link file' in caplog.text
    assert 'old style namespace' not in caplog.text


def test_editable_scan_result_registers_namespaces(monkeypatch, caplog):
    monkeypatch.delitem(
        easy_install.Installer._namespace_packages, 'a.b.c', raising=False)
    entries = [('a.b.c', '.egg-link'), ('a.b.c-nspkg', '.pth')]
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _editable_scan_result(entries, 'a.b.c') == 'a.b.c'
    assert easy_install.Installer._namespace_packages['a.b.c'] == 'a\na.b'
    assert 'Found -nspkg.pth file' in caplog.text
    assert 'old style namespace' in caplog.text


def test_dist_info_dirname_returns_first_match():
    entries = [
        ('demo', '.egg-link'),
        ('demo-1.0', '.dist-info'),
        ('other-2.0', '.dist-info'),
    ]
    assert _dist_info_dirname(entries) == 'demo-1.0.dist-info'


def test_dist_info_dirname_raises_without_match():
    with pytest.raises(IndexError):
        _dist_info_dirname([('demo', '.egg-link')])


def test_installed_dist_name_reads_metadata(tmp_path):
    distinfo = tmp_path / 'demo-1.0.dist-info'
    distinfo.mkdir()
    (distinfo / 'METADATA').write_text(
        'Metadata-Version: 2.1\nName: demo\nVersion: 1.0\n')
    assert _installed_dist_name(str(distinfo)) == 'demo'


def test_installed_dist_name_missing_name_returns_none(tmp_path):
    distinfo = tmp_path / 'demo-1.0.dist-info'
    distinfo.mkdir()
    (distinfo / 'METADATA').write_text('Metadata-Version: 2.1\nVersion: 1.0\n')
    assert _installed_dist_name(str(distinfo)) is None


def _make_dist(tmp_path, requires_txt=None):
    """Build a real ``demo 1.0`` distribution from a requires.txt body."""
    egg_info = tmp_path / 'demo.egg-info'
    egg_info.mkdir()
    (egg_info / 'PKG-INFO').write_text(
        'Metadata-Version: 2.1\nName: demo\nVersion: 1.0\n')
    if requires_txt is not None:
        (egg_info / 'requires.txt').write_text(requires_txt)
    (dist,) = pkg_resources.find_distributions(str(tmp_path))
    return dist


def test_parse_requirements_parses_and_constrains_specs():
    constrained = []

    def constrain(requirement):
        constrained.append(requirement)
        return requirement

    requirements = _parse_requirements(['demo', 'other >= 1.0'], constrain)
    assert requirements == [
        pkg_resources.Requirement.parse('demo'),
        pkg_resources.Requirement.parse('other >= 1.0'),
    ]
    assert constrained == requirements


def test_parse_requirements_keeps_requirement_without_marker():
    requirements = _parse_requirements(['demo'], lambda r: r)
    assert requirements == [pkg_resources.Requirement.parse('demo')]


def test_parse_requirements_keeps_requirement_with_true_marker():
    requirements = _parse_requirements(
        ['demo; python_version >= "3.0"'], lambda r: r)
    assert requirements == [
        pkg_resources.Requirement.parse('demo; python_version >= "3.0"')]


def test_parse_requirements_drops_requirement_with_false_marker():
    constrained = []

    def constrain(requirement):
        constrained.append(requirement)
        return requirement

    requirements = _parse_requirements(
        ['demo; python_version < "1.0"'], constrain)
    assert requirements == []
    # The constraint applies only to surviving requirements.
    assert constrained == []


def test_working_set_or_default_returns_fresh_empty_set():
    ws = _working_set_or_default(None)
    assert isinstance(ws, pkg_resources.WorkingSet)
    assert ws.entries == []


def test_working_set_or_default_keeps_given_set():
    given = pkg_resources.WorkingSet([])
    assert _working_set_or_default(given) is given


def test_resolve_extra_requirements_without_extras_asks_dist(tmp_path):
    req = pkg_resources.Requirement.parse('demo')
    dist = _make_dist(tmp_path, 'dep1\ndep2 >= 1.0\n')
    assert _resolve_extra_requirements(req, dist, False) == [
        pkg_resources.Requirement.parse('dep2 >= 1.0'),
        pkg_resources.Requirement.parse('dep1'),
    ]


def test_resolve_extra_requirements_forwards_requested_extras(tmp_path):
    req = pkg_resources.Requirement.parse('demo[web]')
    dist = _make_dist(tmp_path, 'base-dep\n\n[web]\nweb-dep\n')
    # The base dependency alone would mean requires() got no extras.
    assert _resolve_extra_requirements(req, dist, False) == [
        pkg_resources.Requirement.parse('web-dep'),
        pkg_resources.Requirement.parse('base-dep'),
    ]


def test_resolve_extra_requirements_missing_extra_warns_and_intersects(
        tmp_path, caplog):
    req = pkg_resources.Requirement.parse('demo[web,nothere]')
    dist = _make_dist(tmp_path, '[web]\nweb-dep\n')
    with caplog.at_level(logging.WARNING, logger='zc.buildout.easy_install'):
        result = _resolve_extra_requirements(req, dist, True)
    assert result == ['web']
    assert "does not provide the extra 'nothere'" in caplog.text


def test_resolve_extra_requirements_missing_extra_rejected(tmp_path, caplog):
    req = pkg_resources.Requirement.parse('demo[nothere]')
    dist = _make_dist(tmp_path)
    with caplog.at_level(logging.WARNING, logger='zc.buildout.easy_install'), \
            pytest.raises(zc.buildout.UserError):
        _resolve_extra_requirements(req, dist, False)
    assert "does not provide the extra 'nothere'" in caplog.text


def test_fetch_requested_dists_fetches_each_requirement_in_order():
    calls = []
    dists = {'demo': ['d1'], 'other': ['o1', 'o2']}

    def get_dist(req, ws):
        calls.append(('get', req.key))
        return dists[req.key]

    def maybe_add_setuptools(ws, dist):
        calls.append(('setuptools?', dist))

    requirements = [
        pkg_resources.Requirement.parse('demo'),
        pkg_resources.Requirement.parse('other'),
    ]
    _fetch_requested_dists(
        requirements, pkg_resources.WorkingSet([]),
        get_dist, maybe_add_setuptools)
    assert calls == [
        ('get', 'demo'), ('setuptools?', 'd1'),
        ('get', 'other'), ('setuptools?', 'o1'), ('setuptools?', 'o2'),
    ]


def test_fetch_requested_dists_without_dists_adds_nothing():
    calls = []

    def get_dist(req, ws):
        return []

    def maybe_add_setuptools(ws, dist):
        calls.append(dist)

    _fetch_requested_dists(
        [pkg_resources.Requirement.parse('demo')],
        pkg_resources.WorkingSet([]), get_dist, maybe_add_setuptools)
    assert calls == []


def test_best_matching_dist_prefers_dist_picked_so_far(monkeypatch):
    dist = _env_dist('1.0')
    req = pkg_resources.Requirement.parse('demo')
    env = _env_with(_env_dist('2.0'))

    def boom(req, ws):
        raise AssertionError('env must not be consulted')

    monkeypatch.setattr(env, 'best_match', boom)
    assert _best_matching_dist(
        {'demo': dist}, env, req, pkg_resources.WorkingSet([]), req, True,
    ) is dist


def test_best_matching_dist_uses_environment_best_match():
    dist = _env_dist('1.0')
    req = pkg_resources.Requirement.parse('demo')
    assert _best_matching_dist(
        {}, _env_with(dist), req, pkg_resources.WorkingSet([]), req, True,
    ) is dist


def test_best_matching_dist_conflict_ignored_during_buildout_run(
        monkeypatch, caplog):
    req = pkg_resources.Requirement.parse('demo')
    env = _env_with()

    def conflict(req, ws):
        raise pkg_resources.VersionConflict('dist', 'req')

    monkeypatch.setattr(env, 'best_match', conflict)
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _best_matching_dist(
            {}, env, req, pkg_resources.WorkingSet([]), req, True) is None
    assert 'Version conflict while processing requirement' in caplog.text


def test_best_matching_dist_conflict_fatal_outside_buildout_run(monkeypatch):
    req = pkg_resources.Requirement.parse('demo')
    env = _env_with()

    def conflict(req, ws):
        raise pkg_resources.VersionConflict('dist', 'req')

    monkeypatch.setattr(env, 'best_match', conflict)
    with pytest.raises(easy_install.VersionConflict):
        _best_matching_dist(
            {}, env, req, pkg_resources.WorkingSet([]), req, False)


def _env_dist(version, precedence=pkg_resources.EGG_DIST, project_name='demo'):
    """Build a stub distribution addable to a ``pkg_resources.Environment``."""
    return pkg_resources.Distribution(
        location=f'/{project_name}-{version}.egg',
        project_name=project_name,
        version=version,
        precedence=precedence,
    )


def _env_with(*dists):
    env = pkg_resources.Environment([])
    for dist in dists:
        env.add(dist)
    return env


def _is_final(parsed_version):
    return not parsed_version.is_prerelease


def _index_with(monkeypatch, dists, obtain_result):
    """A dist-holding environment with ``obtain`` stubbed like an index."""
    env = easy_install.Environment([])
    for dist in dists:
        env.add(dist)
    monkeypatch.setattr(env, 'obtain', lambda requirement: obtain_result)
    return env


def test_available_dists_returns_none_when_index_has_nothing(monkeypatch):
    index = _index_with(monkeypatch, [], None)
    req = pkg_resources.Requirement.parse('demo')
    assert _available_dists(index, req, None) is None


def test_available_dists_keeps_only_dists_satisfying_req(monkeypatch):
    old = _env_dist('1.0')
    new = _env_dist('2.0')
    index = _index_with(monkeypatch, [old, new], old)
    req = pkg_resources.Requirement.parse('demo <2')
    assert _available_dists(index, req, None) == [old]


def test_available_dists_ignores_other_projects(monkeypatch):
    demo = _env_dist('1.0')
    other = _env_dist('1.0', project_name='other')
    index = _index_with(monkeypatch, [demo, other], demo)
    req = pkg_resources.Requirement.parse('demo')
    assert _available_dists(index, req, None) == [demo]


def test_available_dists_without_source_keeps_all_precedences(monkeypatch):
    egg = _env_dist('1.0')
    sdist = _env_dist('1.0', precedence=pkg_resources.SOURCE_DIST)
    index = _index_with(monkeypatch, [egg, sdist], egg)
    req = pkg_resources.Requirement.parse('demo')
    assert _available_dists(index, req, None) == [egg, sdist]


def test_available_dists_with_source_keeps_only_source_dists(monkeypatch):
    egg = _env_dist('1.0')
    sdist = _env_dist('1.0', precedence=pkg_resources.SOURCE_DIST)
    index = _index_with(monkeypatch, [egg, sdist], egg)
    req = pkg_resources.Requirement.parse('demo')
    assert _available_dists(index, req, 1) == [sdist]


def test_available_dists_source_without_source_dist_returns_empty(
        monkeypatch):
    egg = _env_dist('1.0')
    index = _index_with(monkeypatch, [egg], egg)
    req = pkg_resources.Requirement.parse('demo')
    assert _available_dists(index, req, 1) == []


def test_best_version_dists_empty_returns_empty():
    assert _best_version_dists([]) == []


def test_best_version_dists_single_dist_returns_it():
    dist = _env_dist('1.0')
    assert _best_version_dists([dist]) == [dist]


def test_best_version_dists_returns_highest_version():
    old = _env_dist('1.0')
    new = _env_dist('2.0')
    assert _best_version_dists([old, new]) == [new]


def test_best_version_dists_version_tie_keeps_all_in_order():
    egg = _env_dist('2.0')
    older = _env_dist('1.0')
    sdist = _env_dist('2.0', precedence=pkg_resources.SOURCE_DIST)
    assert _best_version_dists([egg, older, sdist]) == [egg, sdist]


def test_select_from_best_without_cache_prefers_egg_over_sdist():
    egg = _env_dist('2.0')
    sdist = _env_dist('2.0', precedence=pkg_resources.SOURCE_DIST)
    assert _select_from_best([sdist, egg], None) is egg
    assert _select_from_best([egg, sdist], None) is egg


def test_select_from_best_prefers_dist_in_download_cache(tmp_path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    cached = pkg_resources.Distribution(
        location=str(cache / 'demo-2.0.zip'),
        project_name='demo',
        version='2.0',
        precedence=pkg_resources.SOURCE_DIST,
    )
    egg = _env_dist('2.0')
    download_cache = easy_install.realpath(str(cache))
    assert _select_from_best([egg, cached], download_cache) is cached


def test_select_from_best_cache_miss_returns_sort_last(tmp_path):
    egg = _env_dist('2.0')
    sdist = _env_dist('2.0', precedence=pkg_resources.SOURCE_DIST)
    download_cache = easy_install.realpath(str(tmp_path))
    assert _select_from_best([egg, sdist], download_cache) is egg


def test_select_from_best_first_cached_dist_wins(tmp_path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    first = pkg_resources.Distribution(
        location=str(cache / 'demo-2.0.zip'),
        project_name='demo',
        version='2.0',
        precedence=pkg_resources.SOURCE_DIST,
    )
    second = pkg_resources.Distribution(
        location=str(cache / 'demo-2.0.egg'),
        project_name='demo',
        version='2.0',
        precedence=pkg_resources.EGG_DIST,
    )
    download_cache = easy_install.realpath(str(cache))
    assert _select_from_best([first, second], download_cache) is first


def test_matching_dists_returns_only_dists_satisfying_req():
    old = _env_dist('1.0')
    new = _env_dist('2.0')
    env = _env_with(old, new)
    req = pkg_resources.Requirement.parse('demo <2')
    assert _matching_dists(env, req) == [old]


def test_matching_dists_ignores_other_projects():
    env = _env_with(_env_dist('1.0', project_name='other'))
    req = pkg_resources.Requirement.parse('demo')
    assert _matching_dists(env, req) == []


def test_matching_dists_empty_environment_returns_empty():
    req = pkg_resources.Requirement.parse('demo')
    assert _matching_dists(_env_with(), req) == []


def test_develop_dist_returns_first_develop_egg(caplog):
    plain = _env_dist('2.0')
    develop = _env_dist('1.0', precedence=pkg_resources.DEVELOP_DIST)
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _develop_dist([plain, develop]) is develop
    assert 'We have a develop egg: demo 1.0' in caplog.text


def test_develop_dist_first_develop_egg_wins():
    first = _env_dist('1.0', precedence=pkg_resources.DEVELOP_DIST)
    second = _env_dist('2.0', precedence=pkg_resources.DEVELOP_DIST)
    assert _develop_dist([first, second]) is first


def test_develop_dist_without_develop_egg_returns_none(caplog):
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        assert _develop_dist([_env_dist('1.0'), _env_dist('2.0')]) is None
    assert 'We have a develop egg' not in caplog.text


def test_develop_dist_empty_list_returns_none():
    assert _develop_dist([]) is None


def test_final_dists_without_preference_returns_input_unchanged():
    dists = [_env_dist('1.0a1'), _env_dist('1.0')]
    assert _final_dists(dists, False, _is_final) is dists


def test_final_dists_filters_out_prereleases():
    pre = _env_dist('2.0a1')
    final = _env_dist('1.0')
    assert _final_dists([pre, final], True, _is_final) == [final]


def test_final_dists_without_any_final_returns_input_unchanged():
    dists = [_env_dist('1.0a1'), _env_dist('2.0a1')]
    assert _final_dists(dists, True, _is_final) is dists


def test_final_dists_all_final_keeps_order():
    dists = [_env_dist('2.0'), _env_dist('1.0')]
    assert _final_dists(dists, True, _is_final) == dists


def test_select_newer_dist_not_prefer_final_newer_available():
    have = _env_dist('1.0')
    available = _env_dist('2.0')
    assert _select_newer_dist(have, available, False, _is_final) is available


def test_select_newer_dist_not_prefer_final_older_available():
    have = _env_dist('2.0')
    assert _select_newer_dist(have, _env_dist('1.0'), False, _is_final) is None


def test_select_newer_dist_not_prefer_final_same_version():
    have = _env_dist('1.0')
    assert _select_newer_dist(have, _env_dist('1.0'), False, _is_final) is None


def test_select_newer_dist_prefer_final_both_final_newer_available():
    have = _env_dist('1.0')
    available = _env_dist('2.0')
    assert _select_newer_dist(have, available, True, _is_final) is available


def test_select_newer_dist_prefer_final_both_final_older_available():
    have = _env_dist('2.0')
    assert _select_newer_dist(have, _env_dist('1.0'), True, _is_final) is None


def test_select_newer_dist_prefer_final_final_beats_newer_prerelease():
    have = _env_dist('1.0')
    assert _select_newer_dist(
        have, _env_dist('2.0a1'), True, _is_final) is None


def test_select_newer_dist_prefer_final_final_beats_higher_prerelease_have():
    have = _env_dist('2.0a1')
    available = _env_dist('1.0')
    assert _select_newer_dist(have, available, True, _is_final) is available


def test_select_newer_dist_prefer_final_both_prerelease_newer_available():
    have = _env_dist('1.0a1')
    available = _env_dist('1.0a2')
    assert _select_newer_dist(have, available, True, _is_final) is available


def test_select_newer_dist_prefer_final_both_prerelease_older_available():
    have = _env_dist('1.0a2')
    assert _select_newer_dist(
        have, _env_dist('1.0a1'), True, _is_final) is None


def test_remove_namespace_init_files_removes_found_files(tmp_path, caplog):
    ns_file = tmp_path / 'ns' / '__init__.py'
    ns_file.parent.mkdir()
    ns_file.write_text('__import__("pkg_resources").declare_namespace(__name__)')
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        _remove_namespace_init_files(str(tmp_path))
    assert not ns_file.exists()
    assert f'Removed namespace __init__.py file: {ns_file}' in caplog.text


def test_remove_namespace_init_files_without_files_is_noop(
        tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(
        easy_install, 'find_namespace_init_files', lambda directory: [])
    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        _remove_namespace_init_files(str(tmp_path))
    assert 'Removed namespace __init__.py file' not in caplog.text


def _make_distinfo_with_entry_points(dest, content):
    distinfo = dest / 'demo-1.0.dist-info'
    distinfo.mkdir()
    (distinfo / 'entry_points.txt').write_text(content)


def _make_bin_dir(dest):
    bin_dir = dest / BIN_SCRIPTS
    bin_dir.mkdir()
    (bin_dir / 'demo-script').write_text('#!python')
    return bin_dir


def test_remove_pip_bin_dir_without_entry_points_keeps_bin(tmp_path):
    bin_dir = _make_bin_dir(tmp_path)
    _remove_pip_bin_dir(str(tmp_path), 'demo-1.0.dist-info')
    assert bin_dir.exists()


def test_remove_pip_bin_dir_without_scripts_keeps_bin(tmp_path):
    _make_distinfo_with_entry_points(tmp_path, '[metadata]\n')
    bin_dir = _make_bin_dir(tmp_path)
    _remove_pip_bin_dir(str(tmp_path), 'demo-1.0.dist-info')
    assert bin_dir.exists()


def test_remove_pip_bin_dir_with_console_scripts_removes_bin(tmp_path):
    _make_distinfo_with_entry_points(tmp_path, '[console_scripts]\ndemo = x\n')
    bin_dir = _make_bin_dir(tmp_path)
    _remove_pip_bin_dir(str(tmp_path), 'demo-1.0.dist-info')
    assert not bin_dir.exists()


def test_remove_pip_bin_dir_with_gui_scripts_removes_bin(tmp_path):
    _make_distinfo_with_entry_points(tmp_path, '[gui_scripts]\ndemo = x\n')
    bin_dir = _make_bin_dir(tmp_path)
    _remove_pip_bin_dir(str(tmp_path), 'demo-1.0.dist-info')
    assert not bin_dir.exists()


def test_remove_pip_bin_dir_without_bin_dir_is_noop(tmp_path):
    _make_distinfo_with_entry_points(tmp_path, '[console_scripts]\ndemo = x\n')
    _remove_pip_bin_dir(str(tmp_path), 'demo-1.0.dist-info')
    assert not (tmp_path / BIN_SCRIPTS).exists()


def test_read_project_name_returns_metadata_name(tmp_path):
    distinfo = tmp_path / 'demo-1.0.dist-info'
    distinfo.mkdir()
    (distinfo / 'METADATA').write_text(
        'Metadata-Version: 2.1\nName: Demo.Real\nVersion: 1.0\n')
    assert _read_project_name(str(tmp_path), 'demo-1.0.dist-info') == 'Demo.Real'


def test_read_project_name_without_name_returns_none(tmp_path):
    distinfo = tmp_path / 'demo-1.0.dist-info'
    distinfo.mkdir()
    (distinfo / 'METADATA').write_text('Metadata-Version: 2.1\nVersion: 1.0\n')
    assert _read_project_name(str(tmp_path), 'demo-1.0.dist-info') is None


def test_read_top_levels_without_file_returns_empty(tmp_path):
    assert list(_read_top_levels(str(tmp_path), 'demo-1.0.dist-info')) == []


def test_read_top_levels_strips_lines_and_drops_empty(tmp_path):
    distinfo = tmp_path / 'demo-1.0.dist-info'
    distinfo.mkdir()
    (distinfo / 'top_level.txt').write_text('demo\n\n  other  \n\n')
    assert list(_read_top_levels(str(tmp_path), 'demo-1.0.dist-info')) == [
        'demo', 'other']


def test_move_top_levels_moves_package_directory(tmp_path):
    dest = tmp_path / 'dest'
    egg_dir = tmp_path / 'egg'
    (dest / 'demo').mkdir(parents=True)
    (dest / 'demo' / '__init__.py').write_text('')
    (dest / 'demo.py').write_text('# shadowed module is ignored')
    egg_dir.mkdir()
    _move_top_levels(str(dest), str(egg_dir), ['demo'])
    assert (egg_dir / 'demo' / '__init__.py').exists()
    assert not (dest / 'demo').exists()
    # the package branch won, the module file stays behind
    assert (dest / 'demo.py').exists()


def test_move_top_levels_moves_module_and_pyc(tmp_path):
    dest = tmp_path / 'dest'
    egg_dir = tmp_path / 'egg'
    dest.mkdir()
    egg_dir.mkdir()
    (dest / 'demo.py').write_text('')
    (dest / 'demo.pyc').write_text('')
    _move_top_levels(str(dest), str(egg_dir), ['demo'])
    assert (egg_dir / 'demo.py').exists()
    assert (egg_dir / 'demo.pyc').exists()


def test_move_top_levels_moves_module_without_pyc(tmp_path):
    dest = tmp_path / 'dest'
    egg_dir = tmp_path / 'egg'
    dest.mkdir()
    egg_dir.mkdir()
    (dest / 'demo.py').write_text('')
    _move_top_levels(str(dest), str(egg_dir), ['demo'])
    assert (egg_dir / 'demo.py').exists()
    assert not (egg_dir / 'demo.pyc').exists()


def test_move_top_levels_missing_top_level_is_noop(tmp_path):
    dest = tmp_path / 'dest'
    egg_dir = tmp_path / 'egg'
    dest.mkdir()
    egg_dir.mkdir()
    _move_top_levels(str(dest), str(egg_dir), ['missing'])
    assert list(egg_dir.iterdir()) == []


def test_read_record_entries_returns_first_column(tmp_path):
    record = tmp_path / 'RECORD'
    record.write_text('demo/__init__.py,sha256=abc,12\ndemo.py,sha256=def,34\n')
    assert _read_record_entries(str(record)) == [
        'demo/__init__.py', 'demo.py']


def test_read_record_entries_empty_file_returns_empty(tmp_path):
    record = tmp_path / 'RECORD'
    record.write_text('')
    assert _read_record_entries(str(record)) == []


def _make_dest_and_egg(tmp_path):
    dest = tmp_path / 'dest'
    egg_dir = tmp_path / 'egg'
    dest.mkdir()
    egg_dir.mkdir()
    return dest, egg_dir


def test_move_record_leftovers_skips_compiled_files(tmp_path):
    dest, egg_dir = _make_dest_and_egg(tmp_path)
    (dest / 'demo.pyc').write_text('')
    (dest / 'demo.pyo').write_text('')
    _move_record_leftovers(str(dest), str(egg_dir), ['demo.pyc', 'demo.pyo'])
    assert (dest / 'demo.pyc').exists()
    assert (dest / 'demo.pyo').exists()
    assert list(egg_dir.iterdir()) == []


def test_move_record_leftovers_skips_entries_outside_dest(tmp_path):
    dest, egg_dir = _make_dest_and_egg(tmp_path)
    _move_record_leftovers(str(dest), str(egg_dir), ['../../evil.py'])
    assert list(egg_dir.iterdir()) == []


def test_move_record_leftovers_skips_missing_dest_entry(tmp_path):
    dest, egg_dir = _make_dest_and_egg(tmp_path)
    _move_record_leftovers(str(dest), str(egg_dir), ['missing.py'])
    assert list(egg_dir.iterdir()) == []


def test_move_record_leftovers_skips_entry_already_in_egg(tmp_path):
    dest, egg_dir = _make_dest_and_egg(tmp_path)
    (dest / 'demo.so').write_text('dest')
    (egg_dir / 'demo.so').write_text('egg')
    _move_record_leftovers(str(dest), str(egg_dir), ['demo.so'])
    assert (dest / 'demo.so').read_text() == 'dest'
    assert (egg_dir / 'demo.so').read_text() == 'egg'


def test_move_record_leftovers_moves_entry_creating_parent_dirs(tmp_path):
    dest, egg_dir = _make_dest_and_egg(tmp_path)
    nested = dest / 'demo' / 'sub'
    nested.mkdir(parents=True)
    (nested / 'mod.so').write_text('binary')
    _move_record_leftovers(str(dest), str(egg_dir), ['demo/sub/mod.so'])
    assert (egg_dir / 'demo' / 'sub' / 'mod.so').read_text() == 'binary'
    assert not (nested / 'mod.so').exists()


def test_move_record_leftovers_reuses_existing_egg_dirs(tmp_path):
    dest, egg_dir = _make_dest_and_egg(tmp_path)
    (dest / 'demo').mkdir()
    (dest / 'demo' / 'a.so').write_text('a')
    (dest / 'demo' / 'b.so').write_text('b')
    (egg_dir / 'demo').mkdir()
    _move_record_leftovers(
        str(dest), str(egg_dir), ['demo/a.so', 'demo/b.so'])
    assert (egg_dir / 'demo' / 'a.so').read_text() == 'a'
    assert (egg_dir / 'demo' / 'b.so').read_text() == 'b'


def _make_scripts_dist(tmp_path, project_name='demo',
                       entry_points_txt=None, scripts_meta=None):
    """Build a real 1.0 dist with entry-points and/or scripts metadata."""
    egg_info = tmp_path / (project_name + '.egg-info')
    egg_info.mkdir()
    (egg_info / 'PKG-INFO').write_text(
        f'Metadata-Version: 2.1\nName: {project_name}\nVersion: 1.0\n')
    if entry_points_txt is not None:
        (egg_info / 'entry_points.txt').write_text(entry_points_txt)
    if scripts_meta is not None:
        scripts_dir = egg_info / 'scripts'
        scripts_dir.mkdir()
        for name, contents in scripts_meta.items():
            # Bytes, not text: keep '\n' intact; text mode would translate
            # to os.linesep on disk.
            (scripts_dir / name).write_bytes(contents.encode('utf-8'))
    (dist,) = pkg_resources.find_distributions(str(tmp_path))
    return dist


def _ws_with(*dists):
    ws = pkg_resources.WorkingSet([])
    for dist in dists:
        ws.add(dist)
    return ws


def test_script_paths_collects_locations_and_extras():
    ws = _ws_with(
        _env_dist('1.0', project_name='aa'),
        _env_dist('2.0', project_name='bb'),
    )
    realpath = easy_install.realpath
    assert _script_paths(ws, ['/extra']) == [
        realpath('/aa-1.0.egg'), realpath('/bb-2.0.egg'), realpath('/extra')]


def test_script_paths_dedupes_preserving_order():
    ws = _ws_with(_env_dist('1.0', project_name='aa'))
    realpath = easy_install.realpath
    assert _script_paths(ws, ['/extra', '/aa-1.0.egg', '/extra']) == [
        realpath('/aa-1.0.egg'), realpath('/extra')]


def test_find_req_dist_returns_matching_dist(tmp_path):
    dist = _make_scripts_dist(tmp_path)
    assert _find_req_dist('demo', _ws_with(dist)) is dist


def test_find_req_dist_missing_raises():
    with pytest.raises(ValueError, match="Could not find requirement 'demo'"):
        _find_req_dist('demo', _ws_with())


def test_find_req_dist_excluded_marker_returns_none(tmp_path):
    dist = _make_scripts_dist(tmp_path)
    assert _find_req_dist('demo; python_version < "1.0"', _ws_with(dist)) is None


def test_find_req_dist_included_marker_still_matches(tmp_path):
    dist = _make_scripts_dist(tmp_path)
    assert _find_req_dist('demo; python_version >= "3"', _ws_with(dist)) is dist


def test_find_req_dist_non_normalized_name_matches_by_canonical(tmp_path):
    dist = _make_scripts_dist(tmp_path)
    assert _find_req_dist('Demo', _ws_with(dist)) is dist


def test_find_req_dist_falls_back_to_original_name(monkeypatch):
    ws = _ws_with()
    dist = _env_dist('1.0', project_name='other')
    looked_up = []

    def fake_find(req):
        looked_up.append(req.project_name)
        if req.project_name == 'My-Pkg':
            return dist
        return None

    monkeypatch.setattr(ws, 'find', fake_find)
    assert _find_req_dist('My_Pkg', ws) is dist
    assert looked_up == ['my-pkg', 'My-Pkg']


def test_find_req_dist_non_normalized_missing_mentions_canonical():
    with pytest.raises(ValueError, match="normalized 'my-pkg'"):
        _find_req_dist('My_Pkg', _ws_with())


def test_dist_entry_points_reads_console_scripts(tmp_path):
    dist = _make_scripts_dist(
        tmp_path, entry_points_txt='[console_scripts]\ndemo-cli = demo.cli:main\n')
    assert _dist_entry_points(dist) == [('demo-cli', 'demo.cli', 'main')]


def test_dist_entry_points_joins_dotted_attrs(tmp_path):
    dist = _make_scripts_dist(
        tmp_path, entry_points_txt='[console_scripts]\nrun = pkg.mod:cls.run\n')
    assert _dist_entry_points(dist) == [('run', 'pkg.mod', 'cls.run')]


def test_dist_entry_points_without_metadata_returns_empty(tmp_path):
    assert _dist_entry_points(_make_scripts_dist(tmp_path)) == []


def test_dist_distutils_scripts_reads_scripts_metadata(tmp_path):
    dist = _make_scripts_dist(
        tmp_path, scripts_meta={'run': '#!python\nprint(1)\n'})
    assert _dist_distutils_scripts(dist) == [('run', '#!python\nprint(1)\n')]


def test_dist_distutils_scripts_skips_dirs_and_exe(tmp_path):
    dist = _make_scripts_dist(
        tmp_path, scripts_meta={'run': '#!python\n', 'run.exe': 'MZ'})
    (tmp_path / 'demo.egg-info' / 'scripts' / '__pycache__').mkdir()
    assert _dist_distutils_scripts(dist) == [('run', '#!python\n')]


def test_dist_distutils_scripts_develop_egg_fallback(tmp_path, monkeypatch):
    dist = _make_scripts_dist(tmp_path)
    monkeypatch.setitem(
        easy_install._develop_distutils_scripts, dist.key,
        [('dev-run', '#!python\ndev\n')])
    assert _dist_distutils_scripts(dist) == [('dev-run', '#!python\ndev\n')]


def test_dist_distutils_scripts_without_any_metadata_returns_empty(tmp_path):
    dist = _make_scripts_dist(tmp_path, project_name='bare-demo')
    assert _dist_distutils_scripts(dist) == []


def test_collect_req_scripts_passes_entry_point_tuples_through():
    req = ('demo', 'demo.cli', 'main')
    entry_points, distutils_scripts = _collect_req_scripts([req], _ws_with())
    assert entry_points == [('demo', 'demo.cli', 'main')]
    assert distutils_scripts == []


def test_collect_req_scripts_collects_from_requirement_strings(tmp_path):
    dist = _make_scripts_dist(
        tmp_path,
        entry_points_txt='[console_scripts]\ndemo-cli = demo.cli:main\n',
        scripts_meta={'run': '#!python\n'})
    entry_points, distutils_scripts = _collect_req_scripts(
        ['demo'], _ws_with(dist))
    assert entry_points == [('demo-cli', 'demo.cli', 'main')]
    assert distutils_scripts == [('run', '#!python\n')]


def test_collect_req_scripts_skips_marker_excluded_requirements(tmp_path):
    dist = _make_scripts_dist(
        tmp_path,
        entry_points_txt='[console_scripts]\ndemo-cli = demo.cli:main\n',
        scripts_meta={'run': '#!python\n'})
    entry_points, distutils_scripts = _collect_req_scripts(
        ['demo; python_version < "1.0"'], _ws_with(dist))
    assert entry_points == []
    assert distutils_scripts == []


def test_collect_req_scripts_missing_requirement_raises():
    with pytest.raises(ValueError, match="Could not find requirement 'demo'"):
        _collect_req_scripts(['demo'], _ws_with())


def test_script_target_without_scripts_uses_entry_point_name(tmp_path):
    dest = str(tmp_path / 'bin')
    target = _script_target('demo', None, dest, ['/a', '/b'], False)
    assert target is not None
    sname, spath, rpsetup = target
    assert sname == os.path.join(dest, 'demo')
    assert spath == "'/a',\n  '/b'"
    assert rpsetup == ''


def test_script_target_scripts_mapping_renames_script(tmp_path):
    dest = str(tmp_path / 'bin')
    target = _script_target('demo', {'demo': 'custom'}, dest, ['/a'], False)
    assert target is not None
    sname, _, _ = target
    assert sname == os.path.join(dest, 'custom')


def test_script_target_scripts_mapping_miss_returns_none(tmp_path):
    dest = str(tmp_path / 'bin')
    assert _script_target('demo', {'other': 'x'}, dest, ['/a'], False) is None


def test_script_target_mapping_miss_returns_none_before_dest_assert():
    # A scripts-mapping miss must not trip the destination assertion.
    assert _script_target('demo', {}, None, [], False) is None


def test_script_target_without_dest_asserts():
    with pytest.raises(AssertionError):
        _script_target('demo', None, None, [], False)


def test_script_target_relative_paths_builds_base_setup(tmp_path):
    dest_dir = tmp_path / 'bin'
    egg = tmp_path / 'eggs' / 'demo.egg'
    target = _script_target(
        'demo', None, str(dest_dir), [str(egg)], str(tmp_path))
    assert target is not None
    sname, spath, rpsetup = target
    assert sname == os.path.join(str(dest_dir), 'demo')
    assert spath == f"join(base, {os.path.join('eggs', 'demo.egg')!r})"
    assert rpsetup == (
        easy_install.relative_paths_setup + 'base = os.path.dirname(base)\n')


def test_warn_missing_scripts_without_mapping_is_silent(caplog):
    with caplog.at_level(logging.WARNING, logger='zc.buildout.easy_install'):
        _warn_missing_scripts(None, [])
    assert caplog.records == []


def test_warn_missing_scripts_known_names_are_silent(caplog):
    with caplog.at_level(logging.WARNING, logger='zc.buildout.easy_install'):
        _warn_missing_scripts({'demo': 'demo'}, ['demo'])
    assert caplog.records == []


def test_warn_missing_scripts_same_name_warns(caplog):
    with caplog.at_level(logging.WARNING, logger='zc.buildout.easy_install'):
        _warn_missing_scripts({'missing': 'missing'}, ['demo'])
    assert ("Could not generate script 'missing' as it is not defined "
            'in the egg entry points.') in caplog.text


def test_warn_missing_scripts_renamed_warns_with_target(caplog):
    with caplog.at_level(logging.WARNING, logger='zc.buildout.easy_install'):
        _warn_missing_scripts({'missing': 'target'}, ['demo'])
    assert ("Could not generate script 'missing' as script 'target' is not "
            'defined in the egg entry points.') in caplog.text


def test_fetch_new_dists_requires_a_dest():
    req = pkg_resources.Requirement.parse('demo')
    with pytest.raises(zc.buildout.UserError) as exc:
        _fetch_new_dists(
            req, _env_dist('1.0'), pkg_resources.WorkingSet([]),
            None, None, lambda dist, tmp, cache: dist,
            pkg_resources.Environment([]), lambda: None)
    assert "We don't have a distribution for demo" in str(exc.value)
    assert "offline (no-install) mode" in str(exc.value)


def test_fetch_new_dists_without_available_raises_missing():
    req = pkg_resources.Requirement.parse('demo')
    ws = pkg_resources.WorkingSet([])
    with pytest.raises(easy_install.MissingDistribution):
        _fetch_new_dists(
            req, None, ws, '/dest', None,
            lambda dist, tmp, cache: dist,
            pkg_resources.Environment([]), lambda: None)


def test_fetch_new_dists_fetches_registers_and_rescans(
        tmp_path, monkeypatch, caplog):
    req = pkg_resources.Requirement.parse('demo')
    avail = _env_dist('1.0')
    moved = _env_dist('1.0')
    ws = pkg_resources.WorkingSet([])
    fetched = []
    events = []
    env = pkg_resources.Environment([])

    def fetch(dist, tmp, download_cache):
        fetched.append((dist, tmp, download_cache))
        return dist

    def move(dist, dest):
        events.append(('move', dist, dest))
        return moved

    def best_match(req_arg, ws_arg):
        events.append(('best_match', req_arg, ws_arg))
        return moved

    monkeypatch.setattr(easy_install, '_move_to_eggs_dir_and_compile', move)
    monkeypatch.setattr(env, 'best_match', best_match)

    with caplog.at_level(logging.INFO, logger='zc.buildout.easy_install'):
        dists = _fetch_new_dists(
            req, avail, ws, '/dest', None, fetch, env,
            lambda: events.append(('rescan',)))

    assert dists == [moved]
    (dist, tmp, download_cache), = fetched
    assert dist is avail
    assert download_cache is None
    assert not os.path.exists(tmp)  # temporary directory removed
    assert events == [
        ('move', avail, '/dest'),
        ('rescan',),
        ('best_match', req, ws),
    ]
    assert moved in ws
    assert 'Getting distribution for' in caplog.text
    assert 'Got demo 1.0.' in caplog.text


def test_fetch_new_dists_failed_download_raises(tmp_path, monkeypatch):
    req = pkg_resources.Requirement.parse('demo')
    avail = _env_dist('1.0')
    with pytest.raises(zc.buildout.UserError) as exc:
        _fetch_new_dists(
            req, avail, pkg_resources.WorkingSet([]), '/dest', None,
            lambda dist, tmp, cache: None,
            pkg_resources.Environment([]), lambda: None)
    assert "Couldn't download distribution" in str(exc.value)


def test_fetch_new_dists_uses_download_cache_as_tmp(tmp_path, monkeypatch):
    req = pkg_resources.Requirement.parse('demo')
    avail = _env_dist('1.0')
    moved = _env_dist('1.0')
    fetched = []
    cache = str(tmp_path)

    def fetch(dist, tmp, download_cache):
        fetched.append((tmp, download_cache))
        return dist

    monkeypatch.setattr(
        easy_install, '_move_to_eggs_dir_and_compile',
        lambda dist, dest: moved)

    dists = _fetch_new_dists(
        req, avail, pkg_resources.WorkingSet([]), '/dest', cache, fetch,
        pkg_resources.Environment([]), lambda: None)

    assert dists == [moved]
    assert fetched == [(cache, cache)]
    assert os.path.isdir(cache)  # download cache is not removed


def test_fetch_new_dists_skips_ws_add_for_present_dist(tmp_path, monkeypatch):
    req = pkg_resources.Requirement.parse('demo')
    avail = _env_dist('1.0')
    moved = _env_dist('1.0')
    ws = pkg_resources.WorkingSet([])
    ws.add(moved)
    added = []
    monkeypatch.setattr(
        ws, 'add', lambda dist, replace=False: added.append(dist))
    monkeypatch.setattr(
        easy_install, '_move_to_eggs_dir_and_compile',
        lambda dist, dest: moved)

    dists = _fetch_new_dists(
        req, avail, ws, '/dest', str(tmp_path),
        lambda dist, tmp, cache: dist,
        pkg_resources.Environment([]), lambda: None)

    assert dists == [moved]
    assert added == []


def test_cache_links_and_index_passthrough_without_install_from_cache():
    links = ['https://example.com/simple']
    assert _cache_links_and_index(False, '/cache', links, '/index') == (
        links, '/index')


def test_cache_links_and_index_requires_a_download_cache():
    with pytest.raises(ValueError) as exc:
        _cache_links_and_index(True, None, ['x'], '/index')
    assert "install_from_cache set to true with no download cache" in str(
        exc.value)


def test_cache_links_and_index_cache_becomes_only_index():
    assert _cache_links_and_index(True, '/cache', ['x'], '/index') == (
        (), 'file:///cache')


def test_prepare_links_without_download_cache():
    assert _prepare_links(['a', 'b'], None, iter) == ['a', 'b']


def test_prepare_links_inserts_download_cache_first():
    assert _prepare_links(['a'], '/cache', iter) == ['/cache', 'a']


def test_prepare_links_does_not_duplicate_download_cache():
    assert _prepare_links(['/cache', 'a'], '/cache', iter) == ['/cache', 'a']


def test_prepare_links_applies_the_fixer():
    def fix(links):
        for link in links:
            yield link + '/'

    assert _prepare_links(('a',), None, fix) == ['a/']


def test_initial_path_none_gives_buildout_and_setuptools():
    assert _initial_path(None) == easy_install.buildout_and_setuptools_path


def test_initial_path_appends_buildout_and_setuptools():
    assert _initial_path(['/x']) == (
        ['/x'] + easy_install.buildout_and_setuptools_path)


def test_initial_path_copies_the_given_path():
    path = ['/x']
    result = _initial_path(path)
    path.append('/y')
    assert '/y' not in result


def test_ensure_dest_dir_creates_nested_directories(tmp_path):
    dest = str(tmp_path / 'a' / 'b')
    _ensure_dest_dir(dest)
    assert os.path.isdir(dest)


def test_ensure_dest_dir_accepts_existing_directory(tmp_path):
    _ensure_dest_dir(str(tmp_path))
    assert os.path.isdir(str(tmp_path))


def test_ensure_dest_dir_reraises_when_directory_still_missing(
        tmp_path, monkeypatch):
    def fail_makedirs(path):
        raise OSError('boom')

    monkeypatch.setattr(os, 'makedirs', fail_makedirs)
    with pytest.raises(OSError):
        _ensure_dest_dir(str(tmp_path / 'missing'))


def test_ensure_dest_dir_swallows_error_for_existing_directory(
        tmp_path, monkeypatch):
    def fail_makedirs(path):
        raise OSError('File exists')

    monkeypatch.setattr(os, 'makedirs', fail_makedirs)
    _ensure_dest_dir(str(tmp_path))  # no raise


def test_unpack_dist_to_tmp_copies_prebuilt_directory(tmp_path):
    location = tmp_path / 'demo-1.0.egg'
    location.mkdir()
    (location / 'marker').write_text('x')
    tmp_dest = tmp_path / 'tmp'
    tmp_dest.mkdir()
    dist = _env_dist('1.0')
    dist.location = str(location)

    tmp_loc = _unpack_dist_to_tmp(dist, str(tmp_dest))

    assert tmp_loc == str(tmp_dest / 'demo-1.0.egg')
    assert (tmp_dest / 'demo-1.0.egg' / 'marker').read_text() == 'x'


def test_unpack_dist_to_tmp_uses_registered_unpacker(
        tmp_path, monkeypatch, caplog):
    unpacked = []

    def fake_unpacker(location, tmp_loc):
        unpacked.append((location, tmp_loc))
        os.mkdir(tmp_loc)

    monkeypatch.setitem(easy_install.UNPACKERS, '.gz', fake_unpacker)
    dist = _env_dist('1.0')
    dist.location = '/x/demo-1.0.tar.gz'

    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        tmp_loc = _unpack_dist_to_tmp(dist, str(tmp_path))

    assert tmp_loc == str(tmp_path / 'demo-1.0.egg')  # .tar.gz suffix trimmed
    assert unpacked == [('/x/demo-1.0.tar.gz', tmp_loc)]
    assert 'Calling unpacker for .gz' in caplog.text


def test_unpack_dist_to_tmp_falls_back_to_pip(tmp_path, monkeypatch, caplog):
    installed = []

    def fake_pip_install(location, tmp_dest):
        installed.append((location, tmp_dest))
        return [os.path.join(tmp_dest, 'demo-1.0.egg')]

    monkeypatch.setattr(easy_install, 'call_pip_install', fake_pip_install)
    dist = _env_dist('1.0')
    dist.location = '/x/demo-1.0.zip'

    with caplog.at_level(logging.DEBUG, logger='zc.buildout.easy_install'):
        tmp_loc = _unpack_dist_to_tmp(dist, str(tmp_path))

    assert tmp_loc == str(tmp_path / 'demo-1.0.egg')
    assert installed == [('/x/demo-1.0.zip', str(tmp_path))]
    assert 'Calling pip install for .zip' in caplog.text


def test_move_dist_into_place_renames_and_returns_new_dist(
        tmp_path, monkeypatch):
    tmp_loc = tmp_path / 'tmp' / 'demo-1.0.egg'
    tmp_loc.mkdir(parents=True)
    dest = tmp_path / 'eggs'
    dest.mkdir()
    newdist = _env_dist('1.0')
    looked_up = []
    monkeypatch.setattr(
        easy_install, '_get_matching_dist_in_location',
        lambda dist, location: looked_up.append(location) or newdist)

    result = _move_dist_into_place(_env_dist('1.0'), str(tmp_loc), str(dest))

    assert result is newdist
    assert looked_up == [str(dest / 'demo-1.0.egg')]
    assert not tmp_loc.exists()
    assert (dest / 'demo-1.0.egg').is_dir()


def test_move_dist_into_place_without_matching_dist_raises(
        tmp_path, monkeypatch):
    tmp_loc = tmp_path / 'tmp' / 'demo-1.0.egg'
    tmp_loc.mkdir(parents=True)
    dest = tmp_path / 'eggs'
    dest.mkdir()
    monkeypatch.setattr(
        easy_install, '_get_matching_dist_in_location',
        lambda dist, location: None)

    with pytest.raises(AssertionError) as exc:
        _move_dist_into_place(_env_dist('1.0'), str(tmp_loc), str(dest))
    assert 'has no distribution for demo 1.0' in str(exc.value)


def test_move_dist_into_place_rename_failure_reraises_when_newloc_missing(
        tmp_path, monkeypatch, caplog):
    def fail_rename(src, dst):
        raise OSError('boom')

    monkeypatch.setattr(os, 'rename', fail_rename)
    with caplog.at_level(logging.ERROR, logger='zc.buildout.easy_install'), \
            pytest.raises(OSError):
        _move_dist_into_place(
            _env_dist('1.0'), str(tmp_path / 'demo-1.0.egg'),
            str(tmp_path / 'eggs'))
    assert 'Moving/renaming egg for demo 1.0' in caplog.text
    assert 'does not exist' in caplog.text


def test_move_dist_into_place_accepts_dist_added_in_parallel(
        tmp_path, monkeypatch, caplog):
    def fail_rename(src, dst):
        raise OSError('boom')

    dest = tmp_path / 'eggs'
    (dest / 'demo-1.0.egg').mkdir(parents=True)
    newdist = _env_dist('1.0')
    monkeypatch.setattr(os, 'rename', fail_rename)
    monkeypatch.setattr(
        easy_install, '_get_matching_dist_in_location',
        lambda dist, location: newdist)

    with caplog.at_level(logging.WARNING, logger='zc.buildout.easy_install'):
        result = _move_dist_into_place(
            _env_dist('1.0'), str(tmp_path / 'tmp' / 'demo-1.0.egg'),
            str(dest))

    assert result is newdist
    assert 'unexpectedly already exists' in caplog.text


def test_move_dist_into_place_reraises_for_wrong_package_at_newloc(
        tmp_path, monkeypatch, caplog):
    def fail_rename(src, dst):
        raise OSError('boom')

    dest = tmp_path / 'eggs'
    (dest / 'demo-1.0.egg').mkdir(parents=True)
    monkeypatch.setattr(os, 'rename', fail_rename)
    monkeypatch.setattr(
        easy_install, '_get_matching_dist_in_location',
        lambda dist, location: None)

    with caplog.at_level(logging.ERROR, logger='zc.buildout.easy_install'), \
            pytest.raises(OSError):
        _move_dist_into_place(
            _env_dist('1.0'), str(tmp_path / 'tmp' / 'demo-1.0.egg'),
            str(dest))
    assert 'exists, but has no distribution for demo 1.0' in caplog.text


def _build_dist(tmp_path, project_name='demo', version='1.0'):
    """Distribution whose location is an on-disk-style path under tmp_path."""
    return pkg_resources.Distribution(
        location=str(tmp_path / f'{project_name}-{version}.egg'),
        project_name=project_name,
        version=version,
    )


def test_unpack_dist_for_build_returns_build_tmp_for_top_level_setup(
        tmp_path, monkeypatch):
    calls = []

    def fake_unpack(filename, extract_dir):
        calls.append((filename, extract_dir))
        Path(extract_dir, 'setup.py').write_text(
            'from setuptools import setup\n')

    dist = _build_dist(tmp_path)
    build_tmp = tmp_path / 'unpacked'
    build_tmp.mkdir()
    monkeypatch.setattr(
        'setuptools.archive_util.unpack_archive', fake_unpack)

    base = _unpack_dist_for_build(dist, str(build_tmp))

    assert base == str(build_tmp)
    assert calls == [(dist.location, str(build_tmp))]


def test_unpack_dist_for_build_finds_setup_in_single_subdir(
        tmp_path, monkeypatch):
    def fake_unpack(filename, extract_dir):
        Path(extract_dir, 'demo-1.0').mkdir()
        Path(extract_dir, 'demo-1.0', 'setup.py').write_text('')

    build_tmp = tmp_path / 'unpacked'
    build_tmp.mkdir()
    monkeypatch.setattr(
        'setuptools.archive_util.unpack_archive', fake_unpack)

    base = _unpack_dist_for_build(_build_dist(tmp_path), str(build_tmp))

    assert base == os.path.join(str(build_tmp), 'demo-1.0')


def test_unpack_dist_for_build_warns_and_keeps_base_without_setup(
        tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(
        'setuptools.archive_util.unpack_archive',
        lambda filename, extract_dir: None)
    build_tmp = tmp_path / 'unpacked'
    build_tmp.mkdir()

    with caplog.at_level(logging.WARNING, logger='zc.buildout.easy_install'):
        base = _unpack_dist_for_build(_build_dist(tmp_path), str(build_tmp))

    assert base == str(build_tmp)
    assert ("Couldn't find a setup script to build in demo-1.0.egg"
            in caplog.text)
    assert 'Trying pip install anyway' in caplog.text


def test_unpack_dist_for_build_raises_on_multiple_setups(
        tmp_path, monkeypatch):
    def fake_unpack(filename, extract_dir):
        Path(extract_dir, 'one').mkdir()
        Path(extract_dir, 'one', 'setup.py').write_text('')
        Path(extract_dir, 'two').mkdir()
        Path(extract_dir, 'two', 'setup.py').write_text('')

    build_tmp = tmp_path / 'unpacked'
    build_tmp.mkdir()
    monkeypatch.setattr(
        'setuptools.archive_util.unpack_archive', fake_unpack)

    with pytest.raises(distutils.errors.DistutilsError) as exc:
        _unpack_dist_for_build(_build_dist(tmp_path), str(build_tmp))
    assert 'Multiple setup scripts in demo-1.0.egg' in str(exc.value)


def test_write_build_ext_config_creates_missing_setup_cfg(tmp_path):
    base = tmp_path / 'src'
    base.mkdir()
    include = str(tmp_path / 'include')

    _write_build_ext_config(str(base), {'include-dirs': include})

    content = (base / 'setup.cfg').read_text()
    assert '[build_ext]' in content
    assert 'include-dirs' in content
    assert include in content


def test_write_build_ext_config_keeps_existing_setup_cfg(tmp_path):
    base = tmp_path / 'src'
    base.mkdir()
    setup_cfg = base / 'setup.cfg'
    setup_cfg.write_text('[metadata]\nname = demo\n')
    include = str(tmp_path / 'include')

    _write_build_ext_config(str(base), {'include-dirs': include})

    content = setup_cfg.read_text()
    assert 'name = demo' in content
    assert '[build_ext]' in content
    assert include in content


def test_namespace_candidate_lines_filters_blank_and_comment_lines(tmp_path):
    init = tmp_path / '__init__.py'
    init.write_text(
        '# See http://peak.telecommunity.com/DevCenter/setuptools\n'
        '\n'
        '    # indented comment\n'
        '__import__("pkg_resources").declare_namespace(__name__)\n'
        '   \n'
    )

    assert _namespace_candidate_lines(init) == [
        '__import__("pkg_resources").declare_namespace(__name__)\n']


def test_namespace_candidate_lines_keeps_indented_code_verbatim(tmp_path):
    init = tmp_path / '__init__.py'
    init.write_text('try:\n    pass\n')

    assert _namespace_candidate_lines(init) == ['try:\n', '    pass\n']


def test_lines_declare_namespace_one_liner_pkg_resources():
    assert _lines_declare_namespace(
        ["__import__('pkg_resources').declare_namespace(__name__)\n"])


def test_lines_declare_namespace_multiline_pkg_resources():
    assert _lines_declare_namespace([
        'try:\n',
        '    __import__("pkg_resources").declare_namespace(__name__)\n',
        'except ImportError:\n',
        '    from pkgutil import extend_path\n',
        '    __path__ = extend_path(__path__, __name__)\n',
    ])


def test_lines_declare_namespace_pkgutil_extend_path():
    assert _lines_declare_namespace([
        'from pkgutil import extend_path\n',
        '__path__ = extend_path(__path__, __name__)\n',
    ])


def test_lines_declare_namespace_requires_marker_order():
    # A second marker appearing before the first one does not count.
    assert not _lines_declare_namespace([
        'declare_namespace\n',
        'pkg_resources\n',
    ])


def test_lines_declare_namespace_no_declaration():
    assert not _lines_declare_namespace(['import os\n', 'x = 1\n'])
    assert not _lines_declare_namespace([])


def _marked_script(tmp_path, directory, filename, actual_name, content):
    """Write a marked dev script pointing at an actual script file."""
    actual = tmp_path / actual_name
    actual.write_text(content)
    (directory / filename).write_text(
        f"# EASY-INSTALL-DEV-SCRIPT\n__file__ = '{actual}'\n")


def test_collect_distutils_dev_scripts_reads_actual_script(tmp_path):
    directory = tmp_path / 'dev'
    directory.mkdir()
    _marked_script(tmp_path, directory, 'run', 'actual.py', 'print(1)\n')

    found = _collect_distutils_dev_scripts(
        str(directory), os.listdir(str(directory)))

    assert found == [['run', 'print(1)\n']]


def test_collect_distutils_dev_scripts_skips_exe_and_unmarked_files(tmp_path):
    directory = tmp_path / 'dev'
    directory.mkdir()
    (directory / 'run.exe').write_text('EASY-INSTALL-DEV-SCRIPT')
    (directory / 'plain').write_text('print(1)\n')

    assert _collect_distutils_dev_scripts(
        str(directory), os.listdir(str(directory))) == []


def test_collect_distutils_dev_scripts_skips_directories(tmp_path):
    directory = tmp_path / 'dev'
    (directory / 'EASY-INSTALL-DEV-SCRIPT-dir').mkdir(parents=True)

    assert _collect_distutils_dev_scripts(
        str(directory), os.listdir(str(directory))) == []


def test_collect_distutils_dev_scripts_ignores_marker_without_dunder_file(
        tmp_path):
    directory = tmp_path / 'dev'
    directory.mkdir()
    (directory / 'run').write_text('# EASY-INSTALL-DEV-SCRIPT\nprint(1)\n')

    assert _collect_distutils_dev_scripts(
        str(directory), os.listdir(str(directory))) == []


def test_collect_distutils_dev_scripts_collects_in_dir_contents_order(
        tmp_path):
    directory = tmp_path / 'dev'
    directory.mkdir()
    _marked_script(tmp_path, directory, 'run2', 'a2.py', 'two\n')
    _marked_script(tmp_path, directory, 'run1', 'a1.py', 'one\n')
    contents = sorted(os.listdir(str(directory)))

    found = _collect_distutils_dev_scripts(str(directory), contents)

    assert found == [['run1', 'one\n'], ['run2', 'two\n']]


def test_detect_distutils_scripts_records_scripts_when_egg_link_present(
        tmp_path, monkeypatch):
    scripts = {}
    monkeypatch.setattr(easy_install, '_develop_distutils_scripts', scripts)
    directory = tmp_path / 'dev'
    directory.mkdir()
    (directory / 'demo.egg-link').write_text('link\n')
    _marked_script(tmp_path, directory, 'run', 'actual.py', 'print(1)\n')

    easy_install._detect_distutils_scripts(str(directory))

    assert scripts == {'demo': [['run', 'print(1)\n']]}


def test_detect_distutils_scripts_ignores_directory_without_egg_link(
        tmp_path, monkeypatch):
    scripts = {}
    monkeypatch.setattr(easy_install, '_develop_distutils_scripts', scripts)
    directory = tmp_path / 'dev'
    directory.mkdir()
    _marked_script(tmp_path, directory, 'run', 'actual.py', 'print(1)\n')

    easy_install._detect_distutils_scripts(str(directory))

    assert scripts == {}


def test_eggify_offline_dist_tolerates_path_spelling_differences(tmp_path):
    """The offline env scan must eggify wheel-style eggs however spelled.

    _get_dest_dist_paths globs the configured path entries verbatim, while
    pkg_resources normalizes scanned locations (realpath everywhere, plus
    normcase case-folding on Windows). When the spellings diverge — a
    symlinked path entry here, a case-folded drive letter on Windows — the
    container membership check must still recognize the dist as installed,
    or offline runs treat it as a develop dist and part signatures flip
    from egg basename to directory hash (gh run 35217914643:
    recipe_upgrade reinstalling instead of updating on Windows).
    """
    real_eggs = tmp_path / 'real-eggs'
    dist_info = real_eggs / 'recipe-1-py3.10.egg' / 'recipe-1.dist-info'
    dist_info.mkdir(parents=True)
    (dist_info / 'METADATA').write_text(
        'Metadata-Version: 2.1\nName: recipe\nVersion: 1\n')
    linked_eggs = tmp_path / 'linked-eggs'
    linked_eggs.symlink_to(real_eggs)

    installer = easy_install.Installer(
        None, (), None, sys.executable, path=[str(linked_eggs)])
    env = installer._make_env()

    [dist] = env['recipe']
    assert dist.precedence == pkg_resources.EGG_DIST


def test_get_subprocess_output_failure_is_user_error_with_output():
    with pytest.raises(zc.buildout.UserError) as excinfo:
        easy_install.get_subprocess_output([
            sys.executable, '-c',
            'import sys; sys.stdout.write("the build said boom\\n");'
            ' sys.exit(3)'])
    message = str(excinfo.value)
    assert "Failed to run command" in message
    assert "the build said boom" in message
