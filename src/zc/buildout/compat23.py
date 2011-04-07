#############################################################################
#
# Copyright (c) 2011 Zope Foundation and Contributors.
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
"""Compatibility functions for handling Python 2->3 runtime issues."""

import os
import subprocess
import sys
import tempfile

MUST_CLOSE_FDS = not sys.platform.startswith('win')


class Result(object):
    pass


def call_external_python(cmd, suite_source, env=None):
    """Quote a given code suite for consumption by `python -c '...'`
    and ensure print output encoding in UTF-8."""
    if isinstance(cmd, str):
        cmd = [cmd]
    code_file_path = tempfile.mktemp('.py')
    cmd.append(code_file_path)
    code_file = open(code_file_path, 'w')
    try:
        code_file.write(suite_source)
        code_file.write("""
import sys
import os
v = sys.version_info[0]
if v == 2:
    decode = True
elif v == 3 and isinstance(result, bytes):
    decode = True
else:
    decode = False
if decode:
    result = result.decode(sys.getfilesystemencoding())
os.write(1, result.encode('utf-8'))
""")
        code_file.close()
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=env,
                                   close_fds=MUST_CLOSE_FDS)
        out, err = process.communicate()
    finally:
        os.unlink(code_file_path)
    result = Result()
    result.out = out.decode('utf-8').strip()
    result.err = err
    result.returncode = process.returncode
    return result
