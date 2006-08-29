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

os_path_sep = os.path.sep
if os_path_sep == '\\':
    os_path_sep *= 2

def easy_install_SetUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    zc.buildout.testing.multi_python(test)
    zc.buildout.testing.add_source_dist(test)
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
            'easy_install.txt', 
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,

            checker=PythonNormalizing([
               (re.compile("'"
                           "(\w:)?"
                           "[%(sep)s/]\S+sample-install[%(sep)s/]"
                           "[%(sep)s/]?(dist"
                           "[%(sep)s/])?"
                           % dict(sep=os_path_sep)),
                '/sample-eggs/'),
               (re.compile("([d-]  ((ext)?demo(needed)?|other)"
                           "-\d[.]\d-py)\d[.]\d(-[^. \t\n]+)?[.]egg"),
                '\\1V.V.egg'),
               (re.compile('(\n?)-  ([a-zA-Z_.-]+)-script.py\n-  \\2.exe\n'),
                '\\1-  \\2\n'),
               (re.compile('extdemo-1[.]4[.]tar[.]gz'), 'extdemo-1.4.zip'),
               (re.compile('#!\S+python\S+'), '#!python'),
               ]),
            ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

