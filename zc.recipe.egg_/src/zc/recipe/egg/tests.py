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

import os, re, shutil, sys
import zc.buildout.tests
import zc.buildout.testselectingpython
import zc.buildout.testing

import unittest
from zope.testing import doctest, renormalizing

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

def setUpSelecting(test):
    zc.buildout.testselectingpython.setup(test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)
    
def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.tests.normalize_bang,
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('setuptools-[^-]+-'), 'setuptools-X-')
               ])
            ),
        doctest.DocFileSuite(
            'api.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('_b = \S+sample-buildout.bin'),
                '_b = sample-buildout/bin'),
               (re.compile('__buildout_signature__ = '
                           'sample-\S+\s+'
                           'zc.recipe.egg-\S+\s+'
                           'setuptools-\S+\s+'
                           'zc.buildout-\S+\s*'
                           ),
                '__buildout_signature__ = sample- zc.recipe.egg-'),
               (re.compile('_d = \S+sample-buildout.develop-eggs'),
                '_d = sample-buildout/develop-eggs'),
               (re.compile('_e = \S+sample-buildout.eggs'),
                '_e = sample-buildout/eggs'),
               (re.compile('executable = \S+python\S*'),
                'executable = python'),
               (re.compile('index = \S+python\S+'),
                'executable = python'),
               (re.compile('find-links = http://localhost:\d+/'),
                'find-links = http://localhost:8080/'),
               (re.compile('index = http://localhost:\d+/index'),
                'index = http://localhost:8080/index'),
               ])
            ),
        doctest.DocFileSuite(
            'selecting-python.txt',
            setUp=setUpSelecting,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_script,
               (re.compile('-  ([a-zA-Z_0-9.]+)(-\S+)?[.]egg(-link)?'),
                '\\1.egg'),
               ]),
            ),
        doctest.DocFileSuite(
            'custom.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile("(d  ((ext)?demo(needed)?|other)"
                           "-\d[.]\d-py)\d[.]\d(-\S+)?[.]egg"),
                '\\1V.V.egg'),
               (re.compile('extdemo.c\n.+\\extdemo.exp\n'), ''),
               ]),
            ),
        
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

