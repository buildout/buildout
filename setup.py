from setuptools import setup, find_packages

name = "zc.buildout"
setup(
    name = name,
    version = "1.0.0b2",
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "System for managing development buildouts",
    long_description=open('README.txt').read(),
    license = "ZPL 2.1",
    keywords = "development build",
    url='http://svn.zope.org/zc.buildout',

    data_files = [('.', ['README.txt'])],
    packages = ['zc', 'zc.buildout'],
    package_dir = {'': 'src'},
    namespace_packages = ['zc'],
    install_requires = 'setuptools',
    include_package_data = True,
    tests_require = ['zope.testing'],
    test_suite = name+'.tests.test_suite',
    entry_points = {'console_scripts':
                    ['buildout = %s.buildout:main' % name]}, 
    dependency_links = ['http://download.zope.org/distribution/'],
    zip_safe=False,
    )
