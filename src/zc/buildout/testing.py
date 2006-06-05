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

def dirname(path, n=1):
    if n <= 0:
        return path
    return dirname(os.path.dirname(path), n-1)

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
