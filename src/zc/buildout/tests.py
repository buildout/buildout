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

import os, re, shutil, sys, unittest
from zope.testing import doctest, renormalizing
import zc.buildout.testing

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

    >>> print system(buildout+' -v'), # doctest: +ELLIPSIS
    buildout: Running ...setup.py -q develop ...
    buildout: Installing debug

If we run the buildout again, we shoudn't get a message about
uninstalling anything because the configuration hasn't changed.

    >>> print system(buildout+' -v'),
    buildout: Running setup.py -q develop ...
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
    
    >>> ls(sample_buildout)
    d  bin
    -  bootstrap.py
    -  buildout.cfg
    d  develop-eggs
    d  eggs
    d  parts


    >>> ls(sample_buildout, 'bin')
    -  buildout
    -  py-zc.buildout

    >>> ls(sample_buildout, 'eggs')
    -  setuptools-0.6-py2.4.egg
    d  zc.buildout-1.0-py2.4.egg

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
                           "-\d[.]\d-py)\d[.]\d(-[^. \t\n]+)?[.]egg"),
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
               ]),
            )
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

