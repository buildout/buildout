from setuptools import setup, find_packages

setup(
    name = "zc.recipe.testrunner",
    version = "0.1",
    packages = find_packages('src'),
    include_package_data = True,
    package_dir = {'':'src'},
    namespace_packages = ['zc', 'zc.recipe'],
    install_requires = ['zc.buildout', 'zope.testing', 'setuptools'],
    dependency_links = ['http://download.zope.org/distribution/'],
    test_suite = 'zc.recipe.testrunner.tests.test_suite',
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "ZC Buildout recipe for creating test runners",
    license = "ZPL 2.1",
    keywords = "development build",
    entry_points = {'zc.buildout':
                    ['default = zc.recipe.testrunner:TestRunner']},
    )
