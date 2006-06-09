from setuptools import setup, find_packages

setup(
    name = "zc.buildout",
    version = "0.1",
    packages = ['zc.buildout'],
    package_dir = {'':'src'},
    namespace_packages = ['zc'],
    include_package_data = True,
    tests_require = ['zope.testing'],
    test_suite = 'zc.buildout.tests.test_suite',
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "System for managing development buildouts",
    license = "ZPL 2.1",
    keywords = "development build",
    install_requires = 'setuptools',
    entry_points = {'console_scripts':
                    ['buildout = zc.buildout.buildout:main']}, 
    )
