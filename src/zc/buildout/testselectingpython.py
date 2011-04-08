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
import os, re, subprocess, sys, textwrap, unittest, doctest
from zope.testing import renormalizing
import zc.buildout.tests
import zc.buildout.testing
import pkg_resources

if sys.version_info[:2] == (2, 5):
    other_version = "2.6"
else:
    other_version = "2.5"

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

        current_buildout_ws = [
            x for x in pkg_resources.WorkingSet()
            if x.project_name == 'zc.buildout'][0].location
        ez_setup_other_path = os.path.join(test.globs['tmpdir']('ez_setup'), 'ez_setup_other.py')
        ez_setup_other = open(ez_setup_other_path, 'w')
        ez_setup_other.write(textwrap.dedent('''\
import urllib2
ez_code = urllib2.urlopen(
    'http://python-distribute.org/distribute_setup.py').read().replace('\\r\\n', '\\n')
ez = {}
exec ez_code in ez
ez['use_setuptools'](to_dir='%(executable_dir)s', download_delay=0, no_fake=True)
import pkg_resources
print list(pkg_resources.WorkingSet())[0].__dict__
import sys
#ws = pkg_resources.WorkingSet()
sys.path.insert(0, '%(buildout_location)s')
print '%(buildout_location)s'
import pdb; pdb.set_trace()
import zc.buildout.easy_install
zc.buildout.easy_install.sitepackage_safe_scripts(
    '%(executable_dir)s', ws, sys.executable, '%(parts)s',
    reqs=['setuptools'], interpreter='py')
            ''' % dict(executable_dir=executable_dir,
                       buildout_location=current_buildout_ws,
                       parts=executable_parts)))
        ez_setup_other.close()
        assert not subprocess.call([other_executable, ez_setup_other_path])
        import pdb; pdb.set_trace() 
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
