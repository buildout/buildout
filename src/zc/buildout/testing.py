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


def cat(dir, *names):
    path = os.path.join(dir, *names)
    print open(path).read(),

def ls(dir, *subs):
    if subs:
        dir = os.path.join(dir, *subs)
    names = os.listdir(dir)
    names.sort()
    for name in names:
        if os.path.isdir(os.path.join(dir, name)):
            print 'd ',
        else:
            print '- ',
        print name

def mkdir(dir, *subs):
    if subs:
        dir = os.path.join(dir, *subs)
    os.mkdir(dir)

def write(dir, *args):
    open(os.path.join(dir, *(args[:-1])), 'w').write(args[-1])

def system(command, input=''):
    i, o = os.popen4(command)
    if input:
        i.write(input)
    i.close()
    return o.read()

def buildoutSetUp(test):
    sample = tempfile.mkdtemp('buildout-tests')
    for name in ('bin', 'eggs', 'parts'):
        os.mkdir(os.path.join(sample, name))

    # make sure we can import zc.buildout and setuptools
    import zc.buildout, setuptools

    # Generate buildout script
    dest = os.path.join(sample, 'bin', 'buildout')
    open(dest, 'w').write(
        script_template % dict(python=sys.executable, path=sys.path)
        )
    try:
        os.chmod(dest, 0755)
    except (AttributeError, os.error):
        pass


    open(os.path.join(sample, 'buildout.cfg'), 'w').write(
        "[buildout]\nparts =\n"
        )
    open(os.path.join(sample, '.installed.cfg'), 'w').write(
        "[buildout]\nparts =\n"
        )

    test.globs.update(dict(
        __here = os.getcwd(),
        sample_buildout = sample,
        ls = ls,
        cat = cat,
        mkdir = mkdir,
        write = write,
        system = system,
        __original_wd__ = os.getcwd(),
        ))

def buildoutTearDown(test):
    shutil.rmtree(test.globs['sample_buildout'])
    os.chdir(test.globs['__original_wd__'])


script_template = '''\
#!%(python)s

import sys
sys.path[0:0] = %(path)r

from pkg_resources import load_entry_point
sys.exit(load_entry_point('zc.buildout', 'console_scripts', 'buildout')())
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

def create_sample_eggs(test):
    sample = tempfile.mkdtemp('eggtest')
    test.globs['_sample_eggs_container'] = sample
    test.globs['sample_eggs'] = os.path.join(sample, 'dist')
    write(sample, 'README.txt', '')
    write(sample, 'eggrecipedemobeeded.py', 'y=1\n')
    write(
        sample, 'setup.py',
        "from setuptools import setup\n"
        "setup(name='demoneeded', py_modules=['eggrecipedemobeeded'],"
        " zip_safe=True, version='1.0')\n"
        )
    runsetup(sample)
    os.remove(os.path.join(sample, 'eggrecipedemobeeded.py'))
    for i in (1, 2, 3):
        write(
            sample, 'eggrecipedemo.py',
            'import eggrecipedemobeeded\n'
            'x=%s\n'
            'def main(): print x, eggrecipedemobeeded.y\n'
            % i)
        write(
            sample, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='demo', py_modules=['eggrecipedemo'],"
            " install_requires = 'demoneeded',"
            " entry_points={'console_scripts': ['demo = eggrecipedemo:main']},"
            " zip_safe=True, version='0.%s')\n" % i
            )
        runsetup(sample)
