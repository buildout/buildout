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


def default_cfg():
    r"""
    >>> home = tmpdir('home')
    >>> mkdir(home, '.buildout')
    >>> default_cfg = join(home, '.buildout', 'default.cfg')
    >>> write(default_cfg, '''
    ... [debug]
    ... dec = 1 
    ...       2
    ... inc = 1
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ...
    ... [debug]
    ... dec -= 2
    ... inc += 2
    ... ''')
    >>> env = dict(HOME=home, USERPROFILE=home)
    >>> print_(system(buildout+' annotate debug', env=env), end='')
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [debug]
    dec= 1
        /home/.buildout/default.cfg
    -=  buildout.cfg
    inc= 1
    2
        /home/.buildout/default.cfg
    +=  buildout.cfg
    """


def default_cfg_extensions():
    r"""
    Add two extensions as develop eggs

    >>> mkdir('demo')
    >>> write('demo', 'demo.py', '''
    ... import sys
    ... def ext(buildout):
    ...     sys.stdout.write('demo %s %s\\n' % ('ext', sorted(buildout)))
    ... def unload(buildout):
    ...     sys.stdout.write('demo %s %s\\n' % ('unload', sorted(buildout)))
    ... ''')
    >>> write('demo', 'setup.py', '''
    ... from setuptools import setup
    ...
    ... setup(
    ...     name = "demo",
    ...     entry_points = {
    ...        'zc.buildout.extension': ['ext = demo:ext'],
    ...        'zc.buildout.unloadextension': ['ext = demo:unload'],
    ...        },
    ...     )
    ... ''')
    >>> mkdir('demo2')
    >>> write('demo2', 'demo2.py', '''
    ... import sys
    ... def ext(buildout):
    ...     sys.stdout.write('demo2 %s %s\\n' % ('ext', sorted(buildout)))
    ... def unload(buildout):
    ...     sys.stdout.write('demo2 %s %s\\n' % ('unload', sorted(buildout)))
    ... ''')
    >>> write('demo2', 'setup.py', '''
    ... from setuptools import setup
    ...
    ... setup(
    ...     name = "demo2",
    ...     entry_points = {
    ...        'zc.buildout.extension': ['ext = demo2:ext'],
    ...        'zc.buildout.unloadextension': ['ext = demo2:unload'],
    ...        },
    ...     )
    ... ''')
    >>> write('buildout.cfg', ''' 
    ... [buildout]
    ... develop = demo demo2
    ... parts =
    ... ''')

    Run buildout once without extensions to actually develop the eggs.
    (Develop happens after loading extensions.)

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/demo'
    Develop: '/sample-buildout/demo2'
    >>> ls("develop-eggs")
    -  demo.egg-link
    -  demo2.egg-link
    -  zc.recipe.egg.egg-link

    extensions in .buildout/default.cfg
    incremented in buildout.cfg

    >>> home = tmpdir('home')
    >>> mkdir(home, '.buildout')
    >>> default_cfg = join(home, '.buildout', 'default.cfg')
    >>> write(default_cfg, '''
    ... [buildout]
    ... extensions = demo
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = demo demo2
    ... extensions += demo2
    ... parts =
    ... ''')
    >>> env = dict(HOME=home, USERPROFILE=home)
    >>> print_(system(buildout+' annotate buildout', env=env), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [buildout]
    ...
    extensions= demo
    demo2
        /home/.buildout/default.cfg
    +=  buildout.cfg
    ...
    versions= versions
        DEFAULT_VALUE
    """


def with_extends_increment_in_base():
    r"""
    >>> home = tmpdir('home')
    >>> mkdir(home, '.buildout')
    >>> default_cfg = join(home, '.buildout', 'default.cfg')
    >>> write(default_cfg, '''
    ... [buildout]
    ... extensions = demo
    ... ''')
    >>> write('base.cfg', '''
    ... [buildout]
    ... extensions += demo2
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... extends = base.cfg
    ... parts =
    ... ''')
    >>> env = dict(HOME=home, USERPROFILE=home)
    >>> print_(system(buildout+' annotate buildout', env=env), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [buildout]
    ...
    extensions= demo
    demo2
        /home/.buildout/default.cfg
    +=  base.cfg
    ...
    versions= versions
        DEFAULT_VALUE
    """


def with_extends_increment_in_base2():
    r"""
    >>> home = tmpdir('home')
    >>> mkdir(home, '.buildout')
    >>> default_cfg = join(home, '.buildout', 'default.cfg')
    >>> write(default_cfg, '''
    ... [buildout]
    ... extensions = demo
    ... ''')
    >>> write('base.cfg', '''
    ... [buildout]
    ... ''')
    >>> write('base2.cfg', '''
    ... [buildout]
    ... extensions += demo2
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... extends = base.cfg
    ...           base2.cfg
    ... parts =
    ... ''')
    >>> env = dict(HOME=home, USERPROFILE=home)
    >>> print_(system(buildout+' annotate buildout', env=env), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [buildout]
    ...
    extensions= demo
    demo2
        /home/.buildout/default.cfg
    +=  base2.cfg
    ...
    versions= versions
        DEFAULT_VALUE
    """


def with_extends_increment_in_base2_and_base3():
    r"""
    >>> home = tmpdir('home')
    >>> mkdir(home, '.buildout')
    >>> default_cfg = join(home, '.buildout', 'default.cfg')
    >>> write(default_cfg, '''
    ... [buildout]
    ... extensions = demo
    ... ''')
    >>> write('base.cfg', '''
    ... [buildout]
    ... ''')
    >>> write('base2.cfg', '''
    ... [buildout]
    ... extensions += demo2
    ... ''')
    >>> write('base3.cfg', '''
    ... [buildout]
    ... extensions += demo3
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... extends = base.cfg
    ...           base2.cfg
    ...           base3.cfg
    ... parts =
    ... ''')
    >>> env = dict(HOME=home, USERPROFILE=home)
    >>> print_(system(buildout+' annotate buildout', env=env), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [buildout]
    ...
    extensions= demo
    demo2
    demo3
        /home/.buildout/default.cfg
    +=  base2.cfg
    +=  base3.cfg
    ...
    versions= versions
        DEFAULT_VALUE
    """


def with_extends_increment_in_buildout():
    r"""
    >>> home = tmpdir('home')
    >>> mkdir(home, '.buildout')
    >>> default_cfg = join(home, '.buildout', 'default.cfg')
    >>> write(default_cfg, '''
    ... [buildout]
    ... extensions = demo
    ... ''')
    >>> write('base.cfg', '''
    ... [buildout]
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... extends = base.cfg
    ... extensions += demo2
    ... parts =
    ... ''')
    >>> env = dict(HOME=home, USERPROFILE=home)
    >>> print_(system(buildout+' annotate buildout', env=env), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [buildout]
    ...
    extensions= demo
    demo2
        /home/.buildout/default.cfg
    +=  buildout.cfg
    ...
    versions= versions
        DEFAULT_VALUE
    """


def with_extends_increment_in_buildout_with_base_and_root():
    r"""
    >>> home = tmpdir('home')
    >>> mkdir(home, '.buildout')
    >>> default_cfg = join(home, '.buildout', 'default.cfg')
    >>> write(default_cfg, '''
    ... [buildout]
    ... extensions = demo
    ... ''')
    >>> write('root.cfg', '''
    ... [buildout]
    ... ''')
    >>> write('base.cfg', '''
    ... [buildout]
    ... extends = root.cfg
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... extends = base.cfg
    ... extensions += demo2
    ... parts =
    ... ''')
    >>> env = dict(HOME=home, USERPROFILE=home)
    >>> print_(system(buildout+' annotate buildout', env=env), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [buildout]
    ...
    extensions= demo
    demo2
        /home/.buildout/default.cfg
    +=  buildout.cfg
    ...
    versions= versions
        DEFAULT_VALUE
    """

def no_default_with_extends_increment_in_base2_and_base3():
    r"""
    >>> write('base.cfg', '''
    ... [buildout]
    ... ''')
    >>> write('base2.cfg', '''
    ... [buildout]
    ... extensions += demo2
    ... ''')
    >>> write('base3.cfg', '''
    ... [buildout]
    ... extensions += demo3
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... extends = base.cfg
    ...           base2.cfg
    ...           base3.cfg
    ... parts =
    ... ''')
    >>> print_(system(buildout+' annotate buildout'), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [buildout]
    ...
    extensions= 
    demo2
    demo3
        IMPLICIT_VALUE
    +=  base2.cfg
    +=  base3.cfg
    ...
    versions= versions
        DEFAULT_VALUE
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
