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

version = '1.3.3dev'

import os
from setuptools import setup, find_packages

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

name = "zc.recipe.egg"
setup(
    name = name,
    version = version,
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "Recipe for installing Python package distributions as eggs",
    long_description = (
        read('README.txt')
        + '\n' +
        read('CHANGES.txt')
        + '\n' +
        'Detailed Documentation\n'
        '**********************\n'
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'README.txt')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'selecting-python.txt')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'custom.txt')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'api.txt')
        + '\n' +
        'Download\n'
        '*********\n'
        ),
    keywords = "development build",
    classifiers = [
       'Development Status :: 5 - Production/Stable',
       'Framework :: Buildout',
       'Intended Audience :: Developers',
       'License :: OSI Approved :: Zope Public License',
       'Topic :: Software Development :: Build Tools',
       'Topic :: Software Development :: Libraries :: Python Modules',
       ],
    url='http://cheeseshop.python.org/pypi/zc.recipe.egg',
    license = "ZPL 2.1",

    packages = find_packages('src'),
    package_dir = {'':'src'},
    namespace_packages = ['zc', 'zc.recipe'],
    install_requires = [
        'zc.buildout >=1.5.0',
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
