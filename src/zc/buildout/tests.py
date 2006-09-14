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

import os, re, shutil, sys, unittest, zipfile
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
    buildout: Installing debug
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

    >>> sample_buildout = mkdtemp()
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
     Deccreaae the level of verbosity.  This option can be used multiple times.
<BLANKLINE>
  -c config_file
<BLANKLINE>
     Specify the path to the buildout configuration file to be used.
     This defaults to the file named"buildout.cfg" in the current
     working directory. 
<BLANKLINE>
Assignments are of the form: section:option=value and are used to
provide configuration options that override those givem in the
configuration file.  For example, to run the buildout in offline mode,
use buildout:offline=true.
<BLANKLINE>
Options and assignments can be interspersed.
<BLANKLINE>
Commmonds:
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
     Deccreaae the level of verbosity.  This option can be used multiple times.
<BLANKLINE>
  -c config_file
<BLANKLINE>
     Specify the path to the buildout configuration file to be used.
     This defaults to the file named"buildout.cfg" in the current
     working directory. 
<BLANKLINE>
Assignments are of the form: section:option=value and are used to
provide configuration options that override those givem in the
configuration file.  For example, to run the buildout in offline mode,
use buildout:offline=true.
<BLANKLINE>
Options and assignments can be interspersed.
<BLANKLINE>
Commmonds:
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

def linkerSetUp(test):
    zc.buildout.testing.buildoutSetUp(test, clear_home=False)
    zc.buildout.testing.multi_python(test)
    zc.buildout.testing.setUpServer(test, zc.buildout.testing.make_tree(test))

def easy_install_SetUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    zc.buildout.testing.multi_python(test)
    zc.buildout.testing.add_source_dist(test)
    zc.buildout.testing.setUpServer(test, zc.buildout.testing.make_tree(test))

class PythonNormalizing(renormalizing.RENormalizing):

    def _transform(self, want, got):
        if '/xyzsample-install/' in want:
            got = got.replace('-py2.4.egg', '-py2.3.egg')
            firstg = got.split('\n')[0]
            firstw = want.split('\n')[0]
            if firstg.startswith('#!') and firstw.startswith('#!'):
                firstg = ' '.join(firstg.split()[1:])
                got = firstg + '\n' + '\n'.join(got.split('\n')[1:])
                firstw = ' '.join(firstw.split()[1:])
                want = firstw + '\n' + '\n'.join(want.split('\n')[1:])
        
        for pattern, repl in self.patterns:
            want = pattern.sub(repl, want)
            got = pattern.sub(repl, got)

        return want, got

    def check_output(self, want, got, optionflags):
        if got == want:
            return True

        want, got = self._transform(want, got)
        if got == want:
            return True
            
        return doctest.OutputChecker.check_output(self, want, got, optionflags)

    def output_difference(self, example, got, optionflags):

        want = example.want

        # If want is empty, use original outputter. This is useful
        # when setting up tests for the first time.  In that case, we
        # generally use the differencer to display output, which we evaluate
        # by hand.
        if not want.strip():
            return doctest.OutputChecker.output_difference(
                self, example, got, optionflags)

        # Dang, this isn't as easy to override as we might wish
        original = want
        want, got = self._transform(want, got)

        # temporarily hack example with normalized want:
        example.want = want
        result = doctest.OutputChecker.output_difference(
            self, example, got, optionflags)
        example.want = original

        return result

        

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
    test.globs['new_releases'] = new_releases = test.globs['mkdtemp']()
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
    
def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'buildout.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               (re.compile('\S+sample-(\w+)%s(\S+)' % os_path_sep),
                r'/sample-\1/\2'),
               (re.compile('\S+sample-(\w+)'), r'/sample-\1'),
               (re.compile('executable = \S+python\S*'),
                'executable = python'),
               (re.compile('setuptools-\S+[.]egg'), 'setuptools.egg'),
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('creating \S*setup.cfg'), 'creating setup.cfg'),
               (re.compile('(\n?)-  ([a-zA-Z_.-]+)-script.py\n-  \\2.exe\n'),
                '\\1-  \\2\n'),
               (re.compile("(\w)%s(\w)" % os_path_sep), r"\1/\2"),
               ])
            ),

        doctest.DocFileSuite(
            'update.txt',
            setUp=updateSetup,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('#!\S+python\S*'), '#!python'),
               (re.compile('\S+sample-(\w+)'), r'/sample-\1'),
               (re.compile('-py\d[.]\d.egg'), r'-py2.3.egg'),
               (re.compile(r'\\+'), '/'),
               ])
            ),
        
        doctest.DocFileSuite(
            'easy_install.txt', 
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,

            checker=PythonNormalizing([
               (re.compile("'"
                           "(\w:)?"
                           "[%(sep)s/]\S+sample-install[%(sep)s/]"
                           "[%(sep)s/]?(dist"
                           "[%(sep)s/])?"
                           % dict(sep=os_path_sep)),
                '/sample-eggs/'),
               (re.compile("([d-]  ((ext)?demo(needed)?|other)"
                           "-\d[.]\d-py)\d[.]\d(-\S+)?[.]egg"),
                '\\1V.V.egg'),
               (re.compile('(\n?)-  ([a-zA-Z_.-]+)-script.py\n-  \\2.exe\n'),
                '\\1-  \\2\n'),
               (re.compile('extdemo-1[.]4[.]tar[.]gz'), 'extdemo-1.4.zip'),
               (re.compile('#!\S+python\S+'), '#!python'),
               ]),
            ),
        doctest.DocTestSuite(
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,

            checker=PythonNormalizing([
               (re.compile("buildout: Running \S*setup.py"),
                'buildout: Running setup.py'),
               (re.compile('py_zc'), 'py-zc'), # XXX get rid of after next rel
               (re.compile('setuptools-\S+-py\d.\d.egg'),
                'setuptools.egg'),
               (re.compile('zc.buildout-\S+-py\d.\d.egg'),
                'zc.buildout.egg'),
               (re.compile('(\n?)-  ([a-zA-Z_.-]+)-script.py\n-  \\2.exe\n'),
                '\\1-  \\2\n'),
               ]),
            )
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

