import unittest
import zc.buildout.testing
import os

class TestPEP660(unittest.TestCase):

    def setUp(self):
        self.globs = {}
        zc.buildout.testing.buildoutSetUp(self)
        self.mkdir = self.globs['mkdir']
        self.write = self.globs['write']
        self.system = self.globs['system']

    def tearDown(self):
        zc.buildout.testing.buildoutTearDown(self)

    def test_develop_pep660(self):
        os.environ['BUILDOUT_TESTING_SHOW_PEP660'] = '1'
        try:
            # Create a PEP 660 compliant package (pyproject.toml only)
            self.mkdir('pep660_pkg')
            self.mkdir('pep660_pkg', 'src')
            self.mkdir('pep660_pkg', 'src', 'pep660_pkg')
            self.write('pep660_pkg', 'src', 'pep660_pkg', '__init__.py', 'def main(): print("Hello from PEP 660")')
            self.write('pep660_pkg', 'pyproject.toml', """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pep660_pkg"
version = "0.1.0"
""")

            self.write('buildout.cfg', """
[buildout]
develop = pep660_pkg
parts =
""")

            output = self.system(os.path.join('bin', 'buildout'))
            
            self.assertIn("Develop: ", output)
            self.assertIn("pep660_pkg", output)
            
            # Check develop-eggs
            dev_eggs = os.listdir('develop-eggs')
            
            # Check if there is any .dist-info
            dist_infos = [d for d in dev_eggs if d.endswith('.dist-info')]
            self.assertGreater(len(dist_infos), 0, "Metadata should be present after fix")

            # Check if there is any .pth
            pths = [d for d in dev_eggs if d.endswith('.pth')]
            self.assertGreater(len(pths), 0, ".pth file should be present after fix")
            
            # Now verify that buildout process itself can import it if we add it to sys.path
            import sys
            sys.path.insert(0, os.path.abspath('develop-eggs'))
            # We need to process the .pth files
            import site
            site.addsitedir(os.path.abspath('develop-eggs'))
                 
            try:
                import pep660_pkg
                # Success
            except ImportError:
                self.fail("Could not import pep660_pkg after processing .pth files")
        finally:
            if 'BUILDOUT_TESTING_SHOW_PEP660' in os.environ:
                del os.environ['BUILDOUT_TESTING_SHOW_PEP660']

if __name__ == '__main__':
    unittest.main()
