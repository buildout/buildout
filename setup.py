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
version = "5.3.0a3.dev0"

import os

from setuptools import setup


def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as f:
        return f.read()

long_description= read('README.rst') + '\n' + read('CHANGES.rst')

entry_points = f"""
[console_scripts]
buildout = {name}.buildout:main

[zc.buildout]
debug = {name}.testrecipes:Debug

"""

setup(
    name = name,
    version = version,
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "System for managing development buildouts",
    long_description=long_description,
    license = "ZPL-2.1",
    keywords = "development build",
    url='http://buildout.org',
    packages = ['zc', 'zc.buildout'],
    package_dir = {'': 'src'},
    python_requires = '>=3.9',
    install_requires = [
        'setuptools>=61.0.0,<82',
        'packaging>=23.2',
        'pip',
        'wheel',
        # 0.12.11 is the floor: earlier 0.12.x serve their own cache on
        # --offline resolves, breaking install-from-cache isolation
        # (easy_install.txt and downloadcache.txt pin that contract).
        'uv>=0.12.11',
        'tomli; python_version < "3.11"',
    ],
    include_package_data = True,
    entry_points = entry_points,
    extras_require = {
        "test": ['zope.testing', 'manuel',
              'bobo ==2.3.0', 'zdaemon', 'zc.zdaemonrecipe',
              'zc.recipe.deployment']},
    zip_safe=False,
    classifiers = [
       'Development Status :: 6 - Mature',
       'Intended Audience :: Developers',
       'Programming Language :: Python',
       'Programming Language :: Python :: 3.9',
       'Programming Language :: Python :: 3.10',
       'Programming Language :: Python :: 3.11',
       'Programming Language :: Python :: 3.12',
       'Programming Language :: Python :: 3.13',
       'Programming Language :: Python :: 3.14',
       'Topic :: Software Development :: Build Tools',
       'Topic :: Software Development :: Libraries :: Python Modules',
       ],
    )
