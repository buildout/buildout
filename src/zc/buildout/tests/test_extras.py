# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2020 Zope Foundation and Contributors.
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
import doctest
import re
from zope.testing import renormalizing
import zc.buildout.testing
from zc.buildout.tests import easy_install_SetUp
from zc.buildout.tests import normalize_bang


def install_extras_with_greater_than_constrains():
    """
    There was a bug that caused extras in requirements to be lost.

    >>> working = tmpdir('working')
    >>> cd(working)
    >>> mkdir('dependency')
    >>> cd('dependency')
    >>> with open('setup.py', 'w') as f:
    ...    _ = f.write('''
    ... from setuptools import setup
    ... setup(name='dependency', version='1.0',
    ...       url='x', author='x', author_email='x',
    ...       py_modules=['t'])
    ... ''')
    >>> open('README', 'w').close()
    >>> open('t.py', 'w').close()

    >>> sdist('.', sample_eggs)
    >>> cd(working)
    >>> mkdir('extras')
    >>> cd('extras')
    >>> with open('setup.py', 'w') as f:
    ...    _ = f.write('''
    ... from setuptools import setup
    ... setup(name='extraversiondemo', version='1.0',
    ...       url='x', author='x', author_email='x',
    ...       extras_require=dict(foo=['dependency']), py_modules=['t'])
    ... ''')
    >>> open('README', 'w').close()
    >>> open('t.py', 'w').close()

    >>> sdist('.', sample_eggs)
    >>> mkdir('dest')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['extraversiondemo[foo]'], 'dest', links=[sample_eggs],
    ...     versions = dict(extraversiondemo='1.0', dependency='>0.9')
    ... )
    >>> sorted(dist.key for dist in ws)
    ['dependency', 'extraversiondemo']
    """


def test_suite():
    return doctest.DocTestSuite(
        setUp=easy_install_SetUp,
        tearDown=zc.buildout.testing.buildoutTearDown,
        checker=renormalizing.RENormalizing([
            zc.buildout.testing.normalize_path,
            zc.buildout.testing.normalize_endings,
            zc.buildout.testing.normalize_script,
            zc.buildout.testing.normalize_egg_py,
            zc.buildout.testing.normalize___pycache__,
            zc.buildout.testing.not_found,
            zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
            zc.buildout.testing.adding_find_link,
            zc.buildout.testing.python27_warning,
            zc.buildout.testing.python27_warning_2,
            zc.buildout.testing.easyinstall_deprecated,
            zc.buildout.testing.setuptools_deprecated,
            zc.buildout.testing.pkg_resources_deprecated,
            zc.buildout.testing.warnings_warn,
            normalize_bang,
            (re.compile(r'^(\w+\.)*(Missing\w+: )'), '\2'),
            (re.compile(r"buildout: Running \S*setup.py"),
             'buildout: Running setup.py'),
            (re.compile(r'pip-\S+-'),
             'pip.egg'),
            (re.compile(r'setuptools-\S+-'),
             'setuptools.egg'),
            (re.compile(r'zc.buildout-\S+-'),
             'zc.buildout.egg'),
            (re.compile(r'pip = \S+'), 'pip = 20.0.0'),
            (re.compile(r'setuptools = \S+'), 'setuptools = 0.7.99'),
            (re.compile(r'File "\S+one.py"'),
             'File "one.py"'),
            (re.compile(r'We have a develop egg: (\S+) (\S+)'),
             r'We have a develop egg: \1 V'),
            (re.compile(r'Picked: setuptools = \S+'),
             'Picked: setuptools = V'),
            (re.compile('[-d]  pip'), '-  pip'),
            (re.compile('[-d]  setuptools'), '-  setuptools'),
            (re.compile(r'\\[\\]?'), '/'),
            (re.compile(
                '-q develop -mxN -d "/sample-buildout/develop-eggs'),
             '-q develop -mxN -d /sample-buildout/develop-eggs'
             ),
            (re.compile(r'^[*]...'), '...'),
            # for
            # bug_92891
            # bootstrap_crashes_with_egg_recipe_in_buildout_section
            (re.compile(r"Unused options for buildout: 'eggs' 'scripts'\."),
             "Unused options for buildout: 'scripts' 'eggs'."),
            # Python 3.4 changed the wording of NameErrors
            (re.compile('NameError: global name'), 'NameError: name'),
            # fix for test_distutils_scripts_using_import_are_properly_parsed
            # and test_distutils_scripts_using_from_are_properly_parsed
            # win32 apparently adds a " around sys.executable
            (re.compile('#!"python"'), '#!python'),
            ]),
        )
