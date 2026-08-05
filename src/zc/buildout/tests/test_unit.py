from pathlib import Path

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
        # copy as `pkg_resources` (nothing else imported it before).
        import os
        import subprocess
        import sys

        import zc.buildout.easy_install
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join(
            zc.buildout.easy_install.buildout_and_setuptools_path)
        code = (
            "import zc.buildout, sys; "
            "assert sys.modules['pkg_resources'].__name__ == "
            "'zc.buildout._vendor.pkg_resources', "
            "sys.modules['pkg_resources'].__name__"
        )
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
