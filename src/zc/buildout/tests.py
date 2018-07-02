# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2009 Zope Foundation and Contributors.
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
from __future__ import print_function
import unittest

from zc.buildout.buildout import print_
from zope.testing import renormalizing, setupstack

import doctest
import manuel.capture
import manuel.doctest
import manuel.testing
import os
import pkg_resources
import re
import shutil
import sys
import tempfile
import unittest
import zc.buildout.easy_install
import zc.buildout.testing
import zipfile

os_path_sep = os.path.sep
if os_path_sep == '\\':
    os_path_sep *= 2


class TestEasyInstall(unittest.TestCase):

    # The contents of a zipped egg, created by setuptools:
    # from setuptools import setup
    # setup(
    #    name='TheProject',
    #    version='3.3',
    # )
    #
    # (we can't run setuptools at runtime, it may not be installed)
    EGG_DATA = (
        b'PK\x03\x04\x14\x00\x00\x00\x08\x00q8\xa8Lg0\xb7ix\x00\x00\x00\xb6\x00'
        b'\x00\x00\x11\x00\x00\x00EGG-INFO/PKG-INFO\xf3M-ILI,I\xd4\rK-*'
        b'\xce\xcc\xcf\xb3R0\xd43\xe0\xf2K\xccM\xb5R\x08\xc9H\r(\xca\xcfJM'
        b'.\xe1\x82\xcb\x1a\xeb\x19s\x05\x97\xe6\xe6&\x16UZ)\x84\xfay\xfb\xf9\x87\xfb'
        b'qy\xe4\xe7\xa6\xea\x16$\xa6\xa7"\x84\x1cKK2\xf2\x8b\xd0\xf9\xba\xa9\xb9\x89'
        b'\x999\x08Q\x9f\xcc\xe4\xd4\xbcb$m.\xa9\xc5\xc9E\x99\x05%`\xbb`\x82\x019\x89%'
        b'i\xf9E\xb9\x08\x11\x00PK\x03\x04\x14\x00\x00\x00\x08\x00q8\xa8L61\xa1'
        b'XL\x00\x00\x00\x87\x00\x00\x00\x14\x00\x00\x00EGG-INFO/SOURCES.txt\x0b\xc9H'
        b'\r(\xca\xcfJM.\xd1KMO\xd7\xcd\xccK\xcb\xd7\x0f\xf0v\xd7\xf5\xf4s'
        b'\xf3\xe7\n\xc1"\x19\xec\x1f\x1a\xe4\xec\x1a\xacWRQ\x82U>%\xb5 5/%5/\xb92>\'3'
        b'/\xbb\x18\xa7\xc2\x92\xfc\x82\xf8\x9c\xd4\xb2\xd4\x1c\x90\n\x00PK\x03'
        b'\x04\x14\x00\x00\x00\x08\x00q8\xa8L\x93\x06\xd72\x03\x00\x00\x00\x01'
        b'\x00\x00\x00\x1d\x00\x00\x00EGG-INFO/dependency_links.txt\xe3\x02\x00P'
        b'K\x03\x04\x14\x00\x00\x00\x08\x00q8\xa8L\x93\x06\xd72\x03\x00\x00'
        b'\x00\x01\x00\x00\x00\x16\x00\x00\x00EGG-INFO/top_level.txt\xe3\x02\x00PK'
        b'\x03\x04\x14\x00\x00\x00\x08\x00q8\xa8L\x93\x06\xd72\x03\x00\x00\x00'
        b'\x01\x00\x00\x00\x11\x00\x00\x00EGG-INFO/zip-safe\xe3\x02\x00PK\x01\x02'
        b'\x14\x03\x14\x00\x00\x00\x08\x00q8\xa8Lg0\xb7ix\x00\x00\x00\xb6\x00\x00\x00'
        b'\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa4\x81\x00\x00\x00\x00EG'
        b'G-INFO/PKG-INFOPK\x01\x02\x14\x03\x14\x00\x00\x00\x08\x00q8\xa8L61\xa1XL'
        b'\x00\x00\x00\x87\x00\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\xa4\x81\xa7\x00\x00\x00EGG-INFO/SOURCES.txtPK\x01'
        b'\x02\x14\x03\x14\x00\x00\x00\x08\x00q8\xa8L\x93\x06\xd72\x03\x00\x00'
        b'\x00\x01\x00\x00\x00\x1d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\xa4\x81%\x01\x00\x00EGG-INFO/dependency_links.txtPK\x01\x02'
        b'\x14\x03\x14\x00\x00\x00\x08\x00q8\xa8L\x93\x06\xd72\x03\x00\x00\x00'
        b'\x01\x00\x00\x00\x16\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\xa4\x81c\x01\x00\x00EGG-INFO/top_level.txtPK\x01\x02\x14\x03\x14\x00'
        b'\x00\x00\x08\x00q8\xa8L\x93\x06\xd72\x03\x00\x00\x00\x01\x00\x00\x00'
        b'\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa4\x81\x9a\x01\x00\x00EG'
        b'G-INFO/zip-safePK\x05\x06\x00\x00\x00\x00\x05\x00\x05\x00O\x01\x00\x00\xcc'
        b'\x01\x00\x00\x00\x00'
    )

    def setUp(self):
        self.cwd = os.getcwd()
        self.temp_dir = tempfile.mkdtemp('.buildouttest')
        self.project_dir = os.path.join(self.temp_dir, 'TheProject')
        self.project_dist_dir = os.path.join(self.temp_dir, 'dist')
        os.mkdir(self.project_dist_dir)
        self.egg_path = os.path.join(self.project_dist_dir, 'TheProject.egg')
        os.mkdir(self.project_dir)
        self.setup_path = os.path.join(self.project_dir, 'setup.py')
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.temp_dir)

    def _make_egg(self):
        with open(self.egg_path, 'wb') as f:
            f.write(self.EGG_DATA)


    def _get_distro_and_egg_path(self):
        # Returns a distribution with a version of '3.3.0',
        # but an egg with a version of '3.3'
        self._make_egg()
        from distutils.dist import Distribution
        dist = Distribution()
        dist.project_name = 'TheProject'
        dist.version = '3.3.0'
        dist.parsed_version = pkg_resources.parse_version(dist.version)

        return dist, self.egg_path

    def test_get_matching_dist_in_location_uses_parsed_version(self):
        # https://github.com/buildout/buildout/pull/452
        # An egg built with the version '3.3' should match a distribution
        # looking for '3.3.0'
        dist, location = self._get_distro_and_egg_path()

        result = zc.buildout.easy_install._get_matching_dist_in_location(
            dist,
            self.project_dist_dir
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.version, '3.3')

    def test_move_to_eggs_dir_and_compile(self):
        # https://github.com/buildout/buildout/pull/452
        # An egg built with the version '3.3' should match a distribution
        # looking for '3.3.0'

        dist, location = self._get_distro_and_egg_path()
        dist.location = location

        dest = os.path.join(self.temp_dir, 'NewLoc')

        result = zc.buildout.easy_install._move_to_eggs_dir_and_compile(
            dist,
            dest
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.version, '3.3')
        self.assertIn(dest, result.location)


def develop_w_non_setuptools_setup_scripts():
    """
We should be able to deal with setup scripts that aren't setuptools based.

    >>> mkdir('foo')
    >>> write('foo', 'setup.py',
    ... '''
    ... from distutils.core import setup
    ... setup(name="foo")
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = foo
    ... parts =
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'

    >>> ls('develop-eggs')
    -  foo.egg-link
    -  zc.recipe.egg.egg-link

    """

def develop_verbose():
    """
We should be able to deal with setup scripts that aren't setuptools based.

    >>> mkdir('foo')
    >>> write('foo', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name="foo")
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = foo
    ... parts =
    ... ''')

    >>> print_(system(join('bin', 'buildout')+' -vv'), end='')
    ... # doctest: +ELLIPSIS
    Installing...
    Develop: '/sample-buildout/foo'
    ...
    Installed /sample-buildout/foo
    ...

    >>> ls('develop-eggs')
    -  foo.egg-link
    -  zc.recipe.egg.egg-link

    >>> print_(system(join('bin', 'buildout')+' -vvv'), end='')
    ... # doctest: +ELLIPSIS
    Installing...
    Develop: '/sample-buildout/foo'
    in: '/sample-buildout/foo'
    ... -q develop -mN -d /sample-buildout/develop-eggs/...


    """

def buildout_error_handling():
    r"""Buildout error handling

Asking for a section that doesn't exist, yields a missing section error:

    >>> import os
    >>> os.chdir(sample_buildout)
    >>> import zc.buildout.buildout
    >>> buildout = zc.buildout.buildout.Buildout('buildout.cfg', [])
    >>> buildout['eek']
    Traceback (most recent call last):
    ...
    MissingSection: The referenced section, 'eek', was not defined.

Asking for an option that doesn't exist, a MissingOption error is raised:

    >>> buildout['buildout']['eek']
    Traceback (most recent call last):
    ...
    MissingOption: Missing option: buildout:eek

It is an error to create a variable-reference cycle:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... x = ${buildout:y}
    ... y = ${buildout:z}
    ... z = ${buildout:x}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
      Getting option buildout:y.
      Getting option buildout:z.
      Getting option buildout:x.
    Error: Circular reference in substitutions.

It is an error to use funny characters in variable references:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${bui$ldout:y}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
    Error: The section name in substitution, ${bui$ldout:y},
    has invalid characters.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y{z}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
    Error: The option name in substitution, ${buildout:y{z},
    has invalid characters.

and too have too many or too few colons:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${parts}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
    Error: The substitution, ${parts},
    doesn't contain a colon.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y:z}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
    Error: The substitution, ${buildout:y:z},
    has too many colons.

All parts have to have a section:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Installing.
      Getting section x.
    Error: The referenced section, 'x', was not defined.

and all parts have to have a specified recipe:


    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ...
    ... [x]
    ... foo = 1
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Installing.
    Error: Missing option: x:recipe

"""

make_dist_that_requires_setup_py_template = """
from setuptools import setup
setup(name=%r, version=%r,
      install_requires=%r,
      )
"""

def make_dist_that_requires(dest, name, requires=[], version=1, egg=''):
    os.mkdir(os.path.join(dest, name))
    open(os.path.join(dest, name, 'setup.py'), 'w').write(
        make_dist_that_requires_setup_py_template
        % (name, version, requires)
        )

def show_who_requires_when_there_is_a_conflict():
    """
It's a pain when we require eggs that have requirements that are
incompatible. We want the error we get to tell us what is missing.

Let's make a few develop distros, some of which have incompatible
requirements.

    >>> make_dist_that_requires(sample_buildout, 'sampley',
    ...                         ['demoneeded ==1.0'])
    >>> make_dist_that_requires(sample_buildout, 'samplez',
    ...                         ['demoneeded ==1.1'])

Now, let's create a buildout that requires y and z:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = sampley samplez
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = sampley
    ...        samplez
    ... ''' % globals())

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/sampley'
    Develop: '/sample-buildout/samplez'
    Installing eggs.
    Getting distribution for 'demoneeded==1.1'.
    Got demoneeded 1.1.
    Version and requirements information containing demoneeded:
      Requirement of samplez: demoneeded==1.1
      Requirement of sampley: demoneeded==1.0
    While:
      Installing eggs.
    Error: There is a version conflict.
    We already have: demoneeded 1.1
    but sampley 1 requires 'demoneeded==1.0'.

Here, we see that sampley required an older version of demoneeded. What
if we hadn't required sampley ourselves:

    >>> make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    >>> make_dist_that_requires(sample_buildout, 'sampleb',
    ...                         ['sampley', 'samplea'])
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = sampley samplez samplea sampleb
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = samplea
    ...        samplez
    ... ''' % globals())

If we use the verbose switch, we can see where requirements are coming from:

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    We have a develop egg: zc.buildout 1.0.0
    We have the best distribution that satisfies 'setuptools'.
    Picked: setuptools = 0.7
    Develop: '/sample-buildout/sampley'
    Develop: '/sample-buildout/samplez'
    Develop: '/sample-buildout/samplea'
    Develop: '/sample-buildout/sampleb'
    ...
    Installing eggs.
    Installing 'samplea', 'samplez'.
    We have a develop egg: samplea 1
    We have a develop egg: samplez 1
    Getting required 'demoneeded==1.1'
      required by samplez 1.
    We have the distribution that satisfies 'demoneeded==1.1'.
    Getting required 'sampleb'
      required by samplea 1.
    We have a develop egg: sampleb 1
    Getting required 'sampley'
      required by sampleb 1.
    We have a develop egg: sampley 1
    Version and requirements information containing demoneeded:
      Requirement of samplez: demoneeded==1.1
      Requirement of sampley: demoneeded==1.0
    While:
      Installing eggs.
    Error: There is a version conflict.
    We already have: demoneeded 1.1
    but sampley 1 requires 'demoneeded==1.0'.
    """

def version_conflict_rendering():
    """

We use the arguments passed by pkg_resources.VersionConflict to construct a
nice error message:

    >>> error = pkg_resources.VersionConflict('pkg1 2.1', 'pkg1 1.0')
    >>> ws = []  # Not relevant for this test
    >>> print_(zc.buildout.easy_install.VersionConflict(
    ...     error, ws)) # doctest: +ELLIPSIS
    There is a version conflict...

But sometimes pkg_resources passes a nicely formatted string itself already.
Extracting the original arguments fails in that case, so we just show the string.

    >>> error = pkg_resources.VersionConflict('pkg1 2.1 is simply wrong')
    >>> ws = []  # Not relevant for this test
    >>> print_(zc.buildout.easy_install.VersionConflict(
    ...     error, ws)) # doctest: +ELLIPSIS
    There is a version conflict.
    pkg1 2.1 is simply wrong

    """

def show_who_requires_missing_distributions():
    """

When working with a lot of eggs, which require eggs recursively, it
can be hard to tell why we're requiring things we can't
find. Fortunately, buildout will tell us who's asking for something
that we can't find. when run in verbose mode

    >>> make_dist_that_requires(sample_buildout, 'sampley', ['demoneeded'])
    >>> make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    >>> make_dist_that_requires(sample_buildout, 'sampleb',
    ...                         ['sampley', 'samplea'])
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = sampley samplea sampleb
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = samplea
    ... ''')

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing ...
    Installing 'samplea'.
    We have a develop egg: samplea 1
    Getting required 'sampleb'
      required by samplea 1.
    We have a develop egg: sampleb 1
    Getting required 'sampley'
      required by sampleb 1.
    We have a develop egg: sampley 1
    Getting required 'demoneeded'
      required by sampley 1.
    We have no distributions for demoneeded that satisfies 'demoneeded'.
    ...
    While:
      Installing eggs.
      Getting distribution for 'demoneeded'.
    Error: Couldn't find a distribution for 'demoneeded'.
    """

def show_who_requires_picked_versions():
    """

The show-picked-versions prints the versions, but it also prints who
required the picked distributions.
We do not need to run in verbose mode for that to work:

    >>> make_dist_that_requires(sample_buildout, 'sampley', ['setuptools'])
    >>> make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    >>> make_dist_that_requires(sample_buildout, 'sampleb',
    ...                         ['sampley', 'samplea'])
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... show-picked-versions = true
    ... develop = sampley samplea sampleb
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = samplea
    ... ''')

    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Develop: ...
    Installing eggs.
    Versions had to be automatically picked.
    The following part definition lists the versions picked:
    [versions]
    <BLANKLINE>
    # Required by:
    # sampley==1
    setuptools = 0.7
    """

def test_comparing_saved_options_with_funny_characters():
    """
If an option has newlines, extra/odd spaces or a %, we need to make sure
the comparison with the saved value works correctly.

    >>> mkdir(sample_buildout, 'recipes')
    >>> write(sample_buildout, 'recipes', 'debug.py',
    ... '''
    ... class Debug:
    ...     def __init__(self, buildout, name, options):
    ...         options['debug'] = \"\"\"  <zodb>
    ...
    ...   <filestorage>
    ...     path foo
    ...   </filestorage>
    ...
    ... </zodb>
    ...      \"\"\"
    ...         options['debug1'] = \"\"\"
    ... <zodb>
    ...
    ...   <filestorage>
    ...     path foo
    ...   </filestorage>
    ...
    ... </zodb>
    ... \"\"\"
    ...         options['debug2'] = '  x  '
    ...         options['debug3'] = '42'
    ...         options['format'] = '%3d'
    ...
    ...     def install(self):
    ...         open('t', 'w').write('t')
    ...         return 't'
    ...
    ...     update = install
    ... ''')


    >>> write(sample_buildout, 'recipes', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(
    ...     name = "recipes",
    ...     entry_points = {'zc.buildout': ['default = debug:Debug']},
    ...     )
    ... ''')

    >>> write(sample_buildout, 'recipes', 'README.txt', " ")

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = debug
    ...
    ... [debug]
    ... recipe = recipes
    ... ''')

    >>> os.chdir(sample_buildout)
    >>> buildout = os.path.join(sample_buildout, 'bin', 'buildout')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Installing debug.

If we run the buildout again, we shoudn't get a message about
uninstalling anything because the configuration hasn't changed.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Updating debug.
"""

def finding_eggs_as_local_directories():
    r"""
It is possible to set up find-links so that we could install from
a local directory that may contained unzipped eggs.

    >>> src = tmpdir('src')
    >>> write(src, 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='demo', py_modules=[''],
    ...    zip_safe=False, version='1.0', author='bob', url='bob',
    ...    author_email='bob')
    ... ''')

    >>> write(src, 't.py', '#\n')
    >>> write(src, 'README.txt', '')
    >>> _ = system(join('bin', 'buildout')+' setup ' + src + ' bdist_egg')

Install it so it gets unzipped:

    >>> d1 = tmpdir('d1')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo'], d1, links=[join(src, 'dist')],
    ...     )

    >>> ls(d1)
    d  demo-1.0-py2.4.egg

Then try to install it again:

    >>> d2 = tmpdir('d2')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo'], d2, links=[d1],
    ...     )

    >>> ls(d2)
    d  demo-1.0-py2.4.egg

    """

def create_sections_on_command_line():
    """
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... x = ${foo:bar}
    ... ''')

    >>> print_(system(buildout + ' foo:bar=1 -vv'), end='')
    ...        # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    ...
    [foo]
    bar = 1
    ...

    """

def test_help():
    """
    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')+' -h'))
    ... # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    Usage: buildout [options] [assignments] [command [command arguments]]
    <BLANKLINE>
    Options:
    <BLANKLINE>
      -c config_file
    <BLANKLINE>
        Specify the path to the buildout configuration file to be used.
        This defaults to the file named "buildout.cfg" in the current
        working directory.
    ...
      -h, --help
    ...

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')
    ...              +' --help'))
    ... # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    Usage: buildout [options] [assignments] [command [command arguments]]
    <BLANKLINE>
    Options:
    <BLANKLINE>
      -c config_file
    <BLANKLINE>
        Specify the path to the buildout configuration file to be used.
        This defaults to the file named "buildout.cfg" in the current
        working directory.
    ...
      -h, --help
    ...
    """

def test_version():
    """
    >>> buildout = os.path.join(sample_buildout, 'bin', 'buildout')
    >>> print_(system(buildout+' --version'))
    ... # doctest: +ELLIPSIS
    buildout version ...

    """

def test_bootstrap_with_extension():
    """
We had a problem running a bootstrap with an extension.  Let's make
sure it is fixed.  Basically, we don't load extensions when
bootstrapping.

    >>> d = tmpdir('sample-bootstrap')

    >>> write(d, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... extensions = some_awsome_extension
    ... parts =
    ... ''')

    >>> os.chdir(d)
    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')
    ...              + ' bootstrap'), end='')
    Creating directory '/sample-bootstrap/eggs'.
    Creating directory '/sample-bootstrap/bin'.
    Creating directory '/sample-bootstrap/parts'.
    Creating directory '/sample-bootstrap/develop-eggs'.
    Generated script '/sample-bootstrap/bin/buildout'.
    """


def bug_92891_bootstrap_crashes_with_egg_recipe_in_buildout_section():
    """
    >>> d = tmpdir('sample-bootstrap')

    >>> write(d, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = buildout
    ... eggs-directory = eggs
    ...
    ... [buildout]
    ... recipe = zc.recipe.egg
    ... eggs = zc.buildout
    ... scripts = buildout=buildout
    ... ''')

    >>> os.chdir(d)
    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')
    ...              + ' bootstrap'), end='')
    Creating directory '/sample-bootstrap/eggs'.
    Creating directory '/sample-bootstrap/bin'.
    Creating directory '/sample-bootstrap/parts'.
    Creating directory '/sample-bootstrap/develop-eggs'.
    Generated script '/sample-bootstrap/bin/buildout'.

    >>> print_(system(os.path.join('bin', 'buildout')), end='')
    Unused options for buildout: 'scripts' 'eggs'.

    """

def removing_eggs_from_develop_section_causes_egg_link_to_be_removed():
    '''
    >>> cd(sample_buildout)

Create a develop egg:

    >>> mkdir('foo')
    >>> write('foo', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='foox')
    ... """)
    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = foo
    ... parts =
    ... """)

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'

    >>> ls('develop-eggs')
    -  foox.egg-link
    -  zc.recipe.egg.egg-link

Create another:

    >>> mkdir('bar')
    >>> write('bar', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='fooy')
    ... """)
    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = foo bar
    ... parts =
    ... """)

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'
    Develop: '/sample-buildout/bar'

    >>> ls('develop-eggs')
    -  foox.egg-link
    -  fooy.egg-link
    -  zc.recipe.egg.egg-link

Remove one:

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = bar
    ... parts =
    ... """)
    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/bar'

It is gone

    >>> ls('develop-eggs')
    -  fooy.egg-link
    -  zc.recipe.egg.egg-link

Remove the other:

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... parts =
    ... """)
    >>> print_(system(join('bin', 'buildout')), end='')

All gone

    >>> ls('develop-eggs')
    -  zc.recipe.egg.egg-link
    '''


def add_setuptools_to_dependencies_when_namespace_packages():
    '''
Often, a package depends on setuptools solely by virtue of using
namespace packages. In this situation, package authors often forget to
declare setuptools as a dependency. This is a mistake, but,
unfortunately, a common one that we need to work around.  If an egg
uses namespace packages and does not include setuptools as a dependency,
we will still include setuptools in the working set.  If we see this for
a develop egg, we will also generate a warning.

    >>> mkdir('foo')
    >>> mkdir('foo', 'src')
    >>> mkdir('foo', 'src', 'stuff')
    >>> write('foo', 'src', 'stuff', '__init__.py',
    ... """__import__('pkg_resources').declare_namespace(__name__)
    ... """)
    >>> mkdir('foo', 'src', 'stuff', 'foox')
    >>> write('foo', 'src', 'stuff', 'foox', '__init__.py', '')
    >>> write('foo', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='foox',
    ...       namespace_packages = ['stuff'],
    ...       package_dir = {'': 'src'},
    ...       packages = ['stuff', 'stuff.foox'],
    ...       )
    ... """)
    >>> write('foo', 'README.txt', '')

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = foo
    ... parts =
    ... """)

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'

Now, if we generate a working set using the egg link, we will get a warning
and we will get setuptools included in the working set.

    >>> import logging, zope.testing.loggingsupport
    >>> handler = zope.testing.loggingsupport.InstalledHandler(
    ...        'zc.buildout.easy_install', level=logging.WARNING)
    >>> logging.getLogger('zc.buildout.easy_install').propagate = False

    >>> def get_working_set(*project_names):
    ...     paths = [join(sample_buildout, 'eggs'),
    ...              join(sample_buildout, 'develop-eggs')]
    ...     return [
    ...        dist.project_name
    ...        for dist in zc.buildout.easy_install.working_set(
    ...            project_names, sys.executable, paths)
    ...     ]
    >>> get_working_set('foox')
    ['foox', 'setuptools']

    >>> print_(handler)
    zc.buildout.easy_install WARNING
      Develop distribution: foox 0.0.0
    uses namespace packages but the distribution does not require setuptools.

    >>> handler.clear()

On the other hand, if we have a zipped egg, rather than a develop egg:

    >>> os.remove(join('develop-eggs', 'foox.egg-link'))

    >>> _ = system(join('bin', 'buildout') + ' setup foo bdist_egg')
    >>> foox_dist = join('foo', 'dist')
    >>> import glob
    >>> [foox_egg] = glob.glob(join(foox_dist, 'foox-*.egg'))
    >>> _ = shutil.copy(foox_egg, join(sample_buildout, 'eggs'))
    >>> ls('develop-eggs')
    -  zc.recipe.egg.egg-link

    >>> ls('eggs') # doctest: +ELLIPSIS
    -  foox-0.0.0-py2.4.egg
    d  setuptools.eggpyN.N.egg
    ...

We do not get a warning, but we do get setuptools included in the working set:

    >>> get_working_set('foox')
    ['foox', 'setuptools']

    >>> print_(handler, end='')

Likewise for an unzipped egg:

    >>> foox_egg_basename = os.path.basename(foox_egg)
    >>> os.remove(join(sample_buildout, 'eggs', foox_egg_basename))
    >>> _ = zc.buildout.easy_install.install(
    ...     ['foox'], join(sample_buildout, 'eggs'), links=[foox_dist],
    ...     index='file://' + foox_dist)
    >>> ls('develop-eggs')
    -  zc.recipe.egg.egg-link

    >>> get_working_set('foox')
    ['foox', 'setuptools']

    >>> print_(handler, end='')

We get the same behavior if it is a dependency that uses a
namespace package.


    >>> mkdir('bar')
    >>> write('bar', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='bar', install_requires = ['foox'])
    ... """)
    >>> write('bar', 'README.txt', '')

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = foo bar
    ... parts =
    ... """)

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'
    Develop: '/sample-buildout/bar'

    >>> get_working_set('bar')
    ['bar', 'foox', 'setuptools']

    >>> print_(handler, end='')
    zc.buildout.easy_install WARNING
      Develop distribution: foox 0.0.0
    uses namespace packages but the distribution does not require setuptools.

On the other hand, if the distribution uses ``pkgutil.extend_path()`` to
implement its namespaces, even if just as fallback from the absence of
``pkg_resources``, then ``setuptools`` should not be added as requirement to
its unzipped egg:

    >>> foox_installed_egg = join(sample_buildout, 'eggs', foox_egg_basename)
    >>> namespace_init = join(foox_installed_egg, 'stuff', '__init__.py')
    >>> write(namespace_init,
    ... """try:
    ...     __import__('pkg_resources').declare_namespace(__name__)
    ... except ImportError:
    ...     __path__ = __import__('pkgutil').extend_path(__path__, __name__)
    ... """)

    >>> os.remove(join('develop-eggs', 'foox.egg-link'))
    >>> os.remove(join('develop-eggs', 'bar.egg-link'))
    >>> get_working_set('foox')
    ['foox']

The same goes for packages using PEP420 namespaces

    >>> os.remove(namespace_init)
    >>> get_working_set('foox')
    ['foox']

Cleanup:

    >>> logging.getLogger('zc.buildout.easy_install').propagate = True
    >>> handler.uninstall()

    '''

def develop_preserves_existing_setup_cfg():
    """

See "Handling custom build options for extensions in develop eggs" in
easy_install.txt.  This will be very similar except that we'll have an
existing setup.cfg:

    >>> write(extdemo, "setup.cfg",
    ... '''
    ... # sampe cfg file
    ...
    ... [foo]
    ... bar = 1
    ...
    ... [build_ext]
    ... define = X,Y
    ... ''')

    >>> mkdir('include')
    >>> write('include', 'extdemo.h',
    ... '''
    ... #define EXTDEMO 42
    ... ''')

    >>> dest = tmpdir('dest')
    >>> zc.buildout.easy_install.develop(
    ...   extdemo, dest,
    ...   {'include-dirs': os.path.join(sample_buildout, 'include')})
    '/dest/extdemo.egg-link'

    >>> ls(dest)
    -  extdemo.egg-link

    >>> cat(extdemo, "setup.cfg")
    <BLANKLINE>
    # sampe cfg file
    <BLANKLINE>
    [foo]
    bar = 1
    <BLANKLINE>
    [build_ext]
    define = X,Y

"""

def uninstall_recipes_used_for_removal():
    r"""
Uninstall recipes need to be called when a part is removed too:

    >>> mkdir("recipes")
    >>> write("recipes", "setup.py",
    ... '''
    ... from setuptools import setup
    ... setup(name='recipes',
    ...       entry_points={
    ...          'zc.buildout': ["demo=demo:Install"],
    ...          'zc.buildout.uninstall': ["demo=demo:uninstall"],
    ...          })
    ... ''')

    >>> write("recipes", "demo.py",
    ... r'''
    ... import sys
    ... class Install:
    ...     def __init__(*args): pass
    ...     def install(self):
    ...         sys.stdout.write('installing\n')
    ...         return ()
    ... def uninstall(name, options):
    ...     sys.stdout.write('uninstalling\n')
    ... ''')

    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts = demo
    ... [demo]
    ... recipe = recipes:demo
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipes'
    Installing demo.
    installing


    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts = demo
    ... [demo]
    ... recipe = recipes:demo
    ... x = 1
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling demo.
    Running uninstall recipe.
    uninstalling
    Installing demo.
    installing


    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts =
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling demo.
    Running uninstall recipe.
    uninstalling

"""

def extensions_installed_as_eggs_work_in_offline_mode():
    '''
    >>> mkdir('demo')

    >>> write('demo', 'demo.py',
    ... r"""
    ... import sys
    ... def print_(*args):
    ...     sys.stdout.write(' '.join(map(str, args)) + '\\n')
    ... def ext(buildout):
    ...     print_('ext', sorted(buildout))
    ... """)

    >>> write('demo', 'setup.py',
    ... """
    ... from setuptools import setup
    ...
    ... setup(
    ...     name = "demo",
    ...     py_modules=['demo'],
    ...     entry_points = {'zc.buildout.extension': ['ext = demo:ext']},
    ...     )
    ... """)

    >>> bdist_egg(join(sample_buildout, "demo"), sys.executable,
    ...           join(sample_buildout, "eggs"))

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... extensions = demo
    ... parts =
    ... offline = true
    ... """)

    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    ext ['buildout', 'versions']


    '''

def changes_in_svn_or_CVS_dont_affect_sig():
    """

If we have a develop recipe, it's signature shouldn't be affected to
changes in .svn or CVS directories.

    >>> mkdir('recipe')
    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe',
    ...       entry_points={'zc.buildout': ['default=foo:Foo']})
    ... ''')
    >>> write('recipe', 'foo.py',
    ... '''
    ... class Foo:
    ...     def __init__(*args): pass
    ...     def install(*args): return ()
    ...     update = install
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipe
    ... parts = foo
    ...
    ... [foo]
    ... recipe = recipe
    ... ''')


    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Installing foo.

    >>> mkdir('recipe', '.svn')
    >>> mkdir('recipe', 'CVS')
    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Updating foo.

    >>> write('recipe', '.svn', 'x', '1')
    >>> write('recipe', 'CVS', 'x', '1')

    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Updating foo.

    """

if hasattr(os, 'symlink'):
    def bug_250537_broken_symlink_doesnt_affect_sig():
        """
If we have a develop recipe, it's signature shouldn't be affected by
broken symlinks, and better yet, computing the hash should not break
because of the missing target file.

    >>> mkdir('recipe')
    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe',
    ...       entry_points={'zc.buildout': ['default=foo:Foo']})
    ... ''')
    >>> write('recipe', 'foo.py',
    ... '''
    ... class Foo:
    ...     def __init__(*args): pass
    ...     def install(*args): return ()
    ...     update = install
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipe
    ... parts = foo
    ...
    ... [foo]
    ... recipe = recipe
    ... ''')


    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Installing foo.

    >>> write('recipe', 'some-file', '1')
    >>> os.symlink(join('recipe', 'some-file'),
    ...            join('recipe', 'another-file'))
    >>> remove('recipe', 'some-file')

    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Updating foo.

    """

def unicode_filename_doesnt_break_hash():
    """
Buildout's _dir_hash() used to break on non-ascii filenames on python 2.

    >>> mkdir('héhé')
    >>> write('héhé', 'héhé.py',
    ... '''
    ... print('Example filename from pyramid tests')
    ... ''')
    >>> from zc.buildout.buildout import _dir_hash
    >>> dont_care = _dir_hash('héhé')

    """

def o_option_sets_offline():
    """
    >>> print_(system(join(sample_buildout, 'bin', 'buildout')+' -vvo'), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    ...
    offline = true
    ...
    """

def recipe_upgrade():
    r"""

The buildout will upgrade recipes in newest (and non-offline) mode.

Let's create a recipe egg

    >>> mkdir('recipe')
    >>> write('recipe', 'recipe.py',
    ... r'''
    ... import sys
    ... class Recipe:
    ...     def __init__(*a): pass
    ...     def install(self):
    ...         sys.stdout.write('recipe v1\n')
    ...         return ()
    ...     update = install
    ... ''')

    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe', version='1', py_modules=['recipe'],
    ...       entry_points={'zc.buildout': ['default = recipe:Recipe']},
    ...       )
    ... ''')

    >>> write('recipe', 'README', '')

    >>> print_(system(buildout+' setup recipe bdist_egg')) # doctest: +ELLIPSIS
    Running setup script 'recipe/setup.py'.
    ...

    >>> rmdir('recipe', 'build')

And update our buildout to use it.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = foo
    ... find-links = %s
    ...
    ... [foo]
    ... recipe = recipe
    ... ''' % join('recipe', 'dist'))

    >>> print_(system(buildout), end='')
    Getting distribution for 'recipe'.
    Got recipe 1.
    Installing foo.
    recipe v1

Now, if we update the recipe egg:

    >>> write('recipe', 'recipe.py',
    ... r'''
    ... import sys
    ... class Recipe:
    ...     def __init__(*a): pass
    ...     def install(self):
    ...         sys.stdout.write('recipe v2\n')
    ...         return ()
    ...     update = install
    ... ''')

    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe', version='2', py_modules=['recipe'],
    ...       entry_points={'zc.buildout': ['default = recipe:Recipe']},
    ...       )
    ... ''')


    >>> print_(system(buildout+' setup recipe bdist_egg')) # doctest: +ELLIPSIS
    Running setup script 'recipe/setup.py'.
    ...

We won't get the update if we specify -N:

    >>> print_(system(buildout+' -N'), end='')
    Updating foo.
    recipe v1

or if we use -o:

    >>> print_(system(buildout+' -o'), end='')
    Updating foo.
    recipe v1

But we will if we use neither of these:

    >>> print_(system(buildout), end='')
    Getting distribution for 'recipe'.
    Got recipe 2.
    Uninstalling foo.
    Installing foo.
    recipe v2

We can also select a particular recipe version:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = foo
    ... find-links = %s
    ...
    ... [foo]
    ... recipe = recipe ==1
    ... ''' % join('recipe', 'dist'))

    >>> print_(system(buildout), end='')
    Uninstalling foo.
    Installing foo.
    recipe v1

    """

def update_adds_to_uninstall_list():
    """

Paths returned by the update method are added to the list of paths to
uninstall

    >>> mkdir('recipe')
    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe',
    ...       entry_points={'zc.buildout': ['default = recipe:Recipe']},
    ...       )
    ... ''')

    >>> write('recipe', 'recipe.py',
    ... '''
    ... import os
    ... class Recipe:
    ...     def __init__(*_): pass
    ...     def install(self):
    ...         r = ('a', 'b', 'c')
    ...         for p in r: os.mkdir(p)
    ...         return r
    ...     def update(self):
    ...         r = ('c', 'd', 'e')
    ...         for p in r:
    ...             if not os.path.exists(p):
    ...                os.mkdir(p)
    ...         return r
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipe
    ... parts = foo
    ...
    ... [foo]
    ... recipe = recipe
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipe'
    Installing foo.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipe'
    Updating foo.

    >>> cat('.installed.cfg') # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    [buildout]
    ...
    [foo]
    __buildout_installed__ = a
    	b
    	c
    	d
    	e
    __buildout_signature__ = ...

"""

def log_when_there_are_not_local_distros():
    """
    >>> from zope.testing.loggingsupport import InstalledHandler
    >>> handler = InstalledHandler('zc.buildout.easy_install')
    >>> import logging
    >>> logger = logging.getLogger('zc.buildout.easy_install')
    >>> old_propogate = logger.propagate
    >>> logger.propagate = False

    >>> dest = tmpdir('sample-install')
    >>> import zc.buildout.easy_install
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo==0.2'], dest,
    ...     links=[link_server], index=link_server+'index/')

    >>> print_(handler) # doctest: +ELLIPSIS
    zc.buildout.easy_install DEBUG
      Installing 'demo==0.2'.
    zc.buildout.easy_install DEBUG
      We have no distributions for demo that satisfies 'demo==0.2'.
    ...

    >>> handler.uninstall()
    >>> logger.propagate = old_propogate

    """

def internal_errors():
    """Internal errors are clearly marked and don't generate tracebacks:

    >>> mkdir(sample_buildout, 'recipes')

    >>> write(sample_buildout, 'recipes', 'mkdir.py',
    ... '''
    ... class Mkdir:
    ...     def __init__(self, buildout, name, options):
    ...         self.name, self.options = name, options
    ...         options['path'] = os.path.join(
    ...                               buildout['buildout']['directory'],
    ...                               options['path'],
    ...                               )
    ... ''')

    >>> write(sample_buildout, 'recipes', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name = "recipes",
    ...       entry_points = {'zc.buildout': ['mkdir = mkdir:Mkdir']},
    ...       )
    ... ''')

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data-dir
    ...
    ... [data-dir]
    ... recipe = recipes:mkdir
    ... ''')

    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Develop: '/sample-buildout/recipes'
    While:
      Installing.
      Getting section data-dir.
      Initializing section data-dir.
    <BLANKLINE>
    An internal error occurred due to a bug in either zc.buildout or in a
    recipe being used:
    Traceback (most recent call last):
    ...
    NameError: global name 'os' is not defined
    """

def whine_about_unused_options():
    '''

    >>> write('foo.py',
    ... """
    ... class Foo:
    ...
    ...     def __init__(self, buildout, name, options):
    ...         self.name, self.options = name, options
    ...         options['x']
    ...
    ...     def install(self):
    ...         self.options['y']
    ...         return ()
    ... """)

    >>> write('setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name = "foo",
    ...       entry_points = {'zc.buildout': ['default = foo:Foo']},
    ...       )
    ... """)

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = .
    ... parts = foo
    ... a = 1
    ...
    ... [foo]
    ... recipe = foo
    ... x = 1
    ... y = 1
    ... z = 1
    ... """)

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/.'
    Unused options for buildout: 'a'.
    Installing foo.
    Unused options for foo: 'z'.
    '''

def abnormal_exit():
    """
People sometimes hit control-c while running a builout. We need to make
sure that the installed database Isn't corrupted.  To test this, we'll create
some evil recipes that exit uncleanly:

    >>> mkdir('recipes')
    >>> write('recipes', 'recipes.py',
    ... '''
    ... import os
    ...
    ... class Clean:
    ...     def __init__(*_): pass
    ...     def install(_): return ()
    ...     def update(_): pass
    ...
    ... class EvilInstall(Clean):
    ...     def install(_): os._exit(1)
    ...
    ... class EvilUpdate(Clean):
    ...     def update(_): os._exit(1)
    ... ''')

    >>> write('recipes', 'setup.py',
    ... '''
    ... import setuptools
    ... setuptools.setup(name='recipes',
    ...    entry_points = {
    ...      'zc.buildout': [
    ...          'clean = recipes:Clean',
    ...          'evil_install = recipes:EvilInstall',
    ...          'evil_update = recipes:EvilUpdate',
    ...          'evil_uninstall = recipes:Clean',
    ...          ],
    ...       },
    ...     )
    ... ''')

Now let's look at 3 cases:

1. We exit during installation after installing some other parts:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:clean
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:evil_install
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Installing p1.
    Installing p2.
    Installing p3.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Updating p1.
    Updating p2.
    Installing p3.

    >>> print_(system(buildout+' buildout:parts='), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling p2.
    Uninstalling p1.

2. We exit while updating:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:clean
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:evil_update
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Installing p1.
    Installing p2.
    Installing p3.
    Installing p4.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Updating p1.
    Updating p2.
    Updating p3.

    >>> print_(system(buildout+' buildout:parts='), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling p2.
    Uninstalling p1.
    Uninstalling p4.
    Uninstalling p3.

3. We exit while installing or updating after uninstalling:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:evil_update
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:clean
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Installing p1.
    Installing p2.
    Installing p3.
    Installing p4.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:evil_update
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:clean
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... x = 1
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling p4.
    Updating p1.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:clean
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:clean
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling p1.
    Installing p1.
    Updating p2.
    Updating p3.
    Installing p4.

    """

def install_source_dist_with_bad_py():
    r"""

    >>> mkdir('badegg')
    >>> mkdir('badegg', 'badegg')
    >>> write('badegg', 'badegg', '__init__.py', '#\\n')
    >>> mkdir('badegg', 'badegg', 'scripts')
    >>> write('badegg', 'badegg', 'scripts', '__init__.py', '#\\n')
    >>> write('badegg', 'badegg', 'scripts', 'one.py',
    ... '''
    ... return 1
    ... ''')

    >>> write('badegg', 'setup.py',
    ... '''
    ... from setuptools import setup, find_packages
    ... setup(
    ...     name='badegg',
    ...     version='1',
    ...     packages = find_packages('.'),
    ...     zip_safe=False)
    ... ''')

    >>> print_(system(buildout+' setup badegg sdist'), end='') # doctest: +ELLIPSIS
    Running setup script 'badegg/setup.py'.
    ...

    >>> dist = join('badegg', 'dist')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs bo
    ... find-links = %(dist)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = badegg
    ...
    ... [bo]
    ... recipe = zc.recipe.egg
    ... eggs = zc.buildout
    ... scripts = buildout=bo
    ... ''' % globals())

    >>> print_(system(buildout));print_('X') # doctest: +ELLIPSIS
    Installing eggs.
    Getting distribution for 'badegg'.
    Got badegg 1.
    Installing bo.
    ...
    SyntaxError: ...'return' outside function...
    ...
    SyntaxError: ...'return' outside function...
    ...

    >>> ls('eggs') # doctest: +ELLIPSIS
    d  badegg-1-py2.4.egg
    ...

    >>> ls('bin')
    -  bo
    -  buildout
    """

def version_requirements_in_build_honored():
    '''

    >>> update_extdemo()
    >>> dest = tmpdir('sample-install')
    >>> mkdir('include')
    >>> write('include', 'extdemo.h',
    ... """
    ... #define EXTDEMO 42
    ... """)

    >>> zc.buildout.easy_install.build(
    ...   'extdemo ==1.4', dest,
    ...   {'include-dirs': os.path.join(sample_buildout, 'include')},
    ...   links=[link_server], index=link_server+'index/',
    ...   newest=False)
    ['/sample-install/extdemo-1.4-py2.4-linux-i686.egg']

    '''

def bug_105081_Specific_egg_versions_are_ignored_when_newer_eggs_are_around():
    """
    Buildout might ignore a specific egg requirement for a recipe:

    - Have a newer version of an egg in your eggs directory
    - Use 'recipe==olderversion' in your buildout.cfg to request an
      older version

    Buildout will go and fetch the older version, but it will *use*
    the newer version when installing a part with this recipe.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ... find-links = %(sample_eggs)s
    ...
    ... [x]
    ... recipe = zc.recipe.egg
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout), end='')
    Installing x.
    Getting distribution for 'demo'.
    Got demo 0.3.
    Getting distribution for 'demoneeded'.
    Got demoneeded 1.1.
    Generated script '/sample-buildout/bin/demo'.

    >>> print_(system(join('bin', 'demo')), end='')
    3 1

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ... find-links = %(sample_eggs)s
    ...
    ... [x]
    ... recipe = zc.recipe.egg
    ... eggs = demo ==0.1
    ... ''' % globals())

    >>> print_(system(buildout), end='')
    Uninstalling x.
    Installing x.
    Getting distribution for 'demo==0.1'.
    Got demo 0.1.
    Generated script '/sample-buildout/bin/demo'.

    >>> print_(system(join('bin', 'demo')), end='')
    1 1
    """

if sys.version_info > (2, 4):
    def test_exit_codes():
        """
        >>> import subprocess
        >>> def call(s):
        ...     p = subprocess.Popen(s, stdin=subprocess.PIPE,
        ...                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ...     p.stdin.close()
        ...     print_(p.stdout.read().decode())
        ...     print_('Exit:', bool(p.wait()))

        >>> call(buildout)
        <BLANKLINE>
        Exit: False

        >>> write('buildout.cfg',
        ... '''
        ... [buildout]
        ... parts = x
        ... ''')

        >>> call(buildout) # doctest: +NORMALIZE_WHITESPACE
        While:
          Installing.
          Getting section x.
        Error: The referenced section, 'x', was not defined.
        <BLANKLINE>
        Exit: True

        >>> write('setup.py',
        ... '''
        ... from setuptools import setup
        ... setup(name='zc.buildout.testexit', entry_points={
        ...    'zc.buildout': ['default = testexitrecipe:x']})
        ... ''')

        >>> write('testexitrecipe.py',
        ... '''
        ... x y
        ... ''')

        >>> write('buildout.cfg',
        ... '''
        ... [buildout]
        ... parts = x
        ... develop = .
        ...
        ... [x]
        ... recipe = zc.buildout.testexit
        ... ''')

        >>> call(buildout) # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
        Develop: '/sample-buildout/.'
        While:
          Installing.
          Getting section x.
          Initializing section x.
          Loading zc.buildout recipe entry zc.buildout.testexit:default.
        <BLANKLINE>
        An internal error occurred due to a bug in either zc.buildout or in a
        recipe being used:
        Traceback (most recent call last):
        ...
             x y
               ^
         SyntaxError: invalid syntax
        <BLANKLINE>
        Exit: True
        """

def bug_59270_recipes_always_start_in_buildout_dir():
    r"""
    Recipes can rely on running from buildout directory

    >>> mkdir('bad_start')
    >>> write('bad_recipe.py',
    ... r'''
    ... import os, sys
    ... def print_(*args):
    ...     sys.stdout.write(' '.join(map(str, args)) + '\n')
    ... class Bad:
    ...     def __init__(self, *_):
    ...         print_(os.getcwd())
    ...     def install(self):
    ...         sys.stdout.write(os.getcwd()+'\n')
    ...         os.chdir('bad_start')
    ...         sys.stdout.write(os.getcwd()+'\n')
    ...         return ()
    ... ''')

    >>> write('setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='bad.test',
    ...       entry_points={'zc.buildout': ['default=bad_recipe:Bad']},)
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = .
    ... parts = b1 b2
    ... [b1]
    ... recipe = bad.test
    ... [b2]
    ... recipe = bad.test
    ... ''')

    >>> os.chdir('bad_start')
    >>> print_(system(join(sample_buildout, 'bin', 'buildout')
    ...              +' -c '+join(sample_buildout, 'buildout.cfg')), end='')
    Develop: '/sample-buildout/.'
    /sample-buildout
    /sample-buildout
    Installing b1.
    /sample-buildout
    /sample-buildout/bad_start
    Installing b2.
    /sample-buildout
    /sample-buildout/bad_start
    """

def bug_61890_file_urls_dont_seem_to_work_in_find_dash_links():
    """

    This bug arises from the fact that setuptools is overly restrictive
    about file urls, requiring that file urls pointing at directories
    must end in a slash.

    >>> dest = tmpdir('sample-install')
    >>> import zc.buildout.easy_install
    >>> sample_eggs = sample_eggs.replace(os.path.sep, '/')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo==0.2'], dest,
    ...     links=['file://'+sample_eggs], index=link_server+'index/')


    >>> for dist in ws:
    ...     print_(dist)
    demoneeded 1.1
    demo 0.2

    >>> ls(dest)
    d  demo-0.2-py2.4.egg
    d  demoneeded-1.1-py2.4.egg

    """

def bug_75607_buildout_should_not_run_if_it_creates_an_empty_buildout_cfg():
    """
    >>> remove('buildout.cfg')
    >>> print_(system(buildout), end='')
    While:
      Initializing.
    Error: Couldn't open /sample-buildout/buildout.cfg



    """

def dealing_with_extremely_insane_dependencies():
    r"""

    There was a problem with analysis of dependencies taking a long
    time, in part because the analysis would get repeated every time a
    package was encountered in a dependency list.  Now, we don't do
    the analysis any more:

    >>> import os
    >>> for i in range(5):
    ...     p = 'pack%s' % i
    ...     deps = [('pack%s' % j) for j in range(5) if j is not i]
    ...     if i == 4:
    ...         deps.append('pack5')
    ...     mkdir(p)
    ...     write(p, 'setup.py',
    ...           'from setuptools import setup\n'
    ...           'setup(name=%r, install_requires=%r,\n'
    ...           '      url="u", author="a", author_email="e")\n'
    ...           % (p, deps))

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = pack0 pack1 pack2 pack3 pack4
    ... parts = pack1
    ...
    ... [pack1]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = pack0
    ... ''')

    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Develop: '/sample-buildout/pack0'
    Develop: '/sample-buildout/pack1'
    Develop: '/sample-buildout/pack2'
    Develop: '/sample-buildout/pack3'
    Develop: '/sample-buildout/pack4'
    Installing pack1.
    ...
    While:
      Installing pack1.
      Getting distribution for 'pack5'.
    Error: Couldn't find a distribution for 'pack5'.

    However, if we run in verbose mode, we can see why packages were included:

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    We have a develop egg: zc.buildout 1.0.0
    We have the best distribution that satisfies 'setuptools'.
    Picked: setuptools = 0.7
    Develop: '/sample-buildout/pack0'
    Develop: '/sample-buildout/pack1'
    Develop: '/sample-buildout/pack2'
    Develop: '/sample-buildout/pack3'
    Develop: '/sample-buildout/pack4'
    ...
    Installing pack1.
    Installing 'pack0'.
    We have a develop egg: pack0 0.0.0
    Getting required 'pack4'
      required by pack0 0.0.0.
    We have a develop egg: pack4 0.0.0
    Getting required 'pack3'
      required by pack0 0.0.0.
      required by pack4 0.0.0.
    We have a develop egg: pack3 0.0.0
    Getting required 'pack2'
      required by pack0 0.0.0.
      required by pack3 0.0.0.
      required by pack4 0.0.0.
    We have a develop egg: pack2 0.0.0
    Getting required 'pack1'
      required by pack0 0.0.0.
      required by pack2 0.0.0.
      required by pack3 0.0.0.
      required by pack4 0.0.0.
    We have a develop egg: pack1 0.0.0
    Getting required 'pack5'
      required by pack4 0.0.0.
    We have no distributions for pack5 that satisfies 'pack5'.
    ...
    While:
      Installing pack1.
      Getting distribution for 'pack5'.
    Error: Couldn't find a distribution for 'pack5'.
    """

def read_find_links_to_load_extensions():
    r"""
We'll create a wacky buildout extension that just announces itself when used:

    >>> src = tmpdir('src')
    >>> write(src, 'wacky_handler.py',
    ... '''
    ... import sys
    ... def install(buildout=None):
    ...     sys.stdout.write("I am a wacky extension\\n")
    ... ''')
    >>> write(src, 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='wackyextension', version='1',
    ...       py_modules=['wacky_handler'],
    ...       entry_points = {'zc.buildout.extension':
    ...             ['default = wacky_handler:install']
    ...             },
    ...       )
    ... ''')
    >>> print_(system(buildout+' setup '+src+' bdist_egg'), end='')
    ... # doctest: +ELLIPSIS
    Running setup ...
    creating 'dist/wackyextension-1-...

Now we'll create a buildout that uses this extension to load other packages:

    >>> wacky_server = link_server.replace('http', 'wacky')
    >>> dist = 'file://' + join(src, 'dist').replace(os.path.sep, '/')
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... extensions = wackyextension
    ... find-links = %(dist)s
    ... ''' % globals())

When we run the buildout. it will load the extension from the dist
directory and then use the wacky extension to load the demo package

    >>> print_(system(buildout), end='')
    Getting distribution for 'wackyextension'.
    Got wackyextension 1.
    I am a wacky extension

    """

def distributions_from_local_find_links_make_it_to_download_cache():
    """

If we specify a local directory in find links, distros found there
need to make it to the download cache.

    >>> mkdir('test')
    >>> write('test', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='foo')
    ... ''')

    >>> print_(system(buildout+' setup test bdist_egg')) # doctest: +ELLIPSIS
    Running setup script 'test/setup.py'.
    ...


    >>> mkdir('cache')
    >>> old_cache = zc.buildout.easy_install.download_cache('cache')
    >>> list(zc.buildout.easy_install.install(['foo'], 'eggs',
    ...          links=[join('test', 'dist')])) # doctest: +ELLIPSIS
    [foo 0.0.0 ...

    >>> ls('cache')
    -  foo-0.0.0-py2.4.egg

    >>> _ = zc.buildout.easy_install.download_cache(old_cache)

    """

def create_egg(name, version, dest, install_requires=None,
               dependency_links=None):
    d = tempfile.mkdtemp()
    if dest=='available':
        extras = dict(x=['x'])
    else:
        extras = {}
    if dependency_links:
        links = 'dependency_links = %s, ' % dependency_links
    else:
        links = ''
    if install_requires:
        requires = 'install_requires = %s, ' % install_requires
    else:
        requires = ''
    try:
        open(os.path.join(d, 'setup.py'), 'w').write(
            'from setuptools import setup\n'
            'setup(name=%r, version=%r, extras_require=%r, zip_safe=True,\n'
            '      %s %s py_modules=["setup"]\n)'
            % (name, str(version), extras, requires, links)
            )
        zc.buildout.testing.bdist_egg(d, sys.executable, os.path.abspath(dest))
    finally:
        shutil.rmtree(d)

def prefer_final_permutation(existing, available):
    for d in ('existing', 'available'):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.mkdir(d)
    for version in existing:
        create_egg('spam', version, 'existing')
    for version in available:
        create_egg('spam', version, 'available')

    zc.buildout.easy_install.clear_index_cache()
    [dist] = list(
        zc.buildout.easy_install.install(['spam'], 'existing', ['available'])
        )

    if dist.extras:
        print_('downloaded', dist.version)
    else:
        print_('had', dist.version)
    sys.path_importer_cache.clear()

def prefer_final():
    """
This test tests several permutations:

Using different version numbers to work around zip importer cache problems. :(

- With prefer final:

    - no existing and newer dev available
    >>> prefer_final_permutation((), [1, '2a1'])
    downloaded 1

    - no existing and only dev available
    >>> prefer_final_permutation((), ['3a1'])
    downloaded 3a1

    - final existing and only dev acailable
    >>> prefer_final_permutation([4], ['5a1'])
    had 4

    - final existing and newer final available
    >>> prefer_final_permutation([6], [7])
    downloaded 7

    - final existing and same final available
    >>> prefer_final_permutation([8], [8])
    had 8

    - final existing and older final available
    >>> prefer_final_permutation([10], [9])
    had 10

    - only dev existing and final available
    >>> prefer_final_permutation(['12a1'], [11])
    downloaded 11

    - only dev existing and no final available newer dev available
    >>> prefer_final_permutation(['13a1'], ['13a2'])
    downloaded 13a2

    - only dev existing and no final available older dev available
    >>> prefer_final_permutation(['15a1'], ['14a1'])
    had 15a1

    - only dev existing and no final available same dev available
    >>> prefer_final_permutation(['16a1'], ['16a1'])
    had 16a1

- Without prefer final:

    >>> _ = zc.buildout.easy_install.prefer_final(False)

    - no existing and newer dev available
    >>> prefer_final_permutation((), [18, '19a1'])
    downloaded 19a1

    - no existing and only dev available
    >>> prefer_final_permutation((), ['20a1'])
    downloaded 20a1

    - final existing and only dev acailable
    >>> prefer_final_permutation([21], ['22a1'])
    downloaded 22a1

    - final existing and newer final available
    >>> prefer_final_permutation([23], [24])
    downloaded 24

    - final existing and same final available
    >>> prefer_final_permutation([25], [25])
    had 25

    - final existing and older final available
    >>> prefer_final_permutation([27], [26])
    had 27

    - only dev existing and final available
    >>> prefer_final_permutation(['29a1'], [28])
    had 29a1

    - only dev existing and no final available newer dev available
    >>> prefer_final_permutation(['30a1'], ['30a2'])
    downloaded 30a2

    - only dev existing and no final available older dev available
    >>> prefer_final_permutation(['32a1'], ['31a1'])
    had 32a1

    - only dev existing and no final available same dev available
    >>> prefer_final_permutation(['33a1'], ['33a1'])
    had 33a1

    >>> _ = zc.buildout.easy_install.prefer_final(True)

    """

def buildout_prefer_final_option():
    """
The prefer-final buildout option can be used for override the default
preference for newer distributions.

The default is prefer-final = true:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    ...
    Picked: demo = 0.3
    ...
    Picked: demoneeded = 1.1

Here we see that the final versions of demo and demoneeded are used.
We get the same behavior if we add prefer-final = true

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ... prefer-final = true
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    ...
    Picked: demo = 0.3
    ...
    Picked: demoneeded = 1.1

If we specify prefer-final = false, we'll get the newest
distributions:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ... prefer-final = false
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    ...
    Picked: demo = 0.4rc1
    ...
    Picked: demoneeded = 1.2rc1

We get an error if we specify anything but true or false:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ... prefer-final = no
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    While:
      Initializing.
    Error: Invalid value for 'prefer-final' option: 'no'
    """

def wont_downgrade_due_to_prefer_final():
    r"""
    If we install a non-final buildout version, we don't want to
    downgrade just bcause we prefer-final.  If a buildout version
    isn't specified using a versions entry, then buildout's version
    requirement gets set to >=CURRENT_VERSION.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... ''')

    >>> [v] = [l.split('= >=', 1)[1].strip()
    ...        for l in system(buildout+' -vv').split('\n')
    ...        if l.startswith('zc.buildout = >=')]
    >>> v == pkg_resources.working_set.find(
    ...         pkg_resources.Requirement.parse('zc.buildout')
    ...         ).version
    True

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... [versions]
    ... zc.buildout = >.1
    ... ''')
    >>> [str(l.split('= >', 1)[1].strip())
    ...        for l in system(buildout+' -vv').split('\n')
    ...        if l.startswith('zc.buildout =')]
    ['.1']

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... versions = versions
    ... [versions]
    ... zc.buildout = 43
    ... ''')
    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Getting distribution for 'zc.buildout==43'.
    ...

    """

def develop_with_modules():
    """
Distribution setup scripts can import modules in the distribution directory:

    >>> mkdir('foo')
    >>> write('foo', 'bar.py',
    ... '''# empty
    ... ''')

    >>> write('foo', 'setup.py',
    ... '''
    ... import bar
    ... from setuptools import setup
    ... setup(name="foo")
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = foo
    ... parts =
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'

    >>> ls('develop-eggs')
    -  foo.egg-link
    -  zc.recipe.egg.egg-link

    """

def dont_pick_setuptools_if_version_is_specified_when_required_by_src_dist():
    r"""
When installing a source distribution, we got setuptools without
honoring our version specification.

    >>> mkdir('dist')
    >>> write('setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='foo', version='1', py_modules=['foo'], zip_safe=True)
    ... ''')
    >>> write('foo.py', '')
    >>> _ = system(buildout+' setup . sdist')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = foo
    ... find-links = dist
    ... versions = versions
    ... allow-picked-versions = false
    ...
    ... [versions]
    ... wtf = %s
    ... foo = 1
    ...
    ... [foo]
    ... recipe = zc.recipe.egg
    ... eggs = foo
    ... ''' % ('\n'.join(
    ...     '%s = %s' % (d.key, d.version)
    ...     for d in zc.buildout.easy_install.buildout_and_setuptools_dists)))

    >>> print_(system(buildout), end='')
    Installing foo.
    Getting distribution for 'foo==1'.
    Got foo 1.

    """

def pyc_and_pyo_files_have_correct_paths():
    r"""

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = demo
    ... interpreter = py
    ... ''' % globals())

    >>> _ = system(buildout)

    >>> write('t.py',
    ... r'''
    ... import eggrecipedemo, eggrecipedemoneeded, sys
    ... if sys.version_info > (3,):
    ...     code = lambda f: f.__code__
    ... else:
    ...     code = lambda f: f.func_code
    ... sys.stdout.write(code(eggrecipedemo.main).co_filename+'\n')
    ... sys.stdout.write(code(eggrecipedemoneeded.f).co_filename+'\n')
    ... ''')

    >>> print_(system(join('bin', 'py')+ ' t.py'), end='')
    /sample-buildout/eggs/demo-0.3-py2.4.egg/eggrecipedemo.py
    /sample-buildout/eggs/demoneeded-1.1-py2.4.egg/eggrecipedemoneeded.py
    """

def dont_mess_with_standard_dirs_with_variable_refs():
    """
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... eggs-directory = ${buildout:directory}/develop-eggs
    ... parts =
    ... ''' % globals())
    >>> print_(system(buildout), end='')

    """

def expand_shell_patterns_in_develop_paths():
    """
    Sometimes we want to include a number of eggs in some directory as
    develop eggs, without explicitly listing all of them in our
    buildout.cfg

    >>> make_dist_that_requires(sample_buildout, 'sampley')
    >>> make_dist_that_requires(sample_buildout, 'samplez')

    Now, let's create a buildout that has a shell pattern that matches
    both:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = sample*
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = sampley
    ...        samplez
    ... ''' % globals())

    We can see that both eggs were found:

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/sampley'
    Develop: '/sample-buildout/samplez'
    Installing eggs.

    """

def warn_users_when_expanding_shell_patterns_yields_no_results():
    """
    Sometimes shell patterns do not match anything, so we want to warn
    our users about it...

    >>> make_dist_that_requires(sample_buildout, 'samplea')

    So if we have 2 patterns, one that has a matching directory, and
    another one that does not

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = samplea grumble*
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = samplea
    ... ''' % globals())

    We should get one of the eggs, and a warning for the pattern that
    did not match anything.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/samplea'
    Couldn't develop '/sample-buildout/grumble*' (not found)
    Installing eggs.

    """

def make_sure_versions_dont_cancel_extras():
    """
    There was a bug that caused extras in requirements to be lost.

    >>> _ = open('setup.py', 'w').write('''
    ... from setuptools import setup
    ... setup(name='extraversiondemo', version='1.0',
    ...       url='x', author='x', author_email='x',
    ...       extras_require=dict(foo=['demo']), py_modules=['t'])
    ... ''')
    >>> open('README', 'w').close()
    >>> open('t.py', 'w').close()

    >>> sdist('.', sample_eggs)
    >>> mkdir('dest')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['extraversiondemo[foo]'], 'dest', links=[sample_eggs],
    ...     versions = dict(extraversiondemo='1.0')
    ... )
    >>> sorted(dist.key for dist in ws)
    ['demo', 'demoneeded', 'extraversiondemo']
    """

def increment_buildout_options():
    r"""
    >>> write('b1.cfg', '''
    ... [buildout]
    ... parts = p1
    ... x = 1
    ... y = a
    ...     b
    ...
    ... [p1]
    ... recipe = zc.buildout:debug
    ... foo = ${buildout:x} ${buildout:y}
    ... ''')

    >>> write('buildout.cfg', '''
    ... [buildout]
    ... extends = b1.cfg
    ... parts += p2
    ... x += 2
    ... y -= a
    ...
    ... [p2]
    ... <= p1
    ... ''')

    >>> print_(system(buildout), end='')
    Installing p1.
      foo='1\n2 b'
      recipe='zc.buildout:debug'
    Installing p2.
      foo='1\n2 b'
      recipe='zc.buildout:debug'
    """

def increment_buildout_with_multiple_extended_files_421022():
    r"""
    >>> write('foo.cfg', '''
    ... [buildout]
    ... foo-option = foo
    ... [other]
    ... foo-option = foo
    ... ''')
    >>> write('bar.cfg', '''
    ... [buildout]
    ... bar-option = bar
    ... [other]
    ... bar-option = bar
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... parts = p other
    ... extends = bar.cfg foo.cfg
    ... bar-option += baz
    ... foo-option += ham
    ...
    ... [other]
    ... recipe = zc.buildout:debug
    ... bar-option += baz
    ... foo-option += ham
    ...
    ... [p]
    ... recipe = zc.buildout:debug
    ... x = ${buildout:bar-option} ${buildout:foo-option}
    ... ''')

    >>> print_(system(buildout), end='')
    Installing p.
      recipe='zc.buildout:debug'
      x='bar\nbaz foo\nham'
    Installing other.
      bar-option='bar\nbaz'
      foo-option='foo\nham'
      recipe='zc.buildout:debug'
    """

def increment_on_command_line():
    r"""
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... parts = p1
    ... x = 1
    ... y = a
    ...     b
    ...
    ... [p1]
    ... recipe = zc.buildout:debug
    ... foo = ${buildout:x} ${buildout:y}
    ...
    ... [p2]
    ... <= p1
    ... ''')

    >>> print_(system(buildout+' buildout:parts+=p2 p1:foo+=bar'), end='')
    Installing p1.
      foo='1 a\nb\nbar'
      recipe='zc.buildout:debug'
    Installing p2.
      foo='1 a\nb\nbar'
      recipe='zc.buildout:debug'
    """

def test_constrained_requirement():
    """
    zc.buildout.easy_install._constrained_requirement(constraint, requirement)

    Transforms an environment by applying a constraint.

    Here's a table of examples:

    >>> from zc.buildout.easy_install import IncompatibleConstraintError
    >>> examples = [
    ... # original, constraint, transformed
    ... ('x',        '1',        'x==1'),
    ... ('x>1',      '2',        'x==2'),
    ... ('x>3',      '2',        IncompatibleConstraintError),
    ... ('x>1',      '>2',       'x>1,>2'),
    ... ]
    >>> from zc.buildout.easy_install import _constrained_requirement
    >>> for o, c, e in examples:
    ...     try:
    ...         o = pkg_resources.Requirement.parse(o)
    ...         if isinstance(e, str):
    ...             e = pkg_resources.Requirement.parse(e)
    ...         g = _constrained_requirement(c, o)
    ...     except IncompatibleConstraintError:
    ...         g = IncompatibleConstraintError
    ...     if str(g) != str(e):
    ...         print_('failed', o, c, g, '!=', e)
    """

def test_distutils_scripts_using_import_are_properly_parsed():
    """
    zc.buildout.easy_install._distutils_script(path, dest, script_content, initialization, rsetup):

    Creates a script for a distutils based project. In this example for a
    hypothetical code quality checker called 'pyflint' that uses an import
    statement to import its code.

    >>> pyflint_script = '''#!/path/to/bin/python
    ... import pyflint.do_something
    ... pyflint.do_something()
    ... '''
    >>> import sys
    >>> original_executable = sys.executable
    >>> sys.executable = 'python'

    >>> from zc.buildout.easy_install import _distutils_script
    >>> generated = _distutils_script('\\'/path/test/\\'', 'bin/pyflint', pyflint_script, '', '')
    >>> if sys.platform == 'win32':
    ...     generated == ['bin/pyflint.exe', 'bin/pyflint-script.py']
    ... else:
    ...     generated == ['bin/pyflint']
    True
    >>> if sys.platform == 'win32':
    ...     cat('bin/pyflint-script.py')
    ... else:
    ...     cat('bin/pyflint')
    #!python
    <BLANKLINE>
    <BLANKLINE>
    import sys
    sys.path[0:0] = [
      '/path/test/',
      ]
    <BLANKLINE>
    <BLANKLINE>
    import pyflint.do_something
    pyflint.do_something()

    >>> sys.executable = original_executable
    """

def test_distutils_scripts_using_from_are_properly_parsed():
    """
    zc.buildout.easy_install._distutils_script(path, dest, script_content, initialization, rsetup):

    Creates a script for a distutils based project. In this example for a
    hypothetical code quality checker called 'pyflint' that uses a from
    statement to import its code.

    >>> pyflint_script = '''#!/path/to/bin/python
    ... from pyflint import do_something
    ... do_something()
    ... '''
    >>> import sys
    >>> original_executable = sys.executable
    >>> sys.executable = 'python'

    >>> from zc.buildout.easy_install import _distutils_script
    >>> generated = _distutils_script('\\'/path/test/\\'', 'bin/pyflint', pyflint_script, '', '')
    >>> if sys.platform == 'win32':
    ...     generated == ['bin/pyflint.exe', 'bin/pyflint-script.py']
    ... else:
    ...     generated == ['bin/pyflint']
    True
    >>> if sys.platform == 'win32':
    ...     cat('bin/pyflint-script.py')
    ... else:
    ...     cat('bin/pyflint')
    #!python
    <BLANKLINE>
    <BLANKLINE>
    import sys
    sys.path[0:0] = [
      '/path/test/',
      ]
    <BLANKLINE>
    <BLANKLINE>
    from pyflint import do_something
    do_something()

    >>> sys.executable = original_executable
    """


def want_new_zcrecipeegg():
    """
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = egg
    ... [egg]
    ... recipe = zc.recipe.egg <2dev
    ... eggs = demo
    ... ''')
    >>> print_(system(join('bin', 'buildout')), end='') # doctest: +ELLIPSIS
    Getting distribution for 'zc.recipe.egg<2dev,>=2.0.6'...
    While:
      Installing.
      Getting section egg.
      Initializing section egg.
      Installing recipe zc.recipe.egg <2dev.
      Getting distribution for 'zc.recipe.egg<2dev,>=2.0.6'.
    Error: Couldn't find a distribution for 'zc.recipe.egg<2dev,>=2.0.6'.
    """

def macro_inheritance_bug():
    """

There was a bug preventing a section from using another section as a macro
if that section was extended with macros, and both sections were listed as
parts (phew!).  The following contrived example demonstrates that this
now works.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = foo bar
    ... [base]
    ... recipe = zc.recipe.egg
    ... [foo]
    ... <=base
    ... eggs = zc.buildout
    ... interpreter = python
    ... [bar]
    ... <=foo
    ... interpreter = py
    ... ''')
    >>> print_(system(join('bin', 'buildout')), end='') # doctest: +ELLIPSIS
    Installing foo.
    ...
    Installing bar.
    ...
    >>> ls("./bin")
    -  buildout
    -  py
    -  python
    """

def bootstrap_honors_relative_paths():
    """
    >>> working = tmpdir('working')
    >>> cd(working)
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... relative-paths = true
    ... ''')
    >>> _ = system(buildout+' bootstrap')
    >>> cat('bin', 'buildout') # doctest: +ELLIPSIS
    #!/usr/local/bin/python2.7
    <BLANKLINE>
    import os
    <BLANKLINE>
    join = os.path.join
    base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    base = os.path.dirname(base)
    <BLANKLINE>
    import sys
    sys.path[0:0] = [
      ...
      join(base, 'eggs/setuptools-0.7-py2.7.egg'),
      ]
    <BLANKLINE>
    import zc.buildout.buildout
    <BLANKLINE>
    if __name__ == '__main__':
        sys.exit(zc.buildout.buildout.main())
    """

def cant_use_install_from_cache_and_offline_together():
    r"""
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... offline = true
    ... install-from-cache = true
    ... ''')
    >>> print_(system(join('bin', 'buildout')), end='') # doctest: +ELLIPSIS
    While:
      Initializing.
    Error: install-from-cache can't be used with offline mode.
    Nothing is installed, even from cache, in offline
    mode, which might better be called 'no-install mode'.
    <BLANKLINE>
    """

def error_installing_in_offline_mode_if_dont_have_needed_dist():
    r"""
    >>> import zc.buildout.easy_install
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo==0.2'], None,
    ...     links=[link_server], index=link_server+'index/')
    Traceback (most recent call last):
    ...
    UserError: We don't have a distribution for demo==0.2
    and can't install one in offline (no-install) mode.
    <BLANKLINE>
    """

def error_building_in_offline_mode_if_dont_have_needed_dist():
    r"""
    >>> zc.buildout.easy_install.build(
    ...   'extdemo', None,
    ...   {}, links=[link_server], index=link_server+'index/')
    Traceback (most recent call last):
    ...
    UserError: We don't have a distribution for extdemo
    and can't build one in offline (no-install) mode.
    <BLANKLINE>
    """

def test_buildout_section_shorthand_for_command_line_assignments():
    r"""
    >>> write('buildout.cfg', '')
    >>> print_(system(buildout+' parts='), end='') # doctest: +ELLIPSIS
    """

def buildout_honors_umask():
    """

    For setting the executable permission, the user's umask is honored:

    >>> orig_umask = os.umask(0o077)  # Only user gets permissions.
    >>> zc.buildout.easy_install._execute_permission() == 0o700
    True
    >>> tmp = os.umask(0o022)  # User can write, the rest not.
    >>> zc.buildout.easy_install._execute_permission() == 0o755
    True
    >>> tmp = os.umask(orig_umask)  # Reset umask to the original value.
    """

def parse_with_section_expr():
    r"""
    >>> class Recipe:
    ...     def __init__(self, buildout, *_):
    ...         buildout.parse('''
    ...             [foo : sys.version_info[0] > 0]
    ...             x = 1
    ...             ''')

    >>> buildout = zc.buildout.testing.Buildout()
    >>> buildout.parse('''
    ...     [foo : sys.version_info[0] > 0]
    ...     x = 1
    ...     ''')
    >>> buildout.print_options()
    [foo]
    x = 1

    """

def test_abi_tag_eggs():
    r"""
    >>> mkdir('..', 'bo')
    >>> cd('..', 'bo')
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = egg
    ... abi-tag-eggs = true
    ... [egg]
    ... recipe = zc.recipe.egg
    ... eggs = demo
    ... ''')
    >>> _ = system(join('..', 'sample-buildout', 'bin', 'buildout')
    ...            + ' bootstrap')
    >>> _ = system(join('bin', 'buildout'))
    >>> ls('.')
    d  bin
    -  buildout.cfg
    d  develop-eggs
    d  eggs
    d  parts
    >>> from zc.buildout.pep425tags import get_abi_tag
    >>> ls(join('eggs', get_abi_tag())) # doctest: +ELLIPSIS
    d  setuptools-34.0.3-py3.5.egg
    """

def test_buildout_doesnt_keep_adding_itself_to_versions():
    r"""
    We were constantly writing to versions.cfg for buildout and setuptools

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... extends = versions.cfg
    ... show-picked-versions = true
    ... update-versions-file = versions.cfg
    ... extends = versions.cfg
    ... ''')
    >>> write('versions.cfg',
    ... '''[versions]
    ... ''')
    >>> _ = system(join('bin', 'buildout'))
    >>> with open('versions.cfg') as f:
    ...     versions = f.read()
    >>> _ = system(join('bin', 'buildout'))

    On the first run, some pins were added:

    >>> cat('versions.cfg') # doctest: +ELLIPSIS
    [versions]
    <BLANKLINE>
    # Added by buildout...
    setuptools = 34.0.3
    >>> _ = system(join('bin', 'buildout'))
    >>> _ = system(join('bin', 'buildout'))

    Subsequent runs didn't add additional text:

    >>> with open('versions.cfg') as f:
    ...     versions == f.read()
    True
    """

if sys.platform == 'win32':
    del buildout_honors_umask # umask on dohs is academic

######################################################################

def create_sample_eggs(test, executable=sys.executable):
    assert executable == sys.executable, (executable, sys.executable)
    write = test.globs['write']
    dest = test.globs['sample_eggs']
    tmp = tempfile.mkdtemp()
    try:
        write(tmp, 'README.txt', '')

        for i in (0, 1, 2):
            write(tmp, 'eggrecipedemoneeded.py', 'y=%s\ndef f():\n  pass' % i)
            rc1 = i==2 and 'rc1' or ''
            write(
                tmp, 'setup.py',
                "from setuptools import setup\n"
                "setup(name='demoneeded', py_modules=['eggrecipedemoneeded'],"
                " zip_safe=True, version='1.%s%s', author='bob', url='bob', "
                "author_email='bob')\n"
                % (i, rc1)
                )
            zc.buildout.testing.sdist(tmp, dest)

        write(
            tmp, 'distutilsscript',
            '#!/usr/bin/python\n'
            '# -*- coding: utf-8 -*-\n'
            '"""Module docstring."""\n'
            'from __future__ import print_statement\n'
            'import os\n'
            'import sys; sys.stdout.write("distutils!\\n")\n'
            )
        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='other', zip_safe=False, version='1.0', "
            "scripts=['distutilsscript'],"
            "py_modules=['eggrecipedemoneeded'])\n"
            )
        zc.buildout.testing.bdist_egg(tmp, sys.executable, dest)

        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='du_zipped', zip_safe=True, version='1.0', "
            "scripts=['distutilsscript'],"
            "py_modules=['eggrecipedemoneeded'])\n"
            )
        zc.buildout.testing.bdist_egg(tmp, executable, dest)

        os.remove(os.path.join(tmp, 'distutilsscript'))
        os.remove(os.path.join(tmp, 'eggrecipedemoneeded.py'))

        for i in (1, 2, 3, 4):
            write(
                tmp, 'eggrecipedemo.py',
                'import eggrecipedemoneeded, sys\n'
                'def print_(*a):\n'
                '    sys.stdout.write(" ".join(map(str, a))+"\\n")\n'
                'x=%s\n'
                'def main():\n'
                '   print_(x, eggrecipedemoneeded.y)\n'
                % i)
            rc1 = i==4 and 'rc1' or ''
            write(
                tmp, 'setup.py',
                "from setuptools import setup\n"
                "setup(name='demo', py_modules=['eggrecipedemo'],"
                " install_requires = 'demoneeded',"
                " entry_points={'console_scripts': "
                     "['demo = eggrecipedemo:main']},"
                " zip_safe=True, version='0.%s%s')\n" % (i, rc1)
                )
            zc.buildout.testing.bdist_egg(tmp, dest)

        write(tmp, 'mixedcase.py', 'def f():\n  pass')
        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='MIXEDCASE', py_modules=['mixedcase'],"
            " author='bob', url='bob', author_email='bob',"
            " install_requires = 'demoneeded',"
            " zip_safe=True, version='0.5')\n"
            )
        zc.buildout.testing.sdist(tmp, dest)
        # rename file to lower case
        # to test issues between file and package name
        curdir = os.getcwd()
        os.chdir(dest)
        for file in os.listdir(dest):
            if "MIXEDCASE" in file:
                os.rename(file, file.lower())
        os.chdir(curdir)

        write(tmp, 'eggrecipebigdemo.py', 'import eggrecipedemo')
        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='bigdemo', "
            " install_requires = 'demo',"
            " py_modules=['eggrecipebigdemo'], "
            " zip_safe=True, version='0.1')\n"
            )
        zc.buildout.testing.bdist_egg(tmp, sys.executable, dest)

    finally:
        shutil.rmtree(tmp)

extdemo_c2 = """
#include <Python.h>
#include <extdemo.h>

static PyMethodDef methods[] = {{NULL}};

PyMODINIT_FUNC
initextdemo(void)
{
    PyObject *m;
    m = Py_InitModule3("extdemo", methods, "");
#ifdef TWO
    PyModule_AddObject(m, "val", PyInt_FromLong(2));
#else
    PyModule_AddObject(m, "val", PyInt_FromLong(EXTDEMO));
#endif
}
"""

extdemo_c3 = """
#include <Python.h>
#include <extdemo.h>

static PyMethodDef methods[] = {{NULL}};

#define MOD_DEF(ob, name, doc, methods) \
	  static struct PyModuleDef moduledef = { \
	    PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
	  ob = PyModule_Create(&moduledef);

#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)

MOD_INIT(extdemo)
{
    PyObject *m;

    MOD_DEF(m, "extdemo", "", methods);

#ifdef TWO
    PyModule_AddObject(m, "val", PyLong_FromLong(2));
#else
    PyModule_AddObject(m, "val", PyLong_FromLong(EXTDEMO));
#endif

    return m;
}
"""

extdemo_c = sys.version_info[0] < 3 and extdemo_c2 or extdemo_c3

extdemo_setup_py = r"""
import os, sys
from distutils.core import setup, Extension

if os.environ.get('test-variable'):
    print("Have environment test-variable: %%s" %% os.environ['test-variable'])

setup(name = "extdemo", version = "%s", url="http://www.zope.org",
      author="Demo", author_email="demo@demo.com",
      ext_modules = [Extension('extdemo', ['extdemo.c'])],
      )
"""

def add_source_dist(test, version=1.4):
    if 'extdemo' not in test.globs:
        test.globs['extdemo'] = test.globs['tmpdir']('extdemo')

    tmp = test.globs['extdemo']
    write = test.globs['write']
    try:
        write(tmp, 'extdemo.c', extdemo_c);
        write(tmp, 'setup.py', extdemo_setup_py % version);
        write(tmp, 'README', "");
        write(tmp, 'MANIFEST.in', "include *.c\n");
        test.globs['sdist'](tmp, test.globs['sample_eggs'])
    except:
        shutil.rmtree(tmp)

def easy_install_SetUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    sample_eggs = test.globs['tmpdir']('sample_eggs')
    test.globs['sample_eggs'] = sample_eggs
    os.mkdir(os.path.join(sample_eggs, 'index'))
    create_sample_eggs(test)
    add_source_dist(test)
    test.globs['link_server'] = test.globs['start_server'](
        test.globs['sample_eggs'])
    test.globs['update_extdemo'] = lambda : add_source_dist(test, 1.5)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)

def buildout_txt_setup(test):
    zc.buildout.testing.buildoutSetUp(test)
    mkdir = test.globs['mkdir']
    eggs = os.environ['buildout-testing-index-url'][7:]
    test.globs['sample_eggs'] = eggs
    create_sample_eggs(test)

    for name in os.listdir(eggs):
        if '-' in name:
            pname = name.split('-')[0]
            if not os.path.exists(os.path.join(eggs, pname)):
                mkdir(eggs, pname)
            shutil.move(os.path.join(eggs, name),
                        os.path.join(eggs, pname, name))

    dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('zc.recipe.egg'))
    mkdir(eggs, 'zc.recipe.egg')
    zc.buildout.testing.sdist(
        os.path.dirname(dist.location),
        os.path.join(eggs, 'zc.recipe.egg'),
        )

egg_parse = re.compile('([0-9a-zA-Z_.]+)-([0-9a-zA-Z_.]+)-py(\d[.]\d).egg$'
                       ).match
def makeNewRelease(project, ws, dest, version='99.99'):
    dist = ws.find(pkg_resources.Requirement.parse(project))
    eggname, oldver, pyver = egg_parse(
        os.path.basename(dist.location)
        ).groups()
    dest = os.path.join(dest, "%s-%s-py%s.egg" % (eggname, version, pyver))
    if os.path.isfile(dist.location):
        shutil.copy(dist.location, dest)
        zip = zipfile.ZipFile(dest, 'a')
        zip.writestr(
            'EGG-INFO/PKG-INFO',
            ((zip.read('EGG-INFO/PKG-INFO').decode('ISO-8859-1')
              ).replace("Version: %s" % oldver,
                        "Version: %s" % version)
             ).encode('ISO-8859-1')
            )
        zip.close()
    else:
        shutil.copytree(dist.location, dest)
        info_path = os.path.join(dest, 'EGG-INFO', 'PKG-INFO')
        info = open(info_path).read().replace("Version: %s" % oldver,
                                              "Version: %s" % version)
        open(info_path, 'w').write(info)

def getWorkingSetWithBuildoutEgg(test):
    sample_buildout = test.globs['sample_buildout']
    eggs = os.path.join(sample_buildout, 'eggs')

    # If the zc.buildout dist is a develop dist, convert it to a
    # regular egg in the sample buildout
    req = pkg_resources.Requirement.parse('zc.buildout')
    dist = pkg_resources.working_set.find(req)
    if dist.precedence == pkg_resources.DEVELOP_DIST:
        # We have a develop egg, create a real egg for it:
        here = os.getcwd()
        os.chdir(os.path.dirname(dist.location))
        zc.buildout.easy_install.call_subprocess(
            [sys.executable,
             os.path.join(os.path.dirname(dist.location), 'setup.py'),
             '-q', 'bdist_egg', '-d', eggs],
            env=dict(os.environ,
                     PYTHONPATH=zc.buildout.easy_install.setuptools_pythonpath,
                     ),
            )
        os.chdir(here)
        os.remove(os.path.join(eggs, 'zc.buildout.egg-link'))

        # Rebuild the buildout script
        ws = pkg_resources.WorkingSet([eggs])
        ws.require('zc.buildout')
        zc.buildout.easy_install.scripts(
            ['zc.buildout'], ws, sys.executable,
            os.path.join(sample_buildout, 'bin'))
    else:
        ws = pkg_resources.working_set
    return ws

def updateSetup(test):
    zc.buildout.testing.buildoutSetUp(test)
    new_releases = test.globs['tmpdir']('new_releases')
    test.globs['new_releases'] = new_releases
    ws = getWorkingSetWithBuildoutEgg(test)
    # now let's make the new releases
    for dist in zc.buildout.easy_install.buildout_and_setuptools_dists:
        makeNewRelease(dist.key, ws, new_releases)
        os.mkdir(os.path.join(new_releases, dist.key))

def ancestor(path, level):
    while level > 0:
        path = os.path.dirname(path)
        level -= 1

    return path

bootstrap_py = os.path.join(ancestor(__file__, 4), 'bootstrap', 'bootstrap.py')

def bootstrapSetup(test):
    buildout_txt_setup(test)
    test.globs['link_server'] = test.globs['start_server'](
        test.globs['sample_eggs'])
    sample_eggs = test.globs['sample_eggs']
    ws = getWorkingSetWithBuildoutEgg(test)
    makeNewRelease('zc.buildout', ws, sample_eggs, '2.0.0')
    makeNewRelease('zc.buildout', ws, sample_eggs, '22.0.0')
    os.environ['bootstrap-testing-find-links'] = test.globs['link_server']
    test.globs['bootstrap_py'] = bootstrap_py

normalize_bang = (
    re.compile(re.escape('#!'+
                         zc.buildout.easy_install._safe_arg(sys.executable))),
    '#!/usr/local/bin/python2.7',
    )

normalize_S = (
    re.compile(r'#!/usr/local/bin/python2.7 -S'),
    '#!/usr/local/bin/python2.7',
    )

def test_suite():
    test_suite = [
        manuel.testing.TestSuite(
            manuel.doctest.Manuel() + manuel.capture.Manuel(),
            'configparser.test'),
        manuel.testing.TestSuite(
            manuel.doctest.Manuel(
                optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
                checker=renormalizing.RENormalizing([
                    zc.buildout.testing.normalize_path,
                    zc.buildout.testing.normalize_endings,
                    zc.buildout.testing.normalize_script,
                    zc.buildout.testing.normalize_egg_py,
                    zc.buildout.testing.not_found,
                    zc.buildout.testing.adding_find_link,
                    # (re.compile(r"Installing 'zc.buildout >=\S+"), ''),
                    (re.compile('__buildout_signature__ = recipes-\S+'),
                     '__buildout_signature__ = recipes-SSSSSSSSSSS'),
                    (re.compile('executable = [\S ]+python\S*', re.I),
                     'executable = python'),
                    (re.compile('[-d]  (setuptools|setuptools)-\S+[.]egg'),
                     'setuptools.egg'),
                    (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                     'zc.buildout.egg'),
                    (re.compile('creating \S*setup.cfg'), 'creating setup.cfg'),
                    (re.compile('hello\%ssetup' % os.path.sep), 'hello/setup'),
                    (re.compile('Picked: (\S+) = \S+'),
                     'Picked: \\1 = V.V'),
                    (re.compile(r'We have a develop egg: zc.buildout (\S+)'),
                     'We have a develop egg: zc.buildout X.X.'),
                    (re.compile(r'\\[\\]?'), '/'),
                    (re.compile('WindowsError'), 'OSError'),
                    (re.compile(r'\[Error \d+\] Cannot create a file '
                                r'when that file already exists: '),
                     '[Errno 17] File exists: '
                     ),
                    (re.compile('setuptools'), 'setuptools'),
                    (re.compile('Got zc.recipe.egg \S+'), 'Got zc.recipe.egg'),
                    (re.compile(r'zc\.(buildout|recipe\.egg)\s*= >=\S+'),
                     'zc.\\1 = >=1.99'),
                    ])
                ) + manuel.capture.Manuel(),
            'buildout.txt',
            setUp=buildout_txt_setup,
            tearDown=zc.buildout.testing.buildoutTearDown,
            ),
        doctest.DocFileSuite(
            'runsetup.txt', 'repeatable.txt', 'setup.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.testing.not_found,
               zc.buildout.testing.adding_find_link,
               # (re.compile(r"Installing 'zc.buildout >=\S+"), ''),
               # (re.compile(r"Getting distribution for 'zc.buildout >=\S+"),
               #  ''),
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               (re.compile('[-d]  setuptools-\S+[.]egg'), 'setuptools.egg'),
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('creating \S*setup.cfg'), 'creating setup.cfg'),
               (re.compile('hello\%ssetup' % os.path.sep), 'hello/setup'),
               (re.compile('Picked: (\S+) = \S+'),
                'Picked: \\1 = V.V'),
               (re.compile(r'We have a develop egg: zc.buildout (\S+)'),
                'We have a develop egg: zc.buildout X.X.'),
               (re.compile(r'\\[\\]?'), '/'),
               (re.compile('WindowsError'), 'OSError'),
               (re.compile('setuptools = \S+'), 'setuptools = 0.7.99'),
               (re.compile(r'\[Error 17\] Cannot create a file '
                           r'when that file already exists: '),
                '[Errno 17] File exists: '
                ),
               (re.compile('executable = %s' % re.escape(sys.executable)),
                'executable = python'),
               (re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}'),
                'YYYY-MM-DD hh:mm:ss.dddddd'),
               ]),
            ),
        doctest.DocFileSuite(
            'debugging.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
                zc.buildout.testing.not_found,
                zc.buildout.testing.adding_find_link,
                (re.compile('zc.buildout.buildout.MissingOption'),
                 'MissingOption'),
                (re.compile(r'\S+buildout.py'), 'buildout.py'),
                (re.compile(r'line \d+'), 'line NNN'),
                (re.compile(r'py\(\d+\)'), 'py(NNN)'),
                ])
            ),

        doctest.DocFileSuite(
            'update.txt',
            setUp=updateSetup,
            tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=renormalizing.RENormalizing([
                (re.compile(r'(zc.buildout|setuptools)-\d+[.]\d+\S*'
                            '-py\d.\d.egg'),
                 '\\1.egg'),
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_script,
                zc.buildout.testing.normalize_egg_py,
                zc.buildout.testing.not_found,
                zc.buildout.testing.adding_find_link,
                normalize_bang,
                normalize_S,
                # (re.compile(r"Installing 'zc.buildout >=\S+"), ''),
                (re.compile(r"Getting distribution for 'zc.buildout>=\S+"),
                 ''),
                (re.compile('99[.]99'), 'NINETYNINE.NINETYNINE'),
                (re.compile(
                    r'(zc.buildout|setuptools)( version)? \d+[.]\d+\S*'),
                 '\\1 V.V'),
                (re.compile('[-d]  setuptools'), '-  setuptools'),
                (re.compile(re.escape(os.path.sep)+'+'), '/'),
               ])
            ),

        doctest.DocFileSuite(
            'easy_install.txt', 'downloadcache.txt', 'dependencylinks.txt',
            'allowhosts.txt', 'allow-unknown-extras.txt',
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_script,
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_egg_py,
                zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
                zc.buildout.testing.adding_find_link,
                zc.buildout.testing.not_found,
                normalize_bang,
                normalize_S,
                (re.compile('[-d]  setuptools-\S+[.]egg'), 'setuptools.egg'),
                (re.compile(r'\\[\\]?'), '/'),
                (re.compile('(\n?)-  ([a-zA-Z_.-]+)\n-  \\2.exe\n'),
                 '\\1-  \\2\n'),
               ]+(sys.version_info < (2, 5) and [
                  (re.compile('.*No module named runpy.*', re.S), ''),
                  (re.compile('.*usage: pdb.py scriptfile .*', re.S), ''),
                  (re.compile('.*Error: what does not exist.*', re.S), ''),
                  ] or [])),


            ),

        doctest.DocFileSuite(
            'download.txt', 'extends-cache.txt',
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=renormalizing.RENormalizing([
              zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
              zc.buildout.testing.not_found,
              zc.buildout.testing.adding_find_link,
              (re.compile(' at -?0x[^>]+'), '<MEM ADDRESS>'),
              (re.compile('http://localhost:[0-9]{4,5}/'),
               'http://localhost/'),
              (re.compile('[0-9a-f]{32}'), '<MD5 CHECKSUM>'),
              zc.buildout.testing.normalize_path,
              zc.buildout.testing.ignore_not_upgrading,
              ]),
            ),

        doctest.DocTestSuite(
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
                normalize_bang,
                (re.compile(r'^(\w+\.)*(Missing\w+: )'), '\2'),
                (re.compile("buildout: Running \S*setup.py"),
                 'buildout: Running setup.py'),
                (re.compile('setuptools-\S+-'),
                 'setuptools.egg'),
                (re.compile('zc.buildout-\S+-'),
                 'zc.buildout.egg'),
                (re.compile('setuptools = \S+'), 'setuptools = 0.7.99'),
                (re.compile('File "\S+one.py"'),
                 'File "one.py"'),
                (re.compile(r'We have a develop egg: (\S+) (\S+)'),
                 r'We have a develop egg: \1 V'),
                (re.compile('Picked: setuptools = \S+'),
                 'Picked: setuptools = V'),
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
            ),
        zc.buildout.rmtree.test_suite(),
        doctest.DocFileSuite(
            'windows.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.testing.not_found,
               zc.buildout.testing.adding_find_link,
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               (re.compile('[-d]  setuptools-\S+[.]egg'), 'setuptools.egg'),
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('creating \S*setup.cfg'), 'creating setup.cfg'),
               (re.compile('hello\%ssetup' % os.path.sep), 'hello/setup'),
               (re.compile('Picked: (\S+) = \S+'),
                'Picked: \\1 = V.V'),
               (re.compile(r'We have a develop egg: zc.buildout (\S+)'),
                'We have a develop egg: zc.buildout X.X.'),
               (re.compile(r'\\[\\]?'), '/'),
               (re.compile('WindowsError'), 'OSError'),
               (re.compile(r'\[Error 17\] Cannot create a file '
                           r'when that file already exists: '),
                '[Errno 17] File exists: '
                ),
               ])
            ),
        doctest.DocFileSuite('testing_bugfix.txt'),
    ]

    docdir = os.path.join(ancestor(__file__, 4), 'doc')
    if os.path.exists(docdir) and not sys.platform.startswith('win'):
        # Note that the purpose of the documentation tests are mainly
        # to test the documentation, not to test buildout.

        def docSetUp(test):

            def write(text, *path):
                with open(os.path.join(*path), 'w') as f:
                    f.write(text)

            test.globs.update(
                run_buildout=zc.buildout.testing.run_buildout_in_process,
                yup=lambda cond, orelse='Nope': None if cond else orelse,
                nope=lambda cond, orelse='Nope': orelse if cond else None,
                eq=lambda a, b: None if a == b else (a, b),
                eqs=zc.buildout.testing.eqs,
                read=zc.buildout.testing.read,
                write=write,
                ls=lambda d='.', *rest: os.listdir(os.path.join(d, *rest)),
                join=os.path.join,
                clear_here=zc.buildout.testing.clear_here,
                os=os,
                )
            setupstack.setUpDirectory(test)

        test_suite.append(
            manuel.testing.TestSuite(
                manuel.doctest.Manuel(
                    optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
                    ) + manuel.capture.Manuel(),
                os.path.join(docdir, 'getting-started.rst'),
                os.path.join(docdir, 'reference.rst'),
                os.path.join(docdir, 'topics', 'bootstrapping.rst'),
                os.path.join(docdir, 'topics', 'implicit-parts.rst'),
                os.path.join(
                    docdir,
                    'topics', 'variables-extending-and-substitutions.rst'),
                os.path.join(docdir, 'topics', 'writing-recipes.rst'),
                os.path.join(docdir, 'topics', 'optimizing.rst'),
                os.path.join(docdir, 'topics', 'meta-recipes.rst'),
                setUp=docSetUp, tearDown=setupstack.tearDown
                ))


    # adding bootstrap.txt doctest to the suite
    # only if bootstrap.py is present
    if os.path.exists(bootstrap_py):
        test_suite.append(doctest.DocFileSuite(
            'bootstrap.txt', 'bootstrap_cl_settings.test',
            setUp=bootstrapSetup,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.not_found,
               normalize_bang,
               zc.buildout.testing.adding_find_link,
               (re.compile('Downloading.*setuptools.*egg\n'), ''),
               ]),
            ))

    test_suite.append(unittest.defaultTestLoader.loadTestsFromName(__name__))

    return unittest.TestSuite(test_suite)

if __name__ == '__main__':
    unittest.main()
