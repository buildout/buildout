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
import os, re, subprocess, sys, textwrap, unittest, doctest
from zope.testing import renormalizing
import zc.buildout.tests
import zc.buildout.testing

if sys.version_info[:2] == (2, 4):
    other_version = "2.5"
else:
    other_version = "2.4"

__test__ = dict(
    test_selecting_python_via_easy_install=
    """\

We can specify a specific Python executable.

    >>> dest = tmpdir('sample-install')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo'], dest, links=[link_server],
    ...     index='http://www.python.org/pypi/',
    ...     always_unzip=True, executable=other_executable)

    >>> ls(dest)
    d  demo-0.3-py%(other_version)s.egg
    d  demoneeded-1.1-py%(other_version)s.egg

""" % dict(other_version=other_version)
    )

def multi_python(test):
    other_executable = zc.buildout.testing.find_python(other_version)
    command = textwrap.dedent('''\
        try:
            import setuptools
        except ImportError:
            import sys
            sys.exit(1)
        ''')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    if subprocess.call([other_executable, '-c', command], env=env):
        # the other executable does not have setuptools.  Get setuptools.
        # We will do this using the same tools we are testing, for better or
        # worse.  Alternatively, we could try using bootstrap.
        executable_dir = test.globs['tmpdir']('executable_dir')
        executable_parts = os.path.join(executable_dir, 'parts')
        test.globs['mkdir'](executable_parts)
        ws = zc.buildout.easy_install.install(
            ['setuptools'], executable_dir,
            index='http://www.python.org/pypi/',
            always_unzip=True, executable=other_executable)
        zc.buildout.easy_install.sitepackage_safe_scripts(
            executable_dir, ws, other_executable, executable_parts,
            reqs=['setuptools'], interpreter='py')
        original_executable = other_executable
        other_executable = os.path.join(executable_dir, 'py')
        assert not subprocess.call(
            [other_executable, '-c', command], env=env), (
            'test set up failed')
    sample_eggs = test.globs['tmpdir']('sample_eggs')
    os.mkdir(os.path.join(sample_eggs, 'index'))
    test.globs['sample_eggs'] = sample_eggs
    zc.buildout.tests.create_sample_eggs(test, executable=other_executable)
    test.globs['other_executable'] = other_executable


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
            (re.compile('setuptools-\S+-py%s.egg' % other_version),
             'setuptools-V-py%s.egg' % other_version),
            ]),
        )
