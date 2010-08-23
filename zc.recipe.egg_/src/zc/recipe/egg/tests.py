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

import unittest, doctest
from zope.testing import renormalizing

os_path_sep = os.path.sep
if os_path_sep == '\\':
    os_path_sep *= 2

def dirname(d, level=1):
    if level == 0:
        return d
    return dirname(os.path.dirname(d), level-1)

def testUsingDictAsOptions():
    """
Some recipes using zc.recipe.egg have been passing dictionaries rather than
zc.buildout.buildout.Options objects.  That's unexpected, but to save
complaints, we'll support it.

Note that this test intends to show that a dictionary can be used as an
options object.  It also uses a dictionary for the buildout object, which is
not intended.

    >>> import zc.buildout.buildout
    >>> import zc.recipe.egg
    >>> faux_egg_options = {'find-links': 'example.com'}
    >>> faux_buildout_options = zc.buildout.buildout._unannotate_section(
    ...     zc.buildout.buildout._buildout_default_options.copy())
    >>> faux_buildout_options['bin-directory'] = '/somewhere/over/rainbow'
    >>> faux_buildout = {
    ...     'faux': faux_egg_options, 'buildout': faux_buildout_options}
    >>> scripts = zc.recipe.egg.Scripts(
    ...     faux_buildout, 'faux', faux_egg_options)
    >>> scripts.links
    ['example.com']
    >>> import zc.buildout.easy_install
    >>> old_install = zc.buildout.easy_install.install
    >>> old_scripts = zc.buildout.easy_install.scripts
    >>> def whatever(*args, **kwargs): pass
    >>> zc.buildout.easy_install.install = whatever
    >>> zc.buildout.easy_install.scripts = whatever
    >>> scripts.install() # This used to fail!
    >>> zc.buildout.easy_install.install = old_install
    >>> zc.buildout.easy_install.scripts = old_scripts
"""

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
                zc.buildout.tests.hide_distribute_additions,
                (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                 'zc.buildout.egg'),
                (re.compile('[-d]  (setuptools|distribute)-[^-]+-'),
                 'setuptools-X-'),
                (re.compile(r'eggs\\\\demo'), 'eggs/demo'),
                (re.compile(r'[a-zA-Z]:\\\\foo\\\\bar'), '/foo/bar'),
                # Distribute unzips eggs by default.
                (re.compile('\-  demoneeded'), 'd  demoneeded'),
                ])
            ),
        doctest.DocFileSuite(
            'api.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.tests.hide_distribute_additions,
                (re.compile('__buildout_signature__ = '
                            'sample-\S+\s+'
                            'zc.recipe.egg-\S+\s+'
                            '(setuptools|distribute)-\S+\s+'
                            'zc.buildout-\S+\s*'
                            ),
                 '__buildout_signature__ = sample- zc.recipe.egg-\n'),
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
                zc.buildout.tests.hide_distribute_additions,
                zc.buildout.tests.hide_zip_safe_message,
                (re.compile("(d  ((ext)?demo(needed)?|other)"
                            "-\d[.]\d-py)\d[.]\d(-\S+)?[.]egg"),
                 '\\1V.V.egg'),
                (re.compile('extdemo.c\n.+\\extdemo.exp\n'), ''),
                (re.compile('extdemo[.]pyd'), 'extdemo.so')
                ]),
            ),
        doctest.DocTestSuite(
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            ),
        ))

    if sys.version_info[:2] != (2, 4):
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
                    zc.buildout.tests.hide_distribute_additions,
                    (re.compile('Got (setuptools|distribute) \S+'),
                     'Got setuptools V'),
                    (re.compile('([d-]  )?(setuptools|distribute)-\S+-py'),
                     'setuptools-V-py'),
                    (re.compile('-py2[.][0-35-9][.]'), 'py2.5.'),
                    (re.compile('zc.buildout-\S+[.]egg'),
                     'zc.buildout.egg'),
                    (re.compile('zc.buildout[.]egg-link'),
                     'zc.buildout.egg'),
                    # Distribute unzips eggs by default.
                    (re.compile('\-  demoneeded'), 'd  demoneeded'),
                    ]),
                ),
            )

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

