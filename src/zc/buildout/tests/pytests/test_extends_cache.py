"""Unit tests for extends downloading: offline advice and cache creation."""
import pytest

import zc.buildout
from zc.buildout.annotations import SectionKey
from zc.buildout.configfiles import _open
from zc.buildout.download import Download


def test_offline_download_error_advises_extends_cache():
    download = Download({'offline': 'true'})
    with pytest.raises(zc.buildout.UserError) as excinfo:
        download('http://localhost/base.cfg')
    message = str(excinfo.value)
    assert "in offline mode" in message
    assert "extends-cache" in message
    assert "online mode" in message


def test_extends_cache_directory_is_created_on_first_use(tmp_path):
    """A configured extends-cache may not exist on the first online run.

    Extends are downloaded while the configuration is read, before the
    cache directories get created.  The documented behavior ("The
    configuration cache we specify will be created when running
    buildout", extends-cache.txt) must hold from the first run on.
    """
    extended = tmp_path / 'extended.cfg'
    extended.write_text('[buildout]\nfoo = bar\n')
    cache = tmp_path / 'extends-cache'
    root = tmp_path / 'buildout.cfg'
    root.write_text(
        '[buildout]\n'
        f'extends = file://{extended}\n'
        f'extends-cache = {cache}\n'
        'parts =\n')
    result, _user_defaults = _open(
        str(tmp_path), str(root), [], {}, {}, set(), {})
    assert cache.is_dir()
    assert len(list(cache.iterdir())) == 1
    assert result['buildout']['foo'].value == 'bar'


def test_relative_extends_cache_resolves_like_download(
        tmp_path, monkeypatch):
    """A relative extends-cache follows the config directory, not cwd.

    The Download machinery resolves a relative cache against the
    ``directory`` option; creating the raw option value relative to the
    process cwd instead would leave a junk directory behind and the
    download would still fail.
    """
    project = tmp_path / 'project'
    project.mkdir()
    extended = project / 'extended.cfg'
    extended.write_text('[buildout]\nfoo = bar\n')
    (project / 'buildout.cfg').write_text(
        '[buildout]\n'
        f'extends = file://{extended}\n'
        'extends-cache = cache\n'
        'parts =\n')
    monkeypatch.chdir(tmp_path)
    result, _user_defaults = _open(
        str(project), str(project / 'buildout.cfg'), [],
        {'directory': SectionKey(str(project), 'COMPUTED_VALUE')},
        {}, set(), {})
    assert (project / 'cache').is_dir()
    assert not (tmp_path / 'cache').exists()
    assert result['buildout']['foo'].value == 'bar'
