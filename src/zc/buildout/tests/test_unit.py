from packaging.tags import sys_tags
from pathlib import Path
from pkg_resources import Requirement
from setuptools.wheel import Wheel
from zc.buildout._package_index import distros_for_filename
from zc.buildout._package_index import distros_for_url
from zc.buildout._package_index import wheel_tag_rank
from zc.buildout.easy_install import _dist_sort_key
from zc.buildout.easy_install import Installer
from zc.buildout.easy_install import realpath

import os
import tempfile
import unittest


_oneliner1 = """import__('pkg_resources').declare_namespace(__name__)"""
_oneliner2 = """__path__ = __import__("pkgutil").extend_path(__path__, __name__)"""
_pkg_resources = """from pkg_resources import declare_namespace

declare_namespace(__name__)
"""
_pkgutil = """from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
"""
_both = """# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
    __import__("pkg_resources").declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path

    __path__ = extend_path(__path__, __name__)
"""
_comments = """# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
# try:
#     __import__("pkg_resources").declare_namespace(__name__)
# except ImportError:
#     from pkgutil import extend_path
#
#     __path__ = extend_path(__path__, __name__)
"""


class TestFunctions(unittest.TestCase):
    """Test case for some functions."""

    def test_check_namespace_init_file_and_find_namespace_init_files(self):
        from zc.buildout.easy_install import check_namespace_init_file
        from zc.buildout.easy_install import find_namespace_init_files

        with tempfile.TemporaryDirectory() as package_dir:
            init = Path(package_dir) / "__init__.py"
            str_init = str(init)

            # Test with empty __init__.py file
            init.write_text("")
            self.assertFalse(check_namespace_init_file(init))
            self.assertListEqual(find_namespace_init_files(package_dir), [])

            # Test with non-empty __init__.py file
            init.write_text("# Non-empty init file")
            self.assertFalse(check_namespace_init_file(init))
            self.assertListEqual(find_namespace_init_files(package_dir), [])

            # Test with one-line pkg_resources namespace declaration
            init.write_text(_oneliner1)
            self.assertTrue(check_namespace_init_file(init))
            self.assertListEqual(find_namespace_init_files(package_dir), [str_init])

            # Test with one-line pkgutil namespace declaration
            init.write_text(_oneliner2)
            self.assertTrue(check_namespace_init_file(init))
            self.assertListEqual(find_namespace_init_files(package_dir), [str_init])

            # Test with multiline pkg_resources namespace declaration
            init.write_text(_pkg_resources)
            self.assertTrue(check_namespace_init_file(init))
            self.assertListEqual(find_namespace_init_files(package_dir), [str_init])

            # Test with multiline pkgutil namespace declaration
            init.write_text(_pkgutil)
            self.assertTrue(check_namespace_init_file(init))
            self.assertListEqual(find_namespace_init_files(package_dir), [str_init])

            # Test with multiple namespace declarations
            init.write_text(_both)
            self.assertTrue(check_namespace_init_file(init))
            self.assertListEqual(find_namespace_init_files(package_dir), [str_init])

            # Test with commented-out namespace declarations
            init.write_text(_comments)
            self.assertFalse(check_namespace_init_file(init))
            self.assertListEqual(find_namespace_init_files(package_dir), [])

    def test_find_namespace_init_files(self):
        from zc.buildout.easy_install import find_namespace_init_files

        with tempfile.TemporaryDirectory() as package_dir:
            # Create structure: src/plone/app/example
            # where plone and app are namespace packages.
            package_dir = Path(package_dir)
            (package_dir / "src" / "plone" / "app" / "example").mkdir(parents=True)
            plone_init = package_dir / "src" / "plone" / "__init__.py"
            plone_app_init = package_dir / "src" / "plone" / "app" / "__init__.py"
            example_init = package_dir / "src" / "plone" / "app" / "example" / "__init__.py"

            # In all cases, the example package is not a namespace package,
            # but it will have an __init__.py file.
            example_init.write_text("# Non-empty init file")

            # Native namespaces.
            self.assertListEqual(find_namespace_init_files(package_dir), [])

            # pkg_resources namespaces.
            plone_init.write_text(_oneliner1)
            plone_app_init.write_text(_oneliner1)
            self.assertListEqual(
                find_namespace_init_files(package_dir), [str(plone_init), str(plone_app_init)]
            )

            # pkg_util namespaces.
            plone_init.write_text(_oneliner2)
            plone_app_init.write_text(_oneliner2)
            self.assertListEqual(
                find_namespace_init_files(package_dir), [str(plone_init), str(plone_app_init)]
            )


class TestVendoredPkgResources(unittest.TestCase):
    """Tests for the pkg_resources copy vendored in zc.buildout._vendor.

    See src/zc/buildout/_vendor/README.rst and
    https://github.com/buildout/buildout/issues/685
    """

    def test_pkg_resources_importable(self):
        # Importing zc.buildout guarantees that `import pkg_resources`
        # works afterwards, whatever setuptools version is installed:
        # either something imported a real pkg_resources first
        # (setuptools < 82) or the vendored copy was aliased.
        import sys

        import zc.buildout  # noqa
        import pkg_resources
        self.assertIs(sys.modules['pkg_resources'], pkg_resources)
        self.assertTrue(hasattr(pkg_resources, 'WorkingSet'))

    def test_alias_in_fresh_process(self):
        # In a fresh process, importing zc.buildout installs the vendored
        # copy as `pkg_resources` - unless a real pkg_resources was
        # imported before, which old setuptools versions (< 66) do
        # themselves during `import setuptools`; then the guard keeps
        # that copy to preserve module identity.
        import os
        import subprocess
        import sys
        import textwrap

        import zc.buildout.easy_install
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join(
            zc.buildout.easy_install.buildout_and_setuptools_path)
        code = textwrap.dedent("""
            import sys
            import setuptools
            pre_imported = 'pkg_resources' in sys.modules
            import zc.buildout
            import pkg_resources
            name = sys.modules['pkg_resources'].__name__
            if pre_imported:
                assert name == 'pkg_resources', name
            else:
                assert name == 'zc.buildout._vendor.pkg_resources', name
        """)
        subprocess.check_call([sys.executable, '-c', code], env=env)

    def test_resource_string_finds_setuptools_cli_exe(self):
        # easy_install.py reads setuptools' cli.exe launcher via
        # pkg_resources.resource_string when generating interpreter
        # scripts on Windows.  This must keep working with the vendored
        # pkg_resources, whatever the location of setuptools.
        import zc.buildout  # noqa
        import pkg_resources
        data = pkg_resources.resource_string('setuptools', 'cli.exe')
        self.assertEqual(data[:2], b'MZ')

    def test_vendored_copy_is_functional(self):
        from zc.buildout._vendor import pkg_resources as vendored
        req = vendored.Requirement.parse('foo.bar>=1.0')
        self.assertEqual(req.project_name, 'foo.bar')
        self.assertEqual(req.key, 'foo.bar')
        ws = vendored.WorkingSet()
        self.assertIsNone(ws.find(vendored.Requirement.parse('does-not-exist')))

    def test_jaraco_text_helpers(self):
        from zc.buildout._vendor.jaraco_text import drop_comment
        from zc.buildout._vendor.jaraco_text import join_continuation
        from zc.buildout._vendor.jaraco_text import yield_lines

        self.assertEqual(drop_comment('foo # bar'), 'foo')
        self.assertEqual(
            drop_comment('http://example.com/foo#bar'),
            'http://example.com/foo#bar')
        self.assertEqual(
            list(join_continuation(['foo \\', 'bar', 'baz'])),
            ['foobar', 'baz'])
        self.assertEqual(
            list(yield_lines('\nfoo\n#bar\nbaz #comment')),
            ['foo', 'baz #comment'])
        self.assertEqual(
            list(yield_lines(['foo\nbar', 'baz', 'bing\n\n\n'])),
            ['foo', 'bar', 'baz', 'bing'])


class TestSetuptoolsConstraint(unittest.TestCase):
    """Tests for how an unpinned setuptools requirement is constrained.

    Since zc.buildout vendors its own pkg_resources copy, an unpinned
    setuptools is no longer restricted for regular installs.  Only
    distributions with pkg_resources-style namespace packages still get
    setuptools<82 (the last version shipping pkg_resources) added to
    their working set, because their scripts import pkg_resources at
    script run time.  See https://github.com/buildout/buildout/issues/750
    """

    def test_constrain_leaves_unpinned_setuptools_alone(self):
        import pkg_resources

        from zc.buildout.easy_install import Installer
        installer = Installer()
        requirement = installer._constrain(
            pkg_resources.Requirement.parse('setuptools'))
        self.assertEqual(list(requirement.specs), [])

    def test_constrain_applies_user_pin_to_setuptools(self):
        import pkg_resources

        from zc.buildout.easy_install import Installer
        installer = Installer(versions={'setuptools': '81.0.0'})
        requirement = installer._constrain(
            pkg_resources.Requirement.parse('setuptools'))
        self.assertEqual(str(requirement), 'setuptools==81.0.0')

    def test_namespace_dists_get_setuptools_below_82(self):
        # The building block used by Installer._maybe_add_setuptools when
        # the user did not pin setuptools.
        import pkg_resources

        from zc.buildout.easy_install import _constrained_requirement
        requirement = _constrained_requirement(
            '<82', pkg_resources.Requirement.parse('setuptools'))
        self.assertEqual(str(requirement), 'setuptools<82')
        self.assertIn('81.0.0', requirement)
        self.assertNotIn('82.0.0', requirement)
        self.assertNotIn('83.0.0', requirement)


class TestWheelSelection(unittest.TestCase):
    """Test choosing the most specific wheel of several compatible ones."""

    def _dists(self, *urls):
        return [dist for url in urls for dist in distros_for_url(url)]

    def _platform_wheel(self):
        tag = next(iter(sys_tags()))
        return f"foo-1.0-{tag.interpreter}-{tag.abi}-{tag.platform}.whl"

    def _obtain(self, download_cache, dists):
        class FakeIndex(dict):
            def obtain(self, requirement):
                return True

        installer = object.__new__(Installer)
        installer._index = FakeIndex(foo=dists)
        # Same normalization as `zc.buildout.easy_install.download_cache()`:
        installer._download_cache = realpath(download_cache)
        return installer._obtain(Requirement.parse("foo"))

    def test_wheel_tag_rank(self):
        """It ranks the most specific wheel 0 and incompatible ones None."""
        self.assertEqual(wheel_tag_rank(Wheel(self._platform_wheel())), 0)
        self.assertGreater(wheel_tag_rank(Wheel("foo-1.0-py3-none-any.whl")), 0)
        self.assertIsNone(
            wheel_tag_rank(Wheel("foo-1.0-py2-none-no_such_platform.whl")))

    def test_distros_for_location_skips_incompatible_wheels(self):
        """It does not return a dist for a wheel with an unsupported tag."""
        self.assertEqual(
            self._dists("http://x/foo-1.0-py2-none-no_such_platform.whl"), [])

    def test_dist_sort_key_prefers_most_specific_wheel(self):
        """It sorts a platform wheel after an `any` wheel regardless of URL."""
        # The URLs are chosen so that sorting by URL, as buildout did
        # before, would pick the `any` wheel.
        platform_url = "http://x/aaa/" + self._platform_wheel()
        any_url = "http://x/zzz/foo-1.0-py3-none-any.whl"
        for urls in [(platform_url, any_url), (any_url, platform_url)]:
            best = sorted(self._dists(*urls), key=_dist_sort_key)[-1]
            self.assertEqual(best.location, platform_url)

    def test_dist_sort_key_still_prefers_wheel_over_sdist(self):
        """It sorts a wheel after an sdist."""
        any_url = "http://x/aaa/foo-1.0-py3-none-any.whl"
        sdist_url = "http://x/zzz/foo-1.0.tar.gz"
        best = sorted(self._dists(any_url, sdist_url), key=_dist_sort_key)[-1]
        self.assertEqual(best.location, any_url)

    def test_obtain_prefers_download_cache_only_if_as_specific(self):
        """It uses a cached wheel unless the index has a more specific one."""
        with tempfile.TemporaryDirectory() as cache:
            cached_any = os.path.join(cache, "foo-1.0-py3-none-any.whl")
            cached_any_dist, = distros_for_filename(cached_any)
            any_url = "http://x/foo-1.0-py3-none-any.whl"
            platform_url = "http://x/" + self._platform_wheel()

            # The cached `any` wheel wins over the same wheel on the index:
            best = self._obtain(
                cache, self._dists(any_url) + [cached_any_dist])
            self.assertEqual(best.location, cached_any_dist.location)

            # But a more specific wheel on the index wins over the cache:
            best = self._obtain(
                cache, self._dists(platform_url) + [cached_any_dist])
            self.assertEqual(best.location, platform_url)

    def test_obtain_prefers_index_wheel_over_cached_sdist(self):
        """It uses a wheel from the index over a cached sdist."""
        with tempfile.TemporaryDirectory() as cache:
            cached_sdist_dist, = distros_for_filename(
                os.path.join(cache, "foo-1.0.tar.gz"))
            any_url = "http://x/foo-1.0-py3-none-any.whl"

            # A wheel on the index wins over a cached sdist:
            best = self._obtain(
                cache, self._dists(any_url) + [cached_sdist_dist])
            self.assertEqual(best.location, any_url)

            # Once the wheel is in the cache (downloads go there), the
            # cached wheel is used:
            cached_any_dist, = distros_for_filename(
                os.path.join(cache, "foo-1.0-py3-none-any.whl"))
            best = self._obtain(
                cache,
                self._dists(any_url) + [cached_sdist_dist, cached_any_dist])
            self.assertEqual(best.location, cached_any_dist.location)
