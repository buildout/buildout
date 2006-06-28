from setuptools import setup, find_packages

setup(
    name = "zc.buildout",
    version = "1.0.dev",
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "System for managing development buildouts",
    license = "ZPL 2.1",
    keywords = "development build",
    url='http://svn.zope.org/zc.buildout',
    download_url='http://download.zope.org/distribution',
    long_description=open('README.txt').read(),


    packages = ['zc', 'zc.buildout'],
    package_dir = {'': 'src'},
    namespace_packages = ['zc'],
    include_package_data = True,
    tests_require = ['zope.testing'],
    test_suite = 'zc.buildout.tests.test_suite',
    install_requires = 'setuptools',
    entry_points = {'console_scripts':
                    ['buildout = zc.buildout.buildout:main']}, 
    )
