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

import os, sys

def install(spec, dest, links, python=sys.executable):
    prefix = sys.exec_prefix + os.path.sep
    path = os.pathsep.join([p for p in sys.path if not p.startswith(prefix)])
    os.spawnle(
        os.P_WAIT, python, python,
        '-c', 'from setuptools.command.easy_install import main; main()',
        '-mqxd', dest, '-f', ' '.join(links), spec,
        dict(PYTHONPATH=path))
