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
version = '2.9.7.dev0'

import os
from setuptools import setup

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

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
    namespace_packages = ['zc'],
    install_requires = [
        'setuptools>=8.0',
    ],
    include_package_data = True,
    entry_points = entry_points,
    extras_require = dict(
        test=['zope.testing', 'manuel',
              'bobo ==2.3.0', 'zdaemon', 'zc.zdaemonrecipe',
              'zc.recipe.deployment']),
    zip_safe=False,
    classifiers = [
       'Intended Audience :: Developers',
       'License :: OSI Approved :: Zope Public License',
       'Programming Language :: Python',
       'Programming Language :: Python :: 2',
       'Programming Language :: Python :: 2.7',
       'Programming Language :: Python :: 3',
       'Programming Language :: Python :: 3.4',
       'Programming Language :: Python :: 3.5',
       'Programming Language :: Python :: 3.6',
       'Topic :: Software Development :: Build Tools',
       'Topic :: Software Development :: Libraries :: Python Modules',
       ],
    )
