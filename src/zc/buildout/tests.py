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
    r"""Buildout error handling

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
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y}
    ... y = ${buildout:z}
    ... z = ${buildout:x}
    ... ''')

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: ('Circular references',
           [('buildout', 'y'), ('buildout', 'z'), ('buildout', 'x')],
           ('buildout', 'y'))
"""

def linkerSetUp(test):
    zc.buildout.testing.buildoutSetUp(test, clear_home=False)
    zc.buildout.testing.multi_python(test)
    zc.buildout.testing.setUpServer(test, zc.buildout.testing.make_tree(test))

class PythonNormalizing(renormalizing.RENormalizing):

    def _transform(self, want, got):
        if '/xyzsample-install/' in want:
            got = got.replace('-py2.4.egg', '-py2.3.egg')
            firstg = got.split('\n')[0]
            firstw = want.split('\n')[0]
            if firstg.startswith('#!') and firstw.startswith('#!'):
                firstg = ' '.join(firstg.split()[1:])
                got = firstg + '\n' + '\n'.join(got.split('\n')[1:])
                firstw = ' '.join(firstw.split()[1:])
                want = firstw + '\n' + '\n'.join(want.split('\n')[1:])
        
        for pattern, repl in self.patterns:
            want = pattern.sub(repl, want)
            got = pattern.sub(repl, got)

        return want, got

    def check_output(self, want, got, optionflags):
        if got == want:
            return True

        want, got = self._transform(want, got)
        if got == want:
            return True
            
        return doctest.OutputChecker.check_output(self, want, got, optionflags)

    def output_difference(self, example, got, optionflags):

        want = example.want

        # If want is empty, use original outputter. This is useful
        # when setting up tests for the first time.  In that case, we
        # generally use the differencer to display output, which we evaluate
        # by hand.
        if not want.strip():
            return doctest.OutputChecker.output_difference(
                self, example, got, optionflags)

        # Dang, this isn't as easy to override as we might wish
        original = want
        want, got = self._transform(want, got)

        # temporarily hack example with normalized want:
        example.want = want
        result = doctest.OutputChecker.output_difference(
            self, example, got, optionflags)
        example.want = original

        return result

    
def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'buildout.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               (re.compile('\S+sample-(\w+)%s(\S+)' % os.path.sep),
                r'/sample-\1/\2'),
               (re.compile('\S+sample-(\w+)'), r'/sample-\1'),
               (re.compile('executable = \S+python\S*'),
                'executable = python'),
               (re.compile('setuptools-\S+[.]egg'), 'setuptools.egg'),
               ])
            ),
        
        doctest.DocFileSuite(
            'easy_install.txt', 
            setUp=linkerSetUp, tearDown=zc.buildout.testing.buildoutTearDown,

            checker=PythonNormalizing([
               (re.compile("'%(sep)s\S+sample-install%(sep)s(dist%(sep)s)?"
                           % dict(sep=os.path.sep)),
                '/sample-eggs/'),
               (re.compile("(-  (demo(needed)?|other)"
                           "-\d[.]\d-py)\d[.]\d[.]egg"),
                '\\1V.V.egg'),
               ]),
            ),
        doctest.DocTestSuite(
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

