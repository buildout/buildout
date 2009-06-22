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
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('[-d]  setuptools-[^-]+-'), 'setuptools-X-'),
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
               (re.compile('__buildout_signature__ = '
                           'sample-\S+\s+'
                           'zc.recipe.egg-\S+\s+'
                           'setuptools-\S+\s+'
                           'zc.buildout-\S+\s*'
                           ),
                '__buildout_signature__ = sample- zc.recipe.egg-'),
               (re.compile('executable = [\S ]+python\S*', re.I),
                'executable = python'),
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
               (re.compile("(d  ((ext)?demo(needed)?|other)"
                           "-\d[.]\d-py)\d[.]\d(-\S+)?[.]egg"),
                '\\1V.V.egg'),
               (re.compile('extdemo.c\n.+\\extdemo.exp\n'), ''),
               (re.compile('extdemo[.]pyd'), 'extdemo.so')
               ]),
            ),
        
        ))

    if sys.version_info[:2] == (2, 5):
        # Only run selecting python tests if not 2.4, since
        # 2.4 is the alternate python used in the tests.
        suite.addTest(
            doctest.DocFileSuite(
                'selecting-python.txt',
                setUp=setUpSelecting,
                tearDown=zc.buildout.testing.buildoutTearDown,
                checker=renormalizing.RENormalizing([
                   zc.buildout.testing.normalize_path,
                   zc.buildout.testing.normalize_endings,
                   zc.buildout.testing.normalize_script,
                   (re.compile('Got setuptools \S+'), 'Got setuptools V'),
                   (re.compile('([d-]  )?setuptools-\S+-py'),
                    'setuptools-V-py'),
                   (re.compile('-py2[.][0-35-9][.]'), 'py2.5.'),
                   (re.compile('zc.buildout-\S+[.]egg'),
                    'zc.buildout.egg'),
                   (re.compile('zc.buildout[.]egg-link'),
                    'zc.buildout.egg'),
                   ]),
                ),
            )
    
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

