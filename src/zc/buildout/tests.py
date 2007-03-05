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

import os, re, shutil, sys, tempfile, unittest, zipfile
from zope.testing import doctest, renormalizing
import pkg_resources
import zc.buildout.testing, zc.buildout.easy_install

os_path_sep = os.path.sep
if os_path_sep == '\\':
    os_path_sep *= 2


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

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/foo

    >>> ls('develop-eggs')
    -  foo.egg-link

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

    >>> print system(join('bin', 'buildout')+' -vv'), # doctest: +ELLIPSIS
    zc.buildout...
    buildout: Develop: /sample-buildout/foo
    ...
    Installed /sample-buildout/foo
    ...

    >>> ls('develop-eggs')
    -  foo.egg-link

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

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    Error: Circular reference in substitutions.
    We're evaluating buildout:y, buildout:z, buildout:x
    and are referencing: buildout:y.

It is an error to use funny characters in variable refereces:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${bui$ldout:y}
    ... ''')

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
    Error: The section name in substitution, ${bui$ldout:y},
    has invalid characters.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y{z}
    ... ''')

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
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

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
    Error: The substitution, ${parts},
    doesn't contain a colon.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y:z}
    ... ''')

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
    Error: The substitution, ${buildout:y:z},
    has too many colons.

Al parts have to have a section:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ... ''')

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
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

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
    Error: Missing option: x:recipe

"""
 
def test_comparing_saved_options_with_funny_characters():
    """
    If an option has newlines, extra/odd spaces or a %, we need to make
    sure the comparison with the saved value works correctly.

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

    >>> print system(buildout),
    buildout: Develop: /sample-buildout/recipes
    buildout: Installing debug

If we run the buildout again, we shoudn't get a message about
uninstalling anything because the configuration hasn't changed.

    >>> print system(buildout),
    buildout: Develop: /sample-buildout/recipes
    buildout: Updating debug
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

def make_sure__get_version_works_with_2_digit_python_versions():
    """

This is a test of an internal function used by higher-level machinery.

We'll start by creating a faux 'python' that executable that prints a
2-digit version. This is a bit of a pain to do portably. :(

    >>> mkdir('demo')
    >>> write('demo', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='demo',
    ...       entry_points = {'console_scripts': ['demo = demo:main']},
    ...       )
    ... ''')
    >>> write('demo', 'demo.py',
    ... '''
    ... def main():
    ...     print 'Python 2.5'
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = demo
    ... parts = 
    ... ''')

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/demo

    >>> import zc.buildout.easy_install
    >>> ws = zc.buildout.easy_install.working_set(
    ...    ['demo'], sys.executable, ['develop-eggs'])
    >>> zc.buildout.easy_install.scripts(
    ...    ['demo'], ws, sys.executable, 'bin')
    ['bin/demo']

    >>> print system(join('bin', 'demo')),
    Python 2.5

Now, finally, let's test _get_version:

    >>> zc.buildout.easy_install._get_version(join('bin', 'demo'))
    '2.5'

    """

# Why?
## def error_for_undefined_install_parts():
##     """
## Any parts we pass to install on the command line must be
## listed in the configuration.

##     >>> print system(join('bin', 'buildout') + ' install foo'),
##     buildout: Invalid install parts: foo.
##     Install parts must be listed in the configuration.

##     >>> print system(join('bin', 'buildout') + ' install foo bar'),
##     buildout: Invalid install parts: foo bar.
##     Install parts must be listed in the configuration.
    
##     """


bootstrap_py = os.path.join(
       os.path.dirname(
          os.path.dirname(
             os.path.dirname(
                os.path.dirname(zc.buildout.__file__)
                )
             )
          ),
       'bootstrap', 'bootstrap.py')
if os.path.exists(bootstrap_py):
    def test_bootstrap_py():
        """Make sure the bootstrap script actually works

    >>> sample_buildout = tmpdir('sample')
    >>> os.chdir(sample_buildout)
    >>> write('bootstrap.py', open(bootstrap_py).read())
    >>> print system(sys.executable+' '+'bootstrap.py'), # doctest: +ELLIPSIS
    Downloading ...
    Warning: creating ...buildout.cfg
    buildout: Creating directory ...bin
    buildout: Creating directory ...parts
    buildout: Creating directory ...eggs
    buildout: Creating directory ...develop-eggs

    >>> ls(sample_buildout)
    d  bin
    -  bootstrap.py
    -  buildout.cfg
    d  develop-eggs
    d  eggs
    d  parts


    >>> ls(sample_buildout, 'bin')
    -  buildout

    >>> ls(sample_buildout, 'eggs')
    -  setuptools-0.6-py2.4.egg
    d  zc.buildout-1.0-py2.4.egg

    """

def test_help():
    """
>>> print system(os.path.join(sample_buildout, 'bin', 'buildout')+' -h'),
Usage: buildout [options] [assignments] [command [command arguments]]
<BLANKLINE>
Options:
<BLANKLINE>
  -h, --help
<BLANKLINE>
     Print this message and exit.
<BLANKLINE>
  -v
<BLANKLINE>
     Increase the level of verbosity.  This option can be used multiple times.
<BLANKLINE>
  -q
<BLANKLINE>
     Decrease the level of verbosity.  This option can be used multiple times.
<BLANKLINE>
  -c config_file
<BLANKLINE>
     Specify the path to the buildout configuration file to be used.
     This defaults to the file named "buildout.cfg" in the current
     working directory.
<BLANKLINE>
  -U
<BLANKLINE>
     Don't read user defaults.
<BLANKLINE>
  -o
<BLANKLINE>
    Run in off-line mode.  This is equivalent to the assignment 
    buildout:offline=true.
<BLANKLINE>
  -O
<BLANKLINE>
    Run in non-off-line mode.  This is equivalent to the assignment 
    buildout:offline=false.  This is the default buildout mode.  The
    -O option would normally be used to override a true offline
    setting in a configuration file.
<BLANKLINE>
  -n
<BLANKLINE>
    Run in newest mode.  This is equivalent to the assignment
    buildout:newest=true.  With this setting, which is the default,
    buildout will try to find the newest versions of distributions
    available that satisfy its requirements.
<BLANKLINE>
  -N
<BLANKLINE>
    Run in non-newest mode.  This is equivalent to the assignment 
    buildout:newest=false.  With this setting, buildout will not seek
    new distributions if installed distributions satisfy it's
    requirements. 
<BLANKLINE>
Assignments are of the form: section:option=value and are used to
provide configuration options that override those given in the
configuration file.  For example, to run the buildout in offline mode,
use buildout:offline=true.
<BLANKLINE>
Options and assignments can be interspersed.
<BLANKLINE>
Commands:
<BLANKLINE>
  install [parts]
<BLANKLINE>
    Install parts.  If no command arguments are given, then the parts
    definition from the configuration file is used.  Otherwise, the
    arguments specify the parts to be installed.
<BLANKLINE>
  bootstrap
<BLANKLINE>
    Create a new buildout in the current working directory, copying
    the buildout and setuptools eggs and, creating a basic directory
    structure and a buildout-local buildout script.
<BLANKLINE>
<BLANKLINE>

>>> print system(os.path.join(sample_buildout, 'bin', 'buildout')
...              +' --help'),
Usage: buildout [options] [assignments] [command [command arguments]]
<BLANKLINE>
Options:
<BLANKLINE>
  -h, --help
<BLANKLINE>
     Print this message and exit.
<BLANKLINE>
  -v
<BLANKLINE>
     Increase the level of verbosity.  This option can be used multiple times.
<BLANKLINE>
  -q
<BLANKLINE>
     Decrease the level of verbosity.  This option can be used multiple times.
<BLANKLINE>
  -c config_file
<BLANKLINE>
     Specify the path to the buildout configuration file to be used.
     This defaults to the file named "buildout.cfg" in the current
     working directory.
<BLANKLINE>
  -U
<BLANKLINE>
     Don't read user defaults.
<BLANKLINE>
  -o
<BLANKLINE>
    Run in off-line mode.  This is equivalent to the assignment 
    buildout:offline=true.
<BLANKLINE>
  -O
<BLANKLINE>
    Run in non-off-line mode.  This is equivalent to the assignment 
    buildout:offline=false.  This is the default buildout mode.  The
    -O option would normally be used to override a true offline
    setting in a configuration file.
<BLANKLINE>
  -n
<BLANKLINE>
    Run in newest mode.  This is equivalent to the assignment
    buildout:newest=true.  With this setting, which is the default,
    buildout will try to find the newest versions of distributions
    available that satisfy its requirements.
<BLANKLINE>
  -N
<BLANKLINE>
    Run in non-newest mode.  This is equivalent to the assignment 
    buildout:newest=false.  With this setting, buildout will not seek
    new distributions if installed distributions satisfy it's
    requirements. 
<BLANKLINE>
Assignments are of the form: section:option=value and are used to
provide configuration options that override those given in the
configuration file.  For example, to run the buildout in offline mode,
use buildout:offline=true.
<BLANKLINE>
Options and assignments can be interspersed.
<BLANKLINE>
Commands:
<BLANKLINE>
  install [parts]
<BLANKLINE>
    Install parts.  If no command arguments are given, then the parts
    definition from the configuration file is used.  Otherwise, the
    arguments specify the parts to be installed.
<BLANKLINE>
  bootstrap
<BLANKLINE>
    Create a new buildout in the current working directory, copying
    the buildout and setuptools eggs and, creating a basic directory
    structure and a buildout-local buildout script.
<BLANKLINE>
<BLANKLINE>
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
    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')
    ...              + ' bootstrap'),
    buildout: Creating directory /sample-bootstrap/bin
    buildout: Creating directory /sample-bootstrap/parts
    buildout: Creating directory /sample-bootstrap/eggs
    buildout: Creating directory /sample-bootstrap/develop-eggs
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

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/foo

    >>> ls('develop-eggs')
    -  foox.egg-link

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

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/foo
    buildout: Develop: /sample-buildout/bar

    >>> ls('develop-eggs')
    -  foox.egg-link
    -  fooy.egg-link

Remove one:

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = bar
    ... parts =
    ... """)
    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/bar

It is gone

    >>> ls('develop-eggs')
    -  fooy.egg-link

Remove the other:

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... parts =
    ... """)
    >>> print system(join('bin', 'buildout')),

All gone

    >>> ls('develop-eggs')
    '''


def add_setuptools_to_dependencies_when_namespace_packages():
    '''    
Often, a package depends on setuptools soley by virtue of using
namespace packages. In this situation, package authors often forget to
declare setuptools as a dependency. This is a mistake, but,
unfortunately, a common one that we need to work around.  If an egg
uses namespace packages and does not include setuptools as a depenency,
we will still include setuptools in the working set.  If we see this for
a devlop egg, we will also generate a warning.

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

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/foo

Now, if we generate a working set using the egg link, we will get a warning
and we will get setuptools included in the working set.

    >>> import logging, zope.testing.loggingsupport
    >>> handler = zope.testing.loggingsupport.InstalledHandler(
    ...        'zc.buildout', level=logging.WARNING)
    >>> logging.getLogger('zc').propagate = False
    
    >>> [dist.project_name
    ...  for dist in zc.buildout.easy_install.working_set(
    ...    ['foox'], sys.executable,
    ...    [join(sample_buildout, 'eggs'),
    ...     join(sample_buildout, 'develop-eggs'),
    ...     ])]
    ['foox', 'setuptools']

    >>> print handler
    zc.buildout.easy_install WARNING
      Develop distribution for foox 0.0.0
    uses namespace packages but the distribution does not require setuptools.

    >>> handler.clear()

On the other hand, if we have a regular egg, rather than a develop egg:

    >>> os.remove(join('develop-eggs', 'foox.egg-link'))

    >>> _ = system(join('bin', 'buildout') + ' setup foo bdist_egg -d'
    ...            + join(sample_buildout, 'eggs'))

    >>> ls('develop-eggs')
    
    >>> ls('eggs') # doctest: +ELLIPSIS
    -  foox-0.0.0-py2.4.egg
    ...
    
We do not get a warning, but we do get setuptools included in the working set:

    >>> [dist.project_name
    ...  for dist in zc.buildout.easy_install.working_set(
    ...    ['foox'], sys.executable,
    ...    [join(sample_buildout, 'eggs'),
    ...     join(sample_buildout, 'develop-eggs'),
    ...     ])]
    ['foox', 'setuptools']

    >>> print handler,

We get the same behavior if the it is a depedency that uses a
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

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/foo
    buildout: Develop: /sample-buildout/bar

    >>> [dist.project_name
    ...  for dist in zc.buildout.easy_install.working_set(
    ...    ['bar'], sys.executable,
    ...    [join(sample_buildout, 'eggs'),
    ...     join(sample_buildout, 'develop-eggs'),
    ...     ])]
    ['bar', 'foox', 'setuptools']

    >>> print handler,
    zc.buildout.easy_install WARNING
      Develop distribution for foox 0.0.0
    uses namespace packages but the distribution does not require setuptools.


    >>> logging.getLogger('zc').propagate = True
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
    """
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
    ... '''
    ... class Install:
    ...     def __init__(*args): pass
    ...     def install(self):
    ...         print 'installing'
    ...         return ()
    ... def uninstall(name, options): print 'uninstalling'
    ... ''')

    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts = demo
    ... [demo]
    ... recipe = recipes:demo
    ... ''')

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/recipes
    buildout: Installing demo
    installing


    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts = demo
    ... [demo]
    ... recipe = recipes:demo
    ... x = 1
    ... ''')

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/recipes
    buildout: Uninstalling demo
    buildout: Running uninstall recipe
    uninstalling
    buildout: Installing demo
    installing


    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts = 
    ... ''')

    >>> print system(join('bin', 'buildout')),
    buildout: Develop: /sample-buildout/recipes
    buildout: Uninstalling demo
    buildout: Running uninstall recipe
    uninstalling

"""

def extensions_installed_as_eggs_work_in_offline_mode():
    '''
    >>> mkdir('demo')

    >>> write('demo', 'demo.py', 
    ... """
    ... def ext(buildout):
    ...     print 'ext', list(buildout)
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

    >>> print system(join(sample_buildout, 'bin', 'buildout')),
    ext ['buildout']
    

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


    >>> print system(join(sample_buildout, 'bin', 'buildout')),
    buildout: Develop: /sample-buildout/recipe
    buildout: Installing foo

    >>> mkdir('recipe', '.svn')
    >>> mkdir('recipe', 'CVS')
    >>> print system(join(sample_buildout, 'bin', 'buildout')),
    buildout: Develop: /sample-buildout/recipe
    buildout: Updating foo

    >>> write('recipe', '.svn', 'x', '1')
    >>> write('recipe', 'CVS', 'x', '1')

    >>> print system(join(sample_buildout, 'bin', 'buildout')),
    buildout: Develop: /sample-buildout/recipe
    buildout: Updating foo

    """

def o_option_sets_offline():
    """
    >>> print system(join(sample_buildout, 'bin', 'buildout')+' -vvo'),
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    ...
    offline = true
    ...
    """

def recipe_upgrade():
    """

The buildout will upgrade recipes in newest (and non-offline) mode.

Let's create a recipe egg

    >>> mkdir('recipe')
    >>> write('recipe', 'recipe.py',
    ... '''
    ... class Recipe:
    ...     def __init__(*a): pass
    ...     def install(self):
    ...         print 'recipe v1'
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

    >>> print system(buildout+' setup recipe bdist_egg'), # doctest: +ELLIPSIS
    buildout: Running setup script recipe/setup.py
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

    >>> print system(buildout),
    zc.buildout.easy_install: Getting new distribution for recipe
    zc.buildout.easy_install: Got recipe 1
    buildout: Installing foo
    recipe v1

Now, if we update the recipe egg:

    >>> write('recipe', 'recipe.py',
    ... '''
    ... class Recipe:
    ...     def __init__(*a): pass
    ...     def install(self):
    ...         print 'recipe v2'
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


    >>> print system(buildout+' setup recipe bdist_egg'), # doctest: +ELLIPSIS
    buildout: Running setup script recipe/setup.py
    ...

We won't get the update if we specify -N:

    >>> print system(buildout+' -N'),
    buildout: Updating foo
    recipe v1

or if we use -o:

    >>> print system(buildout+' -o'),
    buildout: Updating foo
    recipe v1

But we will if we use neither of these:

    >>> print system(buildout),
    zc.buildout.easy_install: Getting new distribution for recipe
    zc.buildout.easy_install: Got recipe 2
    buildout: Uninstalling foo
    buildout: Installing foo
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

    >>> print system(buildout),
    buildout: Uninstalling foo
    buildout: Installing foo
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

    >>> print system(buildout),
    buildout: Develop: /tmp/tmpbHOHnU/_TEST_/sample-buildout/recipe
    buildout: Installing foo

    >>> print system(buildout),
    buildout: Develop: /tmp/tmpbHOHnU/_TEST_/sample-buildout/recipe
    buildout: Updating foo

    >>> cat('.installed.cfg') # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    [buildout]
    ...
    [foo]
    __buildout_installed__ = c
    	d
    	e
    	a
    	b
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

    >>> print handler # doctest: +ELLIPSIS
    zc.buildout.easy_install DEBUG
      Installing ['demo==0.2']
    zc.buildout.easy_install DEBUG
      We have no distributions for demo that satisfies demo==0.2.
    ...

    >>> handler.uninstall()
    >>> logger.propagate = old_propogate
    
    """

######################################################################
    
def create_sample_eggs(test, executable=sys.executable):
    write = test.globs['write']
    dest = test.globs['sample_eggs']
    tmp = tempfile.mkdtemp()
    try:
        write(tmp, 'README.txt', '')

        for i in (0, 1):
            write(tmp, 'eggrecipedemobeeded.py', 'y=%s\n' % i)
            write(
                tmp, 'setup.py',
                "from setuptools import setup\n"
                "setup(name='demoneeded', py_modules=['eggrecipedemobeeded'],"
                " zip_safe=True, version='1.%s', author='bob', url='bob', "
                "author_email='bob')\n"
                % i
                )
            zc.buildout.testing.sdist(tmp, dest)

        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='other', zip_safe=False, version='1.0', "
            "py_modules=['eggrecipedemobeeded'])\n"
            )
        zc.buildout.testing.bdist_egg(tmp, executable, dest)

        os.remove(os.path.join(tmp, 'eggrecipedemobeeded.py'))

        for i in (1, 2, 3):
            write(
                tmp, 'eggrecipedemo.py',
                'import eggrecipedemobeeded\n'
                'x=%s\n'
                'def main(): print x, eggrecipedemobeeded.y\n'
                % i)
            write(
                tmp, 'setup.py',
                "from setuptools import setup\n"
                "setup(name='demo', py_modules=['eggrecipedemo'],"
                " install_requires = 'demoneeded',"
                " entry_points={'console_scripts': "
                     "['demo = eggrecipedemo:main']},"
                " zip_safe=True, version='0.%s')\n" % i
                )
            zc.buildout.testing.bdist_egg(tmp, executable, dest)
    finally:
        shutil.rmtree(tmp)

extdemo_c = """
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

extdemo_setup_py = """
from distutils.core import setup, Extension

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

        
egg_parse = re.compile('([0-9a-zA-Z_.]+)-([0-9a-zA-Z_.]+)-py(\d[.]\d).egg$'
                       ).match
def makeNewRelease(project, ws, dest):
    dist = ws.find(pkg_resources.Requirement.parse(project))
    eggname, oldver, pyver = egg_parse(
        os.path.basename(dist.location)
        ).groups()
    dest = os.path.join(dest, "%s-99.99-py%s.egg" % (eggname, pyver)) 
    if os.path.isfile(dist.location):
        shutil.copy(dist.location, dest)
        zip = zipfile.ZipFile(dest, 'a')
        zip.writestr(
            'EGG-INFO/PKG-INFO',
            zip.read('EGG-INFO/PKG-INFO').replace("Version: %s" % oldver, 
                                                  "Version: 99.99")
            )
        zip.close()
    else:
        shutil.copytree(dist.location, dest)
        info_path = os.path.join(dest, 'EGG-INFO', 'PKG-INFO')
        info = open(info_path).read().replace("Version: %s" % oldver, 
                                              "Version: 99.99")
        open(info_path, 'w').write(info)


def updateSetup(test):
    zc.buildout.testing.buildoutSetUp(test)
    new_releases = test.globs['tmpdir']('new_releases')
    test.globs['new_releases'] = new_releases
    sample_buildout = test.globs['sample_buildout']
    eggs = os.path.join(sample_buildout, 'eggs')

    # If the zc.buildout dist is a develo dist, convert it to a
    # regular egg in the sample buildout
    req = pkg_resources.Requirement.parse('zc.buildout')
    dist = pkg_resources.working_set.find(req)
    if dist.precedence == pkg_resources.DEVELOP_DIST:
        # We have a develop egg, create a real egg for it:
        here = os.getcwd()
        os.chdir(os.path.dirname(dist.location))
        assert os.spawnle(
            os.P_WAIT, sys.executable, sys.executable,
            os.path.join(os.path.dirname(dist.location), 'setup.py'),
            '-q', 'bdist_egg', '-d', eggs,
            dict(os.environ,
                 PYTHONPATH=pkg_resources.working_set.find(
                               pkg_resources.Requirement.parse('setuptools')
                               ).location,
                 ),
            ) == 0
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

    # now let's make the new releases
    makeNewRelease('zc.buildout', ws, new_releases)
    makeNewRelease('setuptools', ws, new_releases)

    os.mkdir(os.path.join(new_releases, 'zc.buildout'))
    os.mkdir(os.path.join(new_releases, 'setuptools'))

    
    
normalize_bang = (
    re.compile(re.escape('#!'+sys.executable)),
    '#!/usr/local/bin/python2.4',
    )

def test_suite():
    import zc.buildout.testselectingpython
    suite = unittest.TestSuite((
        doctest.DocFileSuite(
            'buildout.txt', 'runsetup.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               (re.compile('executable = \S+python\S*'),
                'executable = python'),
               (re.compile('[-d]  setuptools-\S+[.]egg'), 'setuptools.egg'),
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('creating \S*setup.cfg'), 'creating setup.cfg'),
               (re.compile('hello\%ssetup' % os.path.sep), 'hello/setup'),
               ])
            ),

        doctest.DocFileSuite(
            'update.txt',
            setUp=updateSetup,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               normalize_bang,
               (re.compile('99[.]99'), 'NINETYNINE.NINETYNINE'),
               (re.compile('(zc.buildout|setuptools)-\d+[.]\d+\S*'
                           '-py\d.\d.egg'),
                '\\1.egg'),
               (re.compile('(zc.buildout|setuptools)( version)? \d+[.]\d+\S*'),
                '\\1 V.V'),
               (re.compile('[-d]  setuptools'), '-  setuptools'),
               ])
            ),
        
        doctest.DocFileSuite(
            'easy_install.txt', 
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,

            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               normalize_bang,
               (re.compile('extdemo[.]pyd'), 'extdemo.so')
               ]),
            ),
        doctest.DocTestSuite(
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               (re.compile("buildout: Running \S*setup.py"),
                'buildout: Running setup.py'),
               (re.compile('setuptools-\S+-'),
                'setuptools.egg'),
               (re.compile('zc.buildout-\S+-'),
                'zc.buildout.egg'),
               ]),
            ),
        ))

    if sys.version_info[:2] != (2, 3):
        # Only run selecting python tests if not 2.3, since
        # 2.3 is the alternate python used in the tests.
        suite.addTest(zc.buildout.testselectingpython.test_suite())

    return suite
