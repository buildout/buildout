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

def buildout_error_handling():
    r"""Buildout error handling

Asking for a section that doesn't exist, yields a key error:

    >>> import os
    >>> os.chdir(sample_buildout)
    >>> import zc.buildout.buildout
    >>> buildout = zc.buildout.buildout.Buildout('buildout.cfg', [])
    >>> buildout['eek']
    Traceback (most recent call last):
    ...
    KeyError: 'eek'

Asking for an option that doesn't exist, a MissingOption error is raised:

    >>> buildout['buildout']['eek']
    Traceback (most recent call last):
    ...
    MissingOption: Missing option: buildout:eek

It is an error to create a variable-reference cycle:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
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
    Error: No section was specified for part x

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

    >>> print system(buildout), # doctest: +ELLIPSIS
    buildout: Develop: ...setup.py
    buildout: Installing debug

If we run the buildout again, we shoudn't get a message about
uninstalling anything because the configuration hasn't changed.

    >>> print system(buildout), # doctest: +ELLIPSIS
    buildout: Develop: ...setup.py
    buildout: Updating debug
"""


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
    PyObject *d;
    d = Py_InitModule3("extdemo", methods, "");
    PyDict_SetItemString(d, "val", PyInt_FromLong(EXTDEMO));    
}
"""

extdemo_setup_py = """
from distutils.core import setup, Extension

setup(name = "extdemo", version = "1.4", url="http://www.zope.org",
      author="Demo", author_email="demo@demo.com",
      ext_modules = [Extension('extdemo', ['extdemo.c'])],
      )
"""

def add_source_dist(test):
    import tarfile
    tmp = tempfile.mkdtemp('test-sdist')
    write = test.globs['write']
    try:
        write(tmp, 'extdemo.c', extdemo_c);
        write(tmp, 'setup.py', extdemo_setup_py);
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
        shutil.copy(dist.location, dest)
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
               (re.compile('setuptools-\S+[.]egg'), 'setuptools.egg'),
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
               ]),
            ),
        doctest.DocTestSuite(
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,

            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               (re.compile("buildout: Running \S*setup.py"),
                'buildout: Running setup.py'),
               (re.compile('py_zc'), 'py-zc'), # XXX get rid of after next rel
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
