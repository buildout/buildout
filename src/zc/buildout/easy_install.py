##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors.
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
"""Python easy_install API

This module provides a high-level Python API for installing packages.
It doesn't install scripts.  It uses setuptools and requires it to be
installed.

$Id$
"""

# XXX needs doctest

import setuptools.command.easy_install
import pkg_resources
import setuptools.package_index
import distutils.dist
import distutils.log

def install(spec, dest, links=(), **kw):
    index = setuptools.package_index.PackageIndex()
    index.add_find_links(links)
    easy = setuptools.command.easy_install.easy_install(
        distutils.dist.Distribution(),
        multi_version=True,
        exclude_scripts=True,
        sitepy_installed=True,
        install_dir=dest,
        outputs=[],
        verbose = 0,
        args = [spec],
        find_links = links,
        **kw
        )
    easy.finalize_options()

    old_warn = distutils.log.warn
    distutils.log.warn = lambda *a, **k: None

    easy.easy_install(spec, deps=True)

    distutils.log.warn = old_warn
    
