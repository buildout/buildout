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
import zc.buildout.testing

import unittest
from zope.testing import doctest, renormalizing

def dirname(d, level=1):
    if level == 0:
        return d
    return dirname(os.path.dirname(d), level-1)

def setUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    open(os.path.join(test.globs['sample_buildout'],
                      'eggs', 'zc.recipe.egg.egg-link'),
         'w').write(dirname(__file__, 4))
    zc.buildout.testing.create_sample_eggs(test)
        
def tearDown(test):
    shutil.rmtree(test.globs['_sample_eggs_container'])
    zc.buildout.testing.buildoutTearDown(test)
    

def test_suite():
    return unittest.TestSuite((
        #doctest.DocTestSuite(),
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=tearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('(\S+[/%(sep)s]| )'
                           '(\\w+-)[^ \t\n%(sep)s/]+.egg'
                           % dict(sep=os.path.sep)
                           ),
                '\\2-VVV-egg')
               ])
            ),
        
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

