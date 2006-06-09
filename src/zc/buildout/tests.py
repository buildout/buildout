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

import os, re, shutil, sys, tempfile, unittest
from zope.testing import doctest, renormalizing
import pkg_resources
import zc.buildout.testing

def buildout_error_handling():
    r'''Buildout error handling

Asking for a section that doesn't exist, yields a key error:

    >>> import os
    >>> os.chdir(sample_buildout)
    >>> import zc.buildout.buildout
    >>> buildout = zc.buildout.buildout.Buildout()
    >>> buildout['eek']
    Traceback (most recent call last):
    ...
    KeyError: 'eek'

Asking for an option that doesn't exist, a MissingOption error is raised:

    >>> buildout['buildout']['eek']
    Traceback (most recent call last):
    ...
    MissingOption: ('Missing option', 'buildout', 'eek')

It is an error to create a variable-reference cycle:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y}
    ... y = ${buildout:z}
    ... z = ${buildout:x}
    ... """)

    >>> print system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: ('Circular references',
           [('buildout', 'y'), ('buildout', 'z'), ('buildout', 'x')],
           ('buildout', 'y'))

'''

    

def runsetup(d):
    here = os.getcwd()
    try:
        os.chdir(d)
        os.spawnle(
            os.P_WAIT, sys.executable, sys.executable,
            'setup.py', '-q', 'bdist_egg',
            {'PYTHONPATH': os.path.dirname(pkg_resources.__file__)},
            )
        shutil.rmtree('build')
    finally:
        os.chdir(here)

def dirname(d, level=1):
    if level == 0:
        return d
    return dirname(os.path.dirname(d), level-1)

def linkerSetUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    sample = tempfile.mkdtemp('eggtest')
    test.globs['_sample_eggs_container'] = sample
    test.globs['sample_eggs'] = os.path.join(sample, 'dist')
    zc.buildout.testing.write(sample, 'README.txt', '')
    zc.buildout.testing.write(sample, 'eggrecipedemobeeded.py', 'y=1\n')
    zc.buildout.testing.write(
        sample, 'setup.py',
        "from setuptools import setup\n"
        "setup(name='demoneeded', py_modules=['eggrecipedemobeeded'],"
        " zip_safe=True, version='1.0')\n"
        )
    runsetup(sample)
    os.remove(os.path.join(sample, 'eggrecipedemobeeded.py'))
    for i in (1, 2, 3):
        zc.buildout.testing.write(
            sample, 'eggrecipedemo.py',
            'import eggrecipedemobeeded\n'
            'x=%s\n'
            'def main(): print x, eggrecipedemobeeded.y\n'
            % i)
        zc.buildout.testing.write(
            sample, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='demo', py_modules=['eggrecipedemo'],"
            " install_requires = 'demoneeded',"
            " entry_points={'console_scripts': ['demo = eggrecipedemo:main']},"
            " zip_safe=True, version='0.%s')\n" % i
            )
        runsetup(sample)
        
def linkerTearDown(test):
    shutil.rmtree(test.globs['_sample_eggs_container'])
    zc.buildout.testing.buildoutTearDown(test)
    

def test_suite():
    return unittest.TestSuite((
        #doctest.DocTestSuite(),
        doctest.DocFileSuite(
            'buildout.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               ])
            ),
        doctest.DocFileSuite(
            'egglinker.txt',
            setUp=linkerSetUp, tearDown=linkerTearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('(\S+[/%(sep)s]| )'
                           '(\\w+-)[^ \t\n%(sep)s/]+.egg'
                           % dict(sep=os.path.sep)
                           ),
                '\\2-VVV-egg'),
               (re.compile('\S%spython(\d.\d)?' % os.path.sep), 'python')
               ]),
            ),
        doctest.DocTestSuite(
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

