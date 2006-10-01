import os
from setuptools import setup, find_packages

name = "zc.recipe.testrunner"
setup(
    name = name,
    version = "1.0.0b2",
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "ZC Buildout recipe for creating test runners",
    long_description = (
        open('README.txt').read()
         + '\n' +
        open('CHANGES.txt').read()
        + '\n' +
        'Detailed Documentation\n'
        '**********************\n'
        + '\n' +
        open(os.path.join('src', 'zc', 'recipe', 'testrunner', 'README.txt')
             ).read()
        ),
    license = "ZPL 2.1",
    keywords = "development build testing",
    url='http://svn.zope.org/zc.buildout',

    packages = find_packages('src'),
    include_package_data = True,
    package_dir = {'':'src'},
    namespace_packages = ['zc', 'zc.recipe'],
    install_requires = ['zc.buildout  >=1.0.0b7', 'zope.testing', 'setuptools',
                        'zc.recipe.egg  >=1.0.0a3',
                        ],
    test_suite = name+'.tests.test_suite',
    entry_points = {'zc.buildout': ['default = %s:TestRunner' % name]},
    classifiers = [
       'Framework :: Buildout',
       'Development Status :: 4 - Beta',
       'Intended Audience :: Developers',
       'License :: OSI Approved :: Zope Public License',
       'Topic :: Software Development :: Build Tools',
       'Topic :: Software Development :: Libraries :: Python Modules',
       ],
    )
