##############################################################################
#
# Copyright (c) 2006-2009 Zope Foundation and Contributors.
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
name = "zc.buildout"
version = '4.1.7'

import os
from setuptools import setup

def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as f:
        return f.read()

long_description= read('README.rst') + '\n' + read('CHANGES.rst')

entry_points = """
[console_scripts]
buildout = %(name)s.buildout:main

[zc.buildout]
debug = %(name)s.testrecipes:Debug

""" % dict(name=name)

setup(
    name = name,
    version = version,
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "System for managing development buildouts",
    long_description=long_description,
    license = "ZPL 2.1",
    keywords = "development build",
    url='http://buildout.org',
    packages = ['zc', 'zc.buildout'],
    package_dir = {'': 'src'},
    python_requires = '>=3.9',
    namespace_packages = ['zc'],
    install_requires = [
        'setuptools>=49.0.0',
        'packaging>=23.2',
        'pip',
        'wheel',
    ],
    include_package_data = True,
    entry_points = entry_points,
    extras_require = dict(
        test=['zope.testing', 'manuel',
              'bobo ==2.3.0', 'zdaemon', 'zc.zdaemonrecipe',
              'zc.recipe.deployment']),
    zip_safe=False,
    classifiers = [
       'Development Status :: 6 - Mature',
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
    )
