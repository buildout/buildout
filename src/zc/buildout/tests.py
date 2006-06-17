##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""XXX short summary goes here.

$Id$
"""

import os, re, shutil, sys, unittest
from zope.testing import doctest, renormalizing
import zc.buildout.testing

def buildout_error_handling():
    r'''Buildout error handling

Asking for a section that doesn't exist, yields a key error:

    >>> import os
    >>> os.chdir(sample_buildout)
    >>> import zc.buildout.buildout
    >>> buildout = zc.buildout.buildout.Buildout('buildout.cfg', [])
    >>> buildout['eek']
    Traceback (most recent call last):
    ...
    KeyError: 'eek'

Asking for an option that doesn't exist, a MissingOption error is raised:

    >>> buildout['buildout']['eek']
    Traceback (most recent call last):
    ...
    MissingOption: ('Missing option', 'buildout', 'eek')

It is an error to create a variable-reference cycle:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y}
    ... y = ${buildout:z}
    ... z = ${buildout:x}
    ... """)

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: ('Circular references',
           [('buildout', 'y'), ('buildout', 'z'), ('buildout', 'x')],
           ('buildout', 'y'))

'''    

def linkerSetUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    zc.buildout.testing.create_sample_eggs(test)
        
def linkerTearDown(test):
    shutil.rmtree(test.globs['_sample_eggs_container'])
    zc.buildout.testing.buildoutTearDown(test)

def buildoutTearDown(test):
    shutil.rmtree(test.globs['extensions'])
    shutil.rmtree(test.globs['home'])
    zc.buildout.testing.buildoutTearDown(test)
    
def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'buildout.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               (re.compile('\S+sample-(\w+)%s(\S+)' % os.path.sep),
                r'/sample-\1/\3'),
               (re.compile('\S+sample-(\w+)'),
                r'/sample-\1/\3'),
                ])
            ),
        doctest.DocFileSuite(
            'egglinker.txt', 'easy_install.txt', 
            setUp=linkerSetUp, tearDown=linkerTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('(\S+[/%(sep)s]| )'
                           '(\\w+-)[^ \t\n%(sep)s/]+.egg'
                           % dict(sep=os.path.sep)
                           ),
                '\\2-VVV-egg'),
               (re.compile('\S+%spython(\d.\d)?' % os.path.sep), 'python')
               ]),
            ),
        doctest.DocTestSuite(
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

