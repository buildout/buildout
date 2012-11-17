##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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

from zope.testing import renormalizing
import doctest
import os
import re
import shutil
import sys
import zc.buildout.tests
import zc.buildout.testing

import unittest

os_path_sep = os.path.sep
if os_path_sep == '\\':
    os_path_sep *= 2

def dirname(d, level=1):
    if level == 0:
        return d
    return dirname(os.path.dirname(d), level-1)

def setUp(test):
    zc.buildout.tests.easy_install_SetUp(test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)

def test_suite():
    suite = unittest.TestSuite((
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.tests.normalize_bang,
               zc.buildout.tests.normalize_S,
               zc.buildout.testing.not_found,
               (re.compile('[d-]  zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('[d-]  distribute-[^-]+-'), 'distribute-X-'),
               (re.compile(r'eggs\\\\demo'), 'eggs/demo'),
               (re.compile(r'[a-zA-Z]:\\\\foo\\\\bar'), '/foo/bar'),
               ])
            ),
        doctest.DocFileSuite(
            'api.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.not_found,
               (re.compile('__buildout_signature__ = '
                           'sample-\S+\s+'
                           'zc.recipe.egg-\S+\s+'
                           'distribute-\S+\s+'
                           'zc.buildout-\S+\s*'
                           ),
                '__buildout_signature__ = sample- zc.recipe.egg-'),
               (re.compile('find-links = http://localhost:\d+/'),
                'find-links = http://localhost:8080/'),
               (re.compile('index = http://localhost:\d+/index'),
                'index = http://localhost:8080/index'),
               ])
            ),
        doctest.DocFileSuite(
            'custom.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.not_found,
                (re.compile("(d  ((ext)?demo(needed)?|other)"
                            "-\d[.]\d-py)\d[.]\d(-\S+)?[.]egg"),
                 '\\1V.V.egg'),
                (re.compile('extdemo.c\n.+\\extdemo.exp\n'), ''),
                (re.compile(
                    r'zip_safe flag not set; analyzing archive contents.*\n'),
                 ''),
                (re.compile(
                    r'\n.*module references __file__'),
                 ''),
                (re.compile(''), ''),
                (re.compile(
                    "extdemo[.]c\n"
                    "extdemo[.]obj : warning LNK4197: "
                    "export 'initextdemo' specified multiple times; "
                    "using first specification\n"
                    "   Creating library build\\\\temp[.]win-amd64-2[.]"
                    "[4567]\\\\Release\\\\extdemo[.]lib and object "
                    "build\\\\temp[.]win-amd64-2[.][4567]\\\\Re"
                    "lease\\\\extdemo[.]exp\n"),
                 ''),
                ]),
            ),
        ))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
