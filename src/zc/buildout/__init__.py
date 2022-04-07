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

import warnings
from pkg_resources import PkgResourcesDeprecationWarning
warnings.filterwarnings('ignore', category=PkgResourcesDeprecationWarning)
warnings.filterwarnings('ignore', message='Setuptools is replacing distutils.')

import sys
import zc.buildout.patches  # NOQA


WINDOWS = sys.platform.startswith('win')
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


class UserError(Exception):
    """Errors made by a user
    """

    def __str__(self):
        return " ".join(map(str, self.args))
