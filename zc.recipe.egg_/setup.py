##############################################################################
#
# Copyright (c) 2007 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Setup for zc.recipe.egg package
"""

version = '4.0.0'

import os
from setuptools import setup


def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as f:
        return f.read()

name = "zc.recipe.egg"
setup(
    name = name,
    version = version,
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "Recipe for installing Python package distributions as eggs",
    long_description = (
        read('README.rst')
        + '\n' +
        read('CHANGES.rst')
        + '\n' +
        'Detailed Documentation\n'
        '**********************\n'
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'README.rst')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'custom.rst')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'api.rst')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'working_set_caching.rst')
        + '\n' +
        'Download\n'
        '*********\n'
        ),
    keywords = "development build",
    classifiers = [
       'Development Status :: 6 - Mature',
       'Framework :: Buildout',
       'Intended Audience :: Developers',
       'License :: OSI Approved :: Zope Public License',
       'Programming Language :: Python',
       'Programming Language :: Python :: 3.9',
       'Programming Language :: Python :: 3.10',
       'Programming Language :: Python :: 3.11',
       'Programming Language :: Python :: 3.12',
       'Programming Language :: Python :: 3.13',
       'Topic :: Software Development :: Build Tools',
       'Topic :: Software Development :: Libraries :: Python Modules',
       ],
    url='https://github.com/buildout/buildout/tree/master/zc.recipe.egg_',
    license = "ZPL 2.1",
    packages = ['zc', 'zc.recipe', 'zc.recipe.egg'],
    package_dir = {'': 'src'},
    python_requires = '>=3.9',
    install_requires = [
        'zc.buildout >=5.0.0',
        'setuptools'],
    tests_require = ['zope.testing'],
    test_suite = name+'.tests.test_suite',
    entry_points = {'zc.buildout': ['default = %s:Scripts' % name,
                                    'script = %s:Scripts' % name,
                                    'scripts = %s:Scripts' % name,
                                    'eggs = %s:Eggs' % name,
                                    'custom = %s:Custom' % name,
                                    'develop = %s:Develop' % name,
                                    ]
                    },
    include_package_data = True,
    zip_safe=False,
    )
