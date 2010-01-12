##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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

import unittest
from zope.testing import doctest, renormalizing

os_path_sep = os.path.sep
if os_path_sep == '\\':
    os_path_sep *= 2

def dirname(d, level=1):
    if level == 0:
        return d
    return dirname(os.path.dirname(d), level-1)

# We do not explicitly test the interpreter recipe support for the ``eggs``,
# ``find-links``, and ``index`` options because they are used for most or
# all of the examples.  The README tests ``extends``,
# ``include-site-customization`` and ``name``.  That leaves ``python``,
# ``extra-paths``, ``initialization``, ``relative-paths``, and
# ``include-site-packages``.

def interpreter_recipe_supports_python_option():
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
    ... recipe = zc.recipe.egg:interpreter
    ... include-site-customization = true
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

def interpreter_recipe_supports_extra_paths_option():
    """
This shows that specifying extra-paths will affect sys.path.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = py
    ...
    ... [py]
    ... recipe = zc.recipe.egg:interpreter
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... extra-paths =
    ...    /foo/bar
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
    ... recipe = zc.recipe.egg:interpreter
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

This also works with the include-site-customization option, processing local
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
    ... recipe = zc.recipe.egg:interpreter
    ... initialization =
    ...     import os
    ...     os.environ['zc.recipe.egg'] = 'baLOOba'
    ... include-site-customization = true
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
    ... # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
    import os
    os.environ['zc.recipe.egg'] = 'baLOOba'
    execfile('/executable_buildout/parts/py/sitecustomize.py')

    >>> print system(join(sample_buildout, 'bin', 'py') + ' -c ' +
    ...              '''"import os; print os.environ['zc.recipe.egg']"'''),
    baLOOba
    >>> print system(join(sample_buildout, 'bin', 'py') +
    ...              ''' -c "import os; print os.environ['zc.buildout']"'''),
    foo bar baz shazam

"""

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
    ... recipe = zc.recipe.egg:interpreter
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... relative-paths = true
    ... extra-paths =
    ...    /foo/bar
    ...    ${buildout:directory}/spam
    ... ''' % dict(server=link_server))

    >>> print system(buildout),
    Installing py.
    Generated interpreter '/sample-buildout/bin/py'.

Let's look at the site.py that was generated:

    >>> cat(sample_buildout, 'parts', 'py', 'site.py')
    ... # doctest: +NORMALIZE_WHITESPACE
    <BLANKLINE>
    import os
    <BLANKLINE>
    join = os.path.join
    base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    base = os.path.dirname(base)
    base = os.path.dirname(base)
    import sys
    sys.path[0:0] = [
      '/foo/bar',
      join(base, 'spam'),
      ]
    import sitecustomize

"""

def interpreter_recipe_supports_include_site_packages_option():
    """
This option simply causes the executable's usual site.py to be processed.
We'll demonstrate this by using a Python that has its own extra path.

    >>> py_path, site_packages_path = make_py()

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = py
    ... executable = %(py_path)s
    ...
    ... [py]
    ... recipe = zc.recipe.egg:interpreter
    ... include-site-packages = true
    ... eggs = demo<0.3
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... ''' % dict(server=link_server, py_path=py_path))

    >>> print system(buildout),
    Installing py.
    Getting distribution for 'demo<0.3'.
    Got demo 0.2.
    Getting distribution for 'demoneeded'.
    Got demoneeded 1.2c1.
    Generated interpreter '/sample-buildout/bin/py'.

    >>> print system(join(sample_buildout, 'bin', 'py') +
    ...              ''' -c "import sys; print (%r in sys.path) or (%r, sys.path)"''' %
    ...              (site_packages_path, site_packages_path)),
    True
"""

def setUp(test):
    zc.buildout.tests.easy_install_SetUp(test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)

def setUpSelecting(test):
    zc.buildout.testselectingpython.setup(test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)

def test_suite():
    suite = unittest.TestSuite((
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.tests.normalize_bang,
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('[-d]  setuptools-[^-]+-'), 'setuptools-X-'),
               (re.compile(r'eggs\\\\demo'), 'eggs/demo'),
               (re.compile(r'[a-zA-Z]:\\\\foo\\\\bar'), '/foo/bar'),
               ])
            ),
        doctest.DocFileSuite(
            'api.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               (re.compile('__buildout_signature__ = '
                           'sample-\S+\s+'
                           'zc.recipe.egg-\S+\s+'
                           'setuptools-\S+\s+'
                           'zc.buildout-\S+\s*'
                           ),
                '__buildout_signature__ = sample- zc.recipe.egg-\n'),
               (re.compile('executable = [\S ]+python\S*', re.I),
                'executable = python'),
               (re.compile('find-links = http://localhost:\d+/'),
                'find-links = http://localhost:8080/'),
               (re.compile('index = http://localhost:\d+/index'),
                'index = http://localhost:8080/index'),
               ])
            ),
        doctest.DocFileSuite(
            'custom.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               (re.compile("(d  ((ext)?demo(needed)?|other)"
                           "-\d[.]\d-py)\d[.]\d(-\S+)?[.]egg"),
                '\\1V.V.egg'),
               (re.compile('extdemo.c\n.+\\extdemo.exp\n'), ''),
               (re.compile('extdemo[.]pyd'), 'extdemo.so')
               ]),
            ),
        doctest.DocTestSuite(
            setUp=setUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_egg_py,
                ]),
            ),

        ))

    if sys.version_info[:2] == (2, 5):
        # Only run selecting python tests if not 2.4, since
        # 2.4 is the alternate python used in the tests.
        suite.addTest(
            doctest.DocFileSuite(
                'selecting-python.txt',
                setUp=setUpSelecting,
                tearDown=zc.buildout.testing.buildoutTearDown,
                checker=renormalizing.RENormalizing([
                   zc.buildout.testing.normalize_path,
                   zc.buildout.testing.normalize_endings,
                   zc.buildout.testing.normalize_script,
                   (re.compile('Got setuptools \S+'), 'Got setuptools V'),
                   (re.compile('([d-]  )?setuptools-\S+-py'),
                    'setuptools-V-py'),
                   (re.compile('-py2[.][0-35-9][.]'), 'py2.5.'),
                   (re.compile('zc.buildout-\S+[.]egg'),
                    'zc.buildout.egg'),
                   (re.compile('zc.buildout[.]egg-link'),
                    'zc.buildout.egg'),
                   ]),
                ),
            )

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

