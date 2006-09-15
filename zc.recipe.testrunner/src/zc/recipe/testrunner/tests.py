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

import os, re, shutil, sys, tempfile
import pkg_resources
import zc.buildout.testing
import zc.recipe.egg

import unittest
import zope.testing
from zope.testing import doctest, renormalizing

def dirname(d, level=1):
    if level == 0:
        return d
    return dirname(os.path.dirname(d), level-1)

def setUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    eggs = os.path.join(test.globs['sample_buildout'], 'eggs')
    open(os.path.join(eggs, 'zc.recipe.testrunner.egg-link'),
         'w').write(dirname(__file__, 4))
    open(os.path.join(eggs, 'zc.recipe.egg.egg-link'),
         'w').write(dirname(zc.recipe.egg.__file__, 4))

    testing = dirname(zope.testing.__file__, 3)
    assert testing.endswith('.egg')
    if os.path.isfile(testing):
        shutil.copy(testing, eggs)
    else:
        shutil.copytree(testing, os.path.join(eggs, os.path.basename(testing)))
        
def tearDown(test):
    zc.buildout.testing.buildoutTearDown(test)
    

def test_suite():
    return unittest.TestSuite((
        #doctest.DocTestSuite(),
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=tearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('(\n?)-  ([a-zA-Z_.-]+)-script.py\n-  \\2.exe\n'),
                '\\1-  \\2\n'),               
               (re.compile('#!\S+python\S*'), '#!python'),
               (re.compile('\S+sample-(\w+)'), r'/sample-\1'),
               (re.compile('-([^-]+)-py\d[.]\d.egg'), r'-py2.3.egg'),
               (re.compile(r'\\+'), '/'),
               (re.compile('\d[.]\d+ seconds'), '0.001 seconds')
               ])
            ),
        
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
