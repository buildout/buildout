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
