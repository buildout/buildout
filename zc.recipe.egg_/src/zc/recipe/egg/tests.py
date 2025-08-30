##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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

from zope.testing import renormalizing
import doctest
import os
import re
import zc.buildout.tests
import zc.buildout.testing
from zc.buildout import WINDOWS

import unittest

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

def test_suite():
    suites = [
        doctest.DocFileSuite(
            'README.rst',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.tests.normalize_bang,
               zc.buildout.testing.not_found,
               zc.buildout.testing.easyinstall_deprecated,
               zc.buildout.testing.setuptools_deprecated,
               zc.buildout.testing.pkg_resources_deprecated,
               zc.buildout.testing.warnings_warn,
               zc.buildout.testing.ignore_root_logger,
               (re.compile(r'[d-]  zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile(r'[d-]  setuptools-[^-]+-'), 'setuptools-X-'),
               (re.compile(r'[d-]  pip-[^-]+-'), 'pip-X-'),
               (re.compile(r'eggs\\\\v5\\\\demo'), 'eggs/v5/demo'),
               (re.compile(r'[a-zA-Z]:\\\\foo\\\\bar'), '/foo/bar'),
               ])
            ),
        doctest.DocFileSuite(
            'api.rst',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.not_found,
               zc.buildout.testing.easyinstall_deprecated,
               zc.buildout.testing.setuptools_deprecated,
               zc.buildout.testing.pkg_resources_deprecated,
               zc.buildout.testing.warnings_warn,
               zc.buildout.testing.ignore_root_logger,
               (re.compile('__buildout_signature__ = '
                           r'sample-\S+\s+'
                           r'zc.recipe.egg-\S+\s+'
                           r'setuptools-\S+\s+'
                           r'zc.buildout-\S+\s*'
                           ),
                '__buildout_signature__ = sample- zc.recipe.egg-'),
               (re.compile(r'find-links = http://localhost:\d+/'),
                'find-links = http://localhost:8080/'),
               (re.compile(r'index = http://localhost:\d+/index'),
                'index = http://localhost:8080/index'),
               ])
            ),
        doctest.DocFileSuite(
            'working_set_caching.rst',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.not_found,
               zc.buildout.testing.ignore_root_logger,
               ])
            ),
        ]
    if not WINDOWS:
        suites.append(
            doctest.DocFileSuite(
                'custom.rst',
                setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
                optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
                checker=renormalizing.RENormalizing([
                    zc.buildout.testing.normalize_path,
                    zc.buildout.testing.normalize_endings,
                    zc.buildout.testing.not_found,
                    zc.buildout.testing.easyinstall_deprecated,
                    zc.buildout.testing.setuptools_deprecated,
                    zc.buildout.testing.pkg_resources_deprecated,
                    zc.buildout.testing.warnings_warn,
                    zc.buildout.testing.ignore_root_logger,
                    (re.compile("(d  ((ext)?demo(needed)?|other)"
                                r"-\d[.]\d-py)\d[.]\d{1,2}(-\S+)?[.]egg"),
                     '\\1V.V.egg'),
                    (re.compile("ld: warning.*"), ""),
                    ]),
                )
        )
    suite = unittest.TestSuite(suites)
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
