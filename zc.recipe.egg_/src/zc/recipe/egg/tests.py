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
                      'develop-eggs', 'zc.recipe.egg.egg-link'),
         'w').write(dirname(__file__, 4))
    zc.buildout.testing.create_sample_eggs(test)
    test.globs['link_server'] = (
        'http://localhost:%s/'
        % zc.buildout.testing.start_server(zc.buildout.testing.make_tree(test))
        )

        
def tearDown(test):
    zc.buildout.testing.buildoutTearDown(test)
    zc.buildout.testing.stop_server(test.globs['link_server'])

def setUpPython(test):
    zc.buildout.testing.buildoutSetUp(test, clear_home=False)
    
    open(os.path.join(test.globs['sample_buildout'],
                      'develop-eggs', 'zc.recipe.egg.egg-link'),
         'w').write(dirname(__file__, 4))

    zc.buildout.testing.multi_python(test)
    test.globs['link_server'] = (
        'http://localhost:%s/'
        % zc.buildout.testing.start_server(zc.buildout.testing.make_tree(test))
        )

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
                '\\2-VVV-egg'),
               (re.compile('-py\d[.]\d.egg'), '-py2.4.egg'),
               ])
            ),
        doctest.DocFileSuite(
            'selecting-python.txt',
            setUp=setUpPython, tearDown=tearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('\S+sample-(\w+)%s(\S+)' % os.path.sep),
                r'/sample-\1/\2'),
               (re.compile('\S+sample-(\w+)'), r'/sample-\1'),
               ]),
            ),        
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

