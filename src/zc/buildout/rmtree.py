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


import shutil
import os
import doctest
import time

def rmtree (path):
    """
    A variant of shutil.rmtree which tries hard to be successful.
    On windows shutil.rmtree aborts when it tries to delete a
    read only file or a file which is still handled by another
    process (e.g. antivirus scanner). This tries to chmod the
    file to writeable and retries 10 times before giving up.

    >>> from tempfile import mkdtemp

    Let's make a directory ...

    >>> d = mkdtemp()

    and make sure it is actually there

    >>> os.path.isdir (d)
    1

    Now create a file ...

    >>> foo = os.path.join (d, 'foo')
    >>> with open (foo, 'w') as f: _ = f.write ('huhu')

    and make it unwriteable

    >>> os.chmod (foo, 256) # 0400

    rmtree should be able to remove it:

    >>> rmtree (d)

    and now the directory is gone

    >>> os.path.isdir (d)
    0
    """
    def retry_writeable (func, path, exc):
        os.chmod (path, 384) # 0600
        for i in range(10):
            try:
                func (path)
                break
            except OSError:
                time.sleep(0.1)
        else:
            # tried 10 times without success, thus
            # finally rethrow the last exception
            raise

    shutil.rmtree (path, onerror = retry_writeable)

def test_suite():
    return doctest.DocTestSuite()

if "__main__" == __name__:
    doctest.testmod()
