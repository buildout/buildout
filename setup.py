##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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

version = "1.1.2dev"

import os
from setuptools import setup, find_packages

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description=(
        read('README.txt')
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
        read('src', 'zc', 'buildout', 'downloadcache.txt')
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
        read('CHANGES.txt')
        + '\n' +
        'Download\n'
        '**********************\n'
        )

open('doc.txt', 'w').write(long_description)

name = "zc.buildout"
setup(
    name = name,
    version = version,
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "System for managing development buildouts",
    long_description=long_description,
    license = "ZPL 2.1",
    keywords = "development build",
    url='http://www.python.org/pypi/zc.buildout',

    data_files = [('.', ['README.txt'])],
    packages = ['zc', 'zc.buildout'],
    package_dir = {'': 'src'},
    namespace_packages = ['zc'],
    install_requires = 'setuptools',
    include_package_data = True,
    entry_points = {'console_scripts':
                    ['buildout = %s.buildout:main' % name]}, 
    zip_safe=False,
    classifiers = [
       'Intended Audience :: Developers',
       'License :: OSI Approved :: Zope Public License',
       'Topic :: Software Development :: Build Tools',
       'Topic :: Software Development :: Libraries :: Python Modules',
       ],
    )
