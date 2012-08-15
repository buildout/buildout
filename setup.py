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
version = "1.6.0"

import os
from setuptools import setup

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description=(
        read('README.txt')
        + '\n' +
        read('SYSTEM_PYTHON_HELP.txt')
        + '\n' +
        'Detailed Documentation\n'
        '**********************\n'
        + '\n' +
        read('src', 'zc', 'buildout', 'buildout.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'unzip.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'repeatable.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'download.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'downloadcache.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'extends-cache.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'setup.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'update.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'debugging.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'testing.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'easy_install.txt')
        + '\n' +
        read('src', 'zc', 'buildout', 'distribute.txt')
        + '\n' +
        read('CHANGES.txt')
        + '\n' +
        'Download\n'
        '**********************\n'
        )

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
    url='http://pypi.python.org/pypi/zc.buildout',

    data_files = [('.', ['README.txt'])],
    packages = ['zc', 'zc.buildout'],
    package_dir = {'': 'src'},
    namespace_packages = ['zc'],
    install_requires = 'setuptools',
    include_package_data = True,
    entry_points = entry_points,
    extras_require = dict(test=['zope.testing']),
    zip_safe=False,
    classifiers = [
       'Intended Audience :: Developers',
       'License :: OSI Approved :: Zope Public License',
       'Topic :: Software Development :: Build Tools',
       'Topic :: Software Development :: Libraries :: Python Modules',
       ],
    )
