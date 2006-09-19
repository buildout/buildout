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
import os, unittest
from zope.testing import doctest
import zc.buildout.tests
import zc.buildout.testing

def test_selecting_python_via_easy_install():
    """\

We can specify an alternate Python executable.

    >>> dest = tmpdir('sample-install')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo'], dest, links=[link_server], index=link_server+'index/',
    ...     always_unzip=True, executable= python2_3_executable)

    >>> ls(dest)
    d  demo-0.3-py2.3.egg
    d  demoneeded-1.1-py2.3.egg

    >>> rmdir(dest)
    >>> dest = tmpdir('sample-install')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo'], dest, links=[link_server], index=link_server+'index/',
    ...     always_unzip=True, executable=python2_4_executable)

    >>> ls(dest)
    d  demo-0.3-py2.4.egg
    d  demoneeded-1.1-py2.4.egg

"""

# XXX need to think how this will work w future versions of python

def multi_python(test):
    p23 = zc.buildout.testing.find_python('2.3')
    p24 = zc.buildout.testing.find_python('2.4')
    sample_eggs = test.globs['tmpdir']('sample_eggs')
    os.mkdir(os.path.join(sample_eggs, 'index'))
    test.globs['sample_eggs'] = sample_eggs
    zc.buildout.tests.create_sample_eggs(test, executable=p23)
    zc.buildout.tests.create_sample_eggs(test, executable=p24)
    test.globs['python2_3_executable'] = p23
    test.globs['python2_4_executable'] = p24


def setup(test):
    zc.buildout.testing.buildoutSetUp(test)
    multi_python(test)
    zc.buildout.tests.add_source_dist(test)
    test.globs['link_server'] = test.globs['start_server'](
        test.globs['sample_eggs'])


def test_suite():
    return doctest.DocTestSuite(setUp=setup,
                                tearDown=zc.buildout.testing.buildoutTearDown)
