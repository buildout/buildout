# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2020 Zope Foundation and Contributors.
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
import re
import os
import sys
import shutil
import tempfile
import zc.buildout


def create_sample_eggs(test, executable=sys.executable):
    assert executable == sys.executable, (executable, sys.executable)
    write = test.globs['write']
    dest = test.globs['sample_eggs']
    tmp = tempfile.mkdtemp()
    try:
        write(tmp, 'README.txt', '')

        for i in (0, 1, 2):
            write(tmp, 'eggrecipedemoneeded.py', 'y=%s\ndef f():\n  pass' % i)
            rc1 = 'rc1' if i==2 else ''
            write(
                tmp, 'setup.py',
                "from setuptools import setup\n"
                "setup(name='demoneeded', py_modules=['eggrecipedemoneeded'],"
                " zip_safe=True, version='1.%s%s', author='bob', url='bob', "
                "author_email='bob')\n"
                % (i, rc1)
                )
            zc.buildout.testing.sdist(tmp, dest)

        write(
            tmp, 'distutilsscript',
            '#!/usr/bin/python\n'
            '# -*- coding: utf-8 -*-\n'
            '"""Module docstring."""\n'
            'from __future__ import print_statement\n'
            'import os\n'
            'import sys; sys.stdout.write("distutils!\\n")\n'
            )
        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='other', zip_safe=False, version='1.0', "
            "scripts=['distutilsscript'],"
            "py_modules=['eggrecipedemoneeded'])\n"
            )
        zc.buildout.testing.bdist_egg(tmp, sys.executable, dest)

        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='du_zipped', zip_safe=True, version='1.0', "
            "scripts=['distutilsscript'],"
            "py_modules=['eggrecipedemoneeded'])\n"
            )
        zc.buildout.testing.bdist_egg(tmp, executable, dest)

        os.remove(os.path.join(tmp, 'distutilsscript'))
        os.remove(os.path.join(tmp, 'eggrecipedemoneeded.py'))

        for i in (1, 2, 3, 4):
            write(
                tmp, 'eggrecipedemo.py',
                'import eggrecipedemoneeded, sys\n'
                'def print_(*a):\n'
                '    sys.stdout.write(" ".join(map(str, a))+"\\n")\n'
                'x=%s\n'
                'def main():\n'
                '   print_(x, eggrecipedemoneeded.y)\n'
                % i)
            rc1 = 'rc1' if i==4 else ''
            write(
                tmp, 'setup.py',
                "from setuptools import setup\n"
                "setup(name='demo', py_modules=['eggrecipedemo'],"
                " install_requires = 'demoneeded',"
                " entry_points={'console_scripts': "
                     "['demo = eggrecipedemo:main']},"
                " zip_safe=True, version='0.%s%s')\n" % (i, rc1)
                )
            zc.buildout.testing.bdist_egg(tmp, dest)

        write(tmp, 'mixedcase.py', 'def f():\n  pass')
        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='MIXEDCASE', py_modules=['mixedcase'],"
            " author='bob', url='bob', author_email='bob',"
            " install_requires = 'demoneeded',"
            " zip_safe=True, version='0.5')\n"
            )
        zc.buildout.testing.sdist(tmp, dest)
        # rename file to lower case
        # to test issues between file and package name
        curdir = os.getcwd()
        os.chdir(dest)
        for file in os.listdir(dest):
            if "MIXEDCASE" in file:
                os.rename(file, file.lower())
        os.chdir(curdir)

        write(tmp, 'eggrecipebigdemo.py', 'import eggrecipedemo')
        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='bigdemo', "
            " install_requires = 'demo',"
            " py_modules=['eggrecipebigdemo'], "
            " zip_safe=True, version='0.1')\n"
            )
        zc.buildout.testing.bdist_egg(tmp, sys.executable, dest)

    finally:
        shutil.rmtree(tmp)


extdemo_c2 = """
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

extdemo_c3 = """
#include <Python.h>
#include <extdemo.h>

static PyMethodDef methods[] = {{NULL}};

#define MOD_DEF(ob, name, doc, methods) \
	  static struct PyModuleDef moduledef = { \
	    PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
	  ob = PyModule_Create(&moduledef);

#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)

MOD_INIT(extdemo)
{
    PyObject *m;

    MOD_DEF(m, "extdemo", "", methods);

#ifdef TWO
    PyModule_AddObject(m, "val", PyLong_FromLong(2));
#else
    PyModule_AddObject(m, "val", PyLong_FromLong(EXTDEMO));
#endif

    return m;
}
"""

extdemo_c = extdemo_c2 if sys.version_info[0] < 3 else extdemo_c3

extdemo_setup_py = r"""
import os, sys
from distutils.core import setup, Extension

if os.environ.get('test_environment_variable'):
    print(
        "Have environment test_environment_variable: %%s"
        %% os.environ['test_environment_variable']
    )

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
    zc.buildout.testing.install_develop('zc.recipe.egg', test)


normalize_bang = (
    re.compile(re.escape('#!'+
                         zc.buildout.easy_install._safe_arg(sys.executable))),
    '#!/usr/local/bin/python2.7',
    )


def create_egg(name, version, dest, install_requires=None,
               dependency_links=None):
    d = tempfile.mkdtemp()
    if dest=='available':
        extras = dict(x=['x'])
    else:
        extras = {}
    if dependency_links:
        links = 'dependency_links = %s, ' % dependency_links
    else:
        links = ''
    if install_requires:
        requires = 'install_requires = %s, ' % install_requires
    else:
        requires = ''
    try:
        with open(os.path.join(d, 'setup.py'), 'w') as f:
            f.write(
                'from setuptools import setup\n'
                'setup(name=%r, version=%r, extras_require=%r, zip_safe=True,\n'
                '      %s %s py_modules=["setup"]\n)'
                % (name, str(version), extras, requires, links)
            )
        zc.buildout.testing.bdist_egg(d, sys.executable, os.path.abspath(dest))
    finally:
        shutil.rmtree(d)
