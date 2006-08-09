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
    zc.buildout.testing.setUpServer(test, zc.buildout.testing.make_tree(test))


def setUpPython(test):
    zc.buildout.testing.buildoutSetUp(test, clear_home=False)
    
    open(os.path.join(test.globs['sample_buildout'],
                      'develop-eggs', 'zc.recipe.egg.egg-link'),
         'w').write(dirname(__file__, 4))

    zc.buildout.testing.multi_python(test)
    zc.buildout.testing.setUpServer(test, zc.buildout.testing.make_tree(test))

def setUpCustom(test):
    zc.buildout.testing.buildoutSetUp(test)
    open(os.path.join(test.globs['sample_buildout'],
                      'develop-eggs', 'zc.recipe.egg.egg-link'),
         'w').write(dirname(__file__, 4))
    zc.buildout.testing.create_sample_eggs(test)
    zc.buildout.testing.add_source_dist(test)
    zc.buildout.testing.setUpServer(test, zc.buildout.testing.make_tree(test))

    
def test_suite():
    return unittest.TestSuite((
        #doctest.DocTestSuite(),
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
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
            'api.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('_b = \S+sample-buildout.bin'),
                '_b = sample-buildout/bin'),
               (re.compile('__buildout_signature__ = \S+'),
                '__buildout_signature__ = sample-6aWMvV2EJ9Ijq+bR8ugArQ=='),
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
            setUp=setUpPython, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('\S+sample-(\w+)%s(\S+)' % os.path.sep),
                r'/sample-\1/\2'),
               (re.compile('\S+sample-(\w+)'), r'/sample-\1'),
               ]),
            ),
        doctest.DocFileSuite(
            'custom.txt',
            setUp=setUpCustom, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile("(d  ((ext)?demo(needed)?|other)"
                           "-\d[.]\d-py)\d[.]\d(-[^. \t\n]+)?[.]egg"),
                '\\1V.V.egg'),
               ]),
            ),
        
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

