============================================================
Optimizing buildouts with shared eggs and download caches
============================================================

Most users should have this :ref:`user-default configuration
<user-default-configuration>` containing option settings that make
Buildout work better:

.. code-block:: ini

  [buildout]
  eggs-directory = ~/.buildout/eggs
  download-cache = ~/.buildout/download-cache
  abi-tag-eggs = true

.. -> src

    >>> import os
    >>> os.makedirs(join('home', '.buildout'))
    >>> write(src, 'home', '.buildout', 'default.cfg')
    >>> write("""\
    ... [buildout]
    ... parts = bobo
    ... [bobo]
    ... recipe=zc.recipe.egg
    ... eggs=bobo
    ... """, "buildout.cfg")
    >>> run_buildout()
    >>> eqs(ls(),
    ...     'out', 'home', '.installed.cfg', 'buildout.cfg',
    ...     'develop-eggs', 'parts', 'bin')
    >>> eqs(ls(join('home', '.buildout')),
    ...     'default.cfg', 'eggs', 'download-cache')
    >>> [abieggs] = ls(join('home', '.buildout', 'eggs'))
    >>> found_eggs = set([n.split('-', 1)[0]
    ...      for n in ls('home', '.buildout', 'eggs', abieggs)])

Some packages are only there on older Python versions or on newer.
Discard them.

    >>> found_eggs.discard("six")
    >>> found_eggs.discard("legacy_cgi")
    >>> eqs(found_eggs, 'bobo', 'WebOb')
    >>> clear_here()

You might be wondering why these settings aren't the default, if
they're recommended for everyone.  They probably *should* be the
default, and perhaps will be in version 3 of buildout.  Making them
the default now might break existing buildouts.

Shared eggs directory
=====================

You can save a lot of time and disk space by sharing eggs between
buildouts.  You can do this by setting the ``eggs-directory`` option,
as shown above. This will override the default value for this option
which puts eggs in the ``eggs`` buildout subdirectory.  By sharing
eggs, you can avoid reinstalling the same popular packages in each
and every buildout that uses them.

ABI tag eggs
------------

If you use a shared eggs directory, it's a good idea to set the
``abi-tag-eggs`` option to ``true``.  This causes eggs to be
segregated by `ABI tag
<https://www.python.org/dev/peps/pep-0425/#abi-tag>`_.  This has two
advantages:

1. If you alternate between Python implementations (PyPy versus C
   Python) or between build configurations (normal versus debug), ABI
   tagging eggs will avoid mixing incompatible eggs.

2. ABI tagging eggs makes Buildout run faster.  Because ABI tags
   include Python version information, eggs for different Python
   versions are kept separate, causing the shared eggs directory for a
   given Python version to be smaller, making it faster to search for
   installed eggs.

Download cache
--------------

When buildout installs distributions, it has to download them first.
Specifying a ``download-cache`` option in your :ref:`user-default
configuration <user-default-configuration>` causes the download to be
cached.  This can be helpful when multiple installations might be
performed for a source distribution.

Some recipes download information.  For example, a number of recipes
download non-Python source archives and user configure, and make to
install them.  Most of these recipes can leverage a download cache to
avoid downloading the same information over and over.
