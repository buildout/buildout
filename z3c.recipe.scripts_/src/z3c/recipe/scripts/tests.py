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

import os, re, shutil, sys
import zc.buildout.tests
import zc.buildout.testselectingpython
import zc.buildout.testing

import unittest, doctest
from zope.testing import renormalizing

# We do not explicitly test the recipe support for the ``eggs``,
# ``find-links``, and ``index`` options because they are used for most or
# all of the examples.  The README tests ``extends``,
# ``include-site-customization`` and ``name``.  That leaves ``python``,
# ``extra-paths``, ``initialization``, ``relative-paths``, and
# ``include-site-packages``.

def supports_python_option():
    """
This simply shows that the ``python`` option can specify another section to
find the ``executable``.  (The ``python`` option defaults to looking in the
``buildout`` section.)  We do this by creating a custom Python that will have
some initialization that we can look for.

    >>> py_path, site_packages_path = make_py(initialization='''
    ... import os
    ... os.environ['zc.buildout'] = 'foo bar baz shazam'
    ... ''')

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = py
    ...
    ... [custom_python]
    ... executable = %(py_path)s
    ...
    ... [py]
    ... recipe = z3c.recipe.scripts:interpreter
    ... exec-sitecustomize = true
    ... eggs = demo<0.3
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... python = custom_python
    ... ''' % dict(server=link_server, py_path=py_path))

    >>> print system(buildout),
    Installing py.
    Getting distribution for 'demo<0.3'.
    Got demo 0.2.
    Getting distribution for 'demoneeded'.
    Got demoneeded 1.2c1.
    Generated interpreter '/sample-buildout/bin/py'.

    >>> print system(join(sample_buildout, 'bin', 'py') +
    ...              ''' -c "import os; print os.environ['zc.buildout']"'''),
    foo bar baz shazam
"""

if not zc.buildout.testing.script_in_shebang:
    del supports_python_option

def interpreter_recipe_supports_extra_paths_option():
    """
This shows that specifying extra-paths will affect sys.path.

This recipe will not add paths that do not exist, so we create them.

    >>> mkdir(sample_buildout, 'foo')
    >>> mkdir(sample_buildout, 'foo', 'bar')
    >>> mkdir(sample_buildout, 'spam')

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = py
    ...
    ... [py]
    ... recipe = z3c.recipe.scripts:interpreter
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... extra-paths =
    ...    ${buildout:directory}/foo/bar
    ...    ${buildout:directory}/spam
    ... ''' % dict(server=link_server))

    >>> print system(buildout),
    Installing py.
    Generated interpreter '/sample-buildout/bin/py'.
    >>> print system(join(sample_buildout, 'bin', 'py') +
    ...              ''' -c "import sys;print 'path' + ' '.join(sys.path)"''')
    ... # doctest:+ELLIPSIS
    path.../foo/bar /sample-buildout/spam...

"""

def interpreter_recipe_supports_initialization_option():
    """
This simply shows that the ``initialization`` option can specify code to
run on initialization.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = py
    ...
    ... [py]
    ... recipe = z3c.recipe.scripts:interpreter
    ... initialization =
    ...     import os
    ...     os.environ['zc.buildout'] = 'foo bar baz shazam'
    ... eggs = demo<0.3
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... ''' % dict(server=link_server))

    >>> print system(buildout),
    Installing py.
    Getting distribution for 'demo<0.3'.
    Got demo 0.2.
    Getting distribution for 'demoneeded'.
    Got demoneeded 1.2c1.
    Generated interpreter '/sample-buildout/bin/py'.

    >>> cat(sample_buildout, 'parts', 'py', 'sitecustomize.py')
    ... # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
    import os
    os.environ['zc.buildout'] = 'foo bar baz shazam'
    >>> print system(join(sample_buildout, 'bin', 'py') +
    ...              ''' -c "import os; print os.environ['zc.buildout']"'''),
    foo bar baz shazam

This also works with the exec-sitecustomize option, processing local
initialization, and then the Python's initialization.  We show this with a
custom Python.

    >>> py_path, site_packages_path = make_py(initialization='''
    ... import os
    ... os.environ['zc.buildout'] = 'foo bar baz shazam'
    ... ''')

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = py
    ...
    ... [custom_python]
    ... executable = %(py_path)s
    ...
    ... [py]
    ... recipe = z3c.recipe.scripts:interpreter
    ... initialization =
    ...     import os
    ...     os.environ['zc.recipe.egg'] = 'baLOOba'
    ... exec-sitecustomize = true
    ... eggs = demo<0.3
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... python = custom_python
    ... ''' % dict(server=link_server, py_path=py_path))

    >>> print system(buildout),
    Uninstalling py.
    Installing py.
    Generated interpreter '/sample-buildout/bin/py'.

    >>> cat(sample_buildout, 'parts', 'py', 'sitecustomize.py')
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    <BLANKLINE>
    import os
    os.environ['zc.recipe.egg'] = 'baLOOba'
    <BLANKLINE>
    # The following is from
    # /executable_buildout/parts/py/sitecustomize.py
    ...
    import os
    os.environ['zc.buildout'] = 'foo bar baz shazam'

    >>> print system(join(sample_buildout, 'bin', 'py') + ' -c ' +
    ...              '''"import os; print os.environ['zc.recipe.egg']"'''),
    baLOOba
    >>> print system(join(sample_buildout, 'bin', 'py') +
    ...              ''' -c "import os; print os.environ['zc.buildout']"'''),
    foo bar baz shazam

"""

if not zc.buildout.testing.script_in_shebang:
    del interpreter_recipe_supports_initialization_option


def interpreter_recipe_supports_relative_paths_option():
    """
This shows that the relative-paths option affects the code for inserting
paths into sys.path.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = py
    ...
    ... [py]
    ... recipe = z3c.recipe.scripts:interpreter
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... include-site-packages = false
    ... relative-paths = true
    ... extra-paths =
    ...    /foo/bar
    ...    ${buildout:directory}/spam
    ... ''' % dict(server=link_server))

    >>> print system(buildout),
    Installing py.
    Generated interpreter '/sample-buildout/bin/py'.

Let's look at the site.py that was generated:

    >>> import sys
    >>> sys.stdout.write('#'); cat(sample_buildout, 'parts', 'py', 'site.py')
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    #...
    def addsitepackages(known_paths):
        "..."
        join = os.path.join
        base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        base = os.path.dirname(base)
        base = os.path.dirname(base)
        buildout_paths = [
            '/foo/bar',
            join(base, 'spam')
            ]...
"""

def include_site_packages_option_reusing_eggs():
    """
The include-site-packages buildout option not only controls whether
site-packages are included in the path, but whether eggs in site-packages
can be used to fulfill direct and indirect dependencies of your package.  If
it did not, it might fail to exclude site-packages because one of the
dependencies actually was supposed to be fulfilled with it.

The default is ``include-site-packages = true``.  This is backwards
compatible with previous versions of zc.buildout.

As a demonstration, we will start with a Python executable that has the
"demoneeded" and "demo" eggs installed.  With the value of
include-site-packages to true in the default, the package will be found.
Notice we do not set find-links, but the eggs are still found because
they are in the executable's path.

    >>> from zc.buildout.tests import create_sample_sys_install
    >>> py_path, site_packages_path = make_py()
    >>> create_sample_sys_install(site_packages_path)
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links =
    ...
    ... [primed_python]
    ... executable = %(py_path)s
    ...
    ... [eggs]
    ... recipe = z3c.recipe.scripts
    ... python = primed_python
    ... include-site-packages = true
    ... eggs = demoneeded
    ... ''' % globals())

    >>> print system(buildout),
    Installing eggs.

You can set the value false explicitly.  This makes it possible to
get a more repeatable build from a system Python.  In our example, the
eggs are not found, even though the system Python provides them.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links =
    ...
    ... [primed_python]
    ... executable = %(py_path)s
    ...
    ... [eggs]
    ... recipe = z3c.recipe.scripts
    ... include-site-packages = false
    ... python = primed_python
    ... eggs = demoneeded
    ... ''' % globals())
    >>> print system(buildout)
    Uninstalling eggs.
    Installing eggs.
    Couldn't find index page for 'demoneeded' (maybe misspelled?)
    Getting distribution for 'demoneeded'.
    While:
      Installing eggs.
      Getting distribution for 'demoneeded'.
    Error: Couldn't find a distribution for 'demoneeded'.
    <BLANKLINE>

We get an error if we specify anything but true or false:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = z3c.recipe.scripts
    ... include-site-packages = no
    ... eggs = other
    ... ''' % globals())

    >>> print system(buildout)
    While:
      Installing.
      Getting section eggs.
      Initializing part eggs.
    Error: Invalid value for include-site-packages option: no
    <BLANKLINE>

    """

def allowed_eggs_from_site_packages_option():
    """
The allowed-eggs-from-site-packages option allows you to specify a
whitelist of project names that may be included from site-packages.

In the test below, our "py_path" has the "demoneeded" and "demo"
packages available.  We'll simply be asking for "demoneeded" here.  The
default value of '*' will allow it, as we've seen elsewhere. Here we
explicitly use a "*" for the same result.  This also shows that we
correctly parse a single-line value.


    >>> from zc.buildout.tests import create_sample_sys_install
    >>> py_path, site_packages_path = make_py()
    >>> create_sample_sys_install(site_packages_path)
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links =
    ...
    ... [primed_python]
    ... executable = %(py_path)s
    ...
    ... [eggs]
    ... recipe = z3c.recipe.scripts
    ... include-site-packages = true
    ... allowed-eggs-from-site-packages = *
    ... python = primed_python
    ... eggs = demoneeded
    ... ''' % globals())

    >>> print system(buildout)
    Installing eggs.
    <BLANKLINE>

Specifying the egg exactly will work as well.  This shows we correctly
parse a multi-line value.

    >>> zc.buildout.easy_install.clear_index_cache()
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links =
    ...
    ... [primed_python]
    ... executable = %(py_path)s
    ...
    ... [eggs]
    ... recipe = z3c.recipe.scripts
    ... include-site-packages = true
    ... allowed-eggs-from-site-packages = other
    ...                                   demoneeded
    ... python = primed_python
    ... eggs = demoneeded
    ... ''' % globals())

    >>> print system(buildout)
    Uninstalling eggs.
    Installing eggs.
    <BLANKLINE>

It will also work if we use a glob ("*" or "?").  (We won't show that here
because we already tested it in
zc.buildout.tests.allowed_eggs_from_site_packages.)

However, if we do not include "demoneeded" in the
"allowed-eggs-from-site-packages" key, we get an error, because the
packages are not available in any links, and they are not allowed to
come from the executable's site packages. (We won't show that here
because we already tested it in the same test mentioned above.)

    """

def setUp(test):
    zc.buildout.tests.easy_install_SetUp(test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)
    zc.buildout.testing.install_develop('z3c.recipe.scripts', test)

def setUpSelecting(test):
    zc.buildout.testselectingpython.setup(test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)
    zc.buildout.testing.install_develop('z3c.recipe.scripts', test)

def test_suite():
    suite = unittest.TestSuite((
        doctest.DocTestSuite(
            setUp=setUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_egg_py,
                zc.buildout.tests.hide_distribute_additions,
                zc.buildout.tests.hide_first_index_page_message,
                (re.compile(r'[a-zA-Z]:\\\\foo\\\\bar'), '/foo/bar'),
                ]),
            ),
        ))

    if zc.buildout.testing.script_in_shebang:
        suite.addTest(
            doctest.DocFileSuite(
                'README.txt',
                setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
                checker=renormalizing.RENormalizing([
                    zc.buildout.testing.normalize_path,
                    zc.buildout.testing.normalize_endings,
                    zc.buildout.testing.normalize_script,
                    zc.buildout.testing.normalize_egg_py,
                    zc.buildout.tests.normalize_bang,
                    zc.buildout.tests.hide_distribute_additions,
                    zc.buildout.tests.hide_first_index_page_message,
                    (re.compile(r'zc.buildout(-\S+)?[.]egg(-link)?'),
                     'zc.buildout.egg'),
                    (re.compile('[-d]  (setuptools|distribute)-[^-]+-'),
                     'setuptools-X-'),
                    (re.compile(r'(setuptools|distribute)-[\w.]+-py'),
                     'setuptools-X-py'),
                    (re.compile(r'eggs\\\\demo'), 'eggs/demo'),
                    (re.compile(r'[a-zA-Z]:\\\\foo\\\\bar'), '/foo/bar'),
                    (re.compile(r'\#!\S+\bpython\S*'), '#!/usr/bin/python'),
                    # Normalize generate_script's Windows interpreter to UNIX:
                    (re.compile(r'\nimport subprocess\n'), '\n'),
                    (re.compile('subprocess\\.call\\(argv, env=environ\\)'),
                     'os.execve(sys.executable, argv, environ)'),
                    (re.compile('distribute'), 'setuptools'),
                    ])
                ))

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

