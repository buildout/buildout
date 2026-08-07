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
"""Buildout package
"""
# do not change the import order
# deleting the spec_for_pip hack needs to be done before importing pip
# see https://github.com/pypa/pip/issues/8761 to understand
# the reason for the hack.
# I think it is reasonable to assume we will not run into the race.
import setuptools

try:
    from _distutils_hack import DistutilsMetaFinder
    if hasattr(DistutilsMetaFinder, 'spec_for_pip'):
        del DistutilsMetaFinder.spec_for_pip
except ImportError:
    pass

import pip  # NOQA

import sys

# zc.buildout ships its own copy of pkg_resources, taken from setuptools
# 81.0.0 (the last release that contained it).  Make it importable as
# plain `pkg_resources` for buildout's own code and for recipes and
# extensions running inside the buildout process.  If some other code
# already imported pkg_resources before us (only possible with
# setuptools < 82), keep using that copy to preserve module identity
# (isinstance checks etc.).
# See src/zc/buildout/_vendor/README.rst and
# https://github.com/buildout/buildout/issues/685
if 'pkg_resources' not in sys.modules:
    from zc.buildout._vendor import pkg_resources as _vendored_pkg_resources
    sys.modules['pkg_resources'] = _vendored_pkg_resources

import warnings
from pkg_resources import PkgResourcesDeprecationWarning
warnings.filterwarnings('ignore', category=PkgResourcesDeprecationWarning)
warnings.filterwarnings('ignore', message='Setuptools is replacing distutils.')

import zc.buildout.patches  # NOQA


WINDOWS = sys.platform.startswith('win')


class UserError(Exception):
    """Errors made by a user
    """

    def __str__(self):
        return " ".join(map(str, self.args))
