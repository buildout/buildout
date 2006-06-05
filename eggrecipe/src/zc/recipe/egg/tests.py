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

import os, re, shutil, sys, tempfile
import pkg_resources
import zc.buildout.testing

import unittest
from zope.testing import doctest, renormalizing

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

def setUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    open(os.path.join(test.globs['sample_buildout'],
                      'eggs', 'zc.recipe.egg.egg-link'),
         'w').write(dirname(__file__, 4))
                    
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
        
def tearDown(test):
    shutil.rmtree(test.globs['_sample_eggs_container'])
    zc.buildout.testing.buildoutTearDown(test)
    

def test_suite():
    return unittest.TestSuite((
        #doctest.DocTestSuite(),
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=tearDown,
            checker=renormalizing.RENormalizing([
               (re.compile('\S+[/%(sep)s]'
                           '(\\w+-)[^ \t\n%(sep)s/]+.egg'
                           % dict(sep=os.path.sep)
                           ),
                '\\1-VVV-egg')
               ])
            ),
        
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

