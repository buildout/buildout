##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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
import os, re, unittest
from zope.testing import doctest, renormalizing
import zc.buildout.tests
import zc.buildout.testing

def test_selecting_python_via_easy_install():
    """\

We can specify an specific Python executable.

    >>> dest = tmpdir('sample-install')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo'], dest, links=[link_server],
    ...     index='http://www.python.org/pypi/',
    ...     always_unzip=True, executable= python2_3_executable)

    >>> ls(dest)
    d  demo-0.3-py2.3.egg
    d  demoneeded-1.1-py2.3.egg
    d  setuptools-0.6-py2.3.egg

"""

def multi_python(test):
    p23 = zc.buildout.testing.find_python('2.3')
    sample_eggs = test.globs['tmpdir']('sample_eggs')
    os.mkdir(os.path.join(sample_eggs, 'index'))
    test.globs['sample_eggs'] = sample_eggs
    zc.buildout.tests.create_sample_eggs(test, executable=p23)
    test.globs['python2_3_executable'] = p23


def setup(test):
    zc.buildout.testing.buildoutSetUp(test)
    multi_python(test)
    zc.buildout.tests.add_source_dist(test)
    test.globs['link_server'] = test.globs['start_server'](
        test.globs['sample_eggs'])


def test_suite():
    return doctest.DocTestSuite(
        setUp=setup,
        tearDown=zc.buildout.testing.buildoutTearDown,
        checker=renormalizing.RENormalizing([
            (re.compile('setuptools-\S+-py2.3.egg'), 'setuptools-V-py2.3.egg'),
            ]),
        )
