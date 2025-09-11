Change History
**************

.. You should *NOT* be adding new change log entries to this file.
   You should create a file in the news directory instead.
   For helpful instructions, please see:
   https://github.com/buildout/buildout/blob/master/doc/ADD-A-NEWS-ITEM.rst

.. towncrier release notes start

5.0.0a1 (2025-09-11)
--------------------

Breaking changes:


- Install development eggs (editable installs) using pip.
  Theoretically this means that you could develop a package that uses for example ``hatchling`` as build system.
  In practice this does not work yet, but the foundation is there.
  [maurits] (#676)
- Install all namespace packages as native namespaces.  [maurits] (#676)
- Store eggs in a sub directory: ``eggs/v5``.
  Or with abi tags for example: ``eggs/v5/cp313``.
  [maurits] (#676)
- Install most packages with pip, with only rare exceptions.  [maurits] (#676)
- The ``zc.buildout`` package itself uses native namespaces now.  [maurits] (#676)
- Require at least ``setuptools`` version 61.0.0.
  This is needed due to the changes in the test setup.
  [maurits]


Tests:


- The tests have mostly been changed to use wheels instead of eggs, so they more closely resemble real life.  [maurits] (#676)
- Removed inactive tests for no longer existing ``bootstrap.py``.
  [maurits]
- Split the ``buildout.txt`` test file into multiple files.
  [maurits]


4.1.12 (2025-06-11)
-------------------

Bug fixes:


- Fix error ``get_win_launcher`` not found on Windows on setuptools 80.3+.
  [maurits] (#713)


4.1.11 (2025-06-11)
-------------------

Bug fixes:


- Fix development installs to still work when using setuptools 80.0.0.
  From then on, setuptools internally calls ``pip install --editable``.
  Note that "distutils scripts" can no longer be detected with setuptools 80.
  This seems an ancient technology, and probably hardly used.
  [maurits] (#708)
- Use a copy of ``package_index.py`` from ``setuptools`` 80.2.0.
  This fixes compatibility with ``setuptools`` 80.3.0 where this module was removed.
  Merged some of our patches into this copy.
  [maurits] (#710)


4.1.10 (2025-05-21)
-------------------

Bug fixes:


- Override `pkg_resources.Environment.can_add` to have better results on Mac.
  Without this, a freshly created Mac-specific egg may not be considered compatible.
  This can happen when the Python you use was built on a different Mac OSX version.
  [maurits] (#609)


4.1.9 (2025-04-09)
------------------

Bug fixes:


- Fix accidental changes to ``PYTHONPATH`` in ``os.environ`` when calling ``pip install``.
  [xavth] (#639)


Tests


- Use ``wheel`` 0.45.1 when testing with ``setuptools`` older than 70.1.0.
  Otherwise, when combining an older ``setuptools`` with a newer ``wheel`` version, the ``bdist_wheel`` command exists in neither of these packages.
  [maurits] (#705)


4.1.8 (2025-04-09)
------------------

Bug fixes:


- Use the canonical name of a package when checking for a version constraint.
  [maurits] (#689)
- Get actual project name from dist.
  Use this for naming the egg that gets created after installing a wheel or after doing a pip install of a source dist.
  [maurits] (#695)
- Log all http errors when processing package url.
  [maurits] (#1013)


4.1.7 (2025-04-08)
------------------

Bug fixes:


- Prevent getting package pages twice.
  Since version 4.1.5 we first request normalized package url on PyPI servers, but a subsequent check needed a fix.
  [maurits] (#634)
- No longer recompile py files if we moved the dist.
  This code was never updated for Python 3, where the `.pyc` files are in a `__pycache__` directory, so it had no effect.
  [maurits] (#699)
- Require at least `packaging` version 23.2.
  Needed because we use the `utils.is_normalized_name` function.
  [maurits] (#700)


4.1.6 (2025-04-03)
------------------

Tests


- While creating sample packages for testing, mostly create wheels instead of eggs.
  For the sample source distributions, create ``tar.gz`` instead of ``zip`` files.
  Then our package index for testing is more like the actual PyPI.
  [maurits] (#675)


4.1.5 (2025-03-31)
------------------

Bug fixes:


- Implement PEP 503: request normalized package url on PyPI servers.
  [andreclimaco] (#634)
- Install ``wheel`` before ``setuptools`` when checking if an upgrade and restart are needed.
  [maurits] (#691)


4.1.4 (2025-03-07)
------------------

Bug fixes:


- If needed, copy and rename wheels before making an egg out of them.
  This helps for wheels of namespace packages created with ``setuptools`` 75.8.1 or higher.
  For namespace package we need a dot instead of an underscore in the resulting egg name.
  [maurits] (#686)


4.1.3 (2025-03-05)
------------------

Bug fixes:


- Patch the ``find`` method from ``pkg_resources.WorkingSet``.
  Let this use the code from ``setuptools`` 75.8.2, if the currently used version is older.
  This is better at finding installed distributions.
  But don't patch ``setuptools`` versions older than 61: the new version of the method would give an error there.
  [maurits] (#682)


4.1.2 (2025-03-05)
------------------

Bug fixes:


- Fix error finding the ``zc.buildout`` distribution when checking if we need to upgrade/restart.
  This depends on your ``setuptools`` version.
  [maurits] (#681)


4.1.1 (2025-03-04)
------------------

Bug fixes:


- Fix error adding minimum ``zc.buildout`` version as requirement.
  [maurits] (#679)


4.1 (2025-03-04)
----------------

New features:


- In the ``ls`` testing method, add keyword argument ``lowercase_and_sort_output``.
  The default is False, so no change.
  When true, as the name says, it sorts the output by lowercase, and prints it lowercase.
  We need this in one test because with ``setuptools`` 75.8.1 we no longer have a filename ``MIXEDCASE-0.5-pyN.N.egg``, but ``mixedcase-0.5-pyN.N.egg``.
  [maurits] (#7581)


Bug fixes:


- When trying to find a distribution for ``package.name``, first try the normalized name (``package_name``).
  This fixes an error finding entry points for namespace packages.
  The error is: ``TypeError: ('Expected str, Requirement, or Distribution', None)``.
  [maurits] (#7581)


Development:


- Test with latest ``setuptools`` 75.8.2 and with ``pip`` 25.0.1.
  Note that ``setuptools`` 75.8.1 can be troublesome and should be avoided.
  [maurits] (#7581)


4.0 (2025-01-30)
----------------

Breaking changes:


- Drop Python 3.8 support.  Require 3.9 as minimum. (#38)


Development:


- Test against `setuptools == 75.6.0`. (#671)


4.0.0a1 (2024-10-22)
--------------------

Breaking changes:


- Add dependency on ``packaging``.  This gets rid of ugly compatibility code.
  [maurits] (#38)
- Require ``setuptools >= 49.0.0``.
  This is the first version that supports PEP 496 environment markers, for example ``demo ==0.1; python_version < '3.9'``.
  An earlier change had ``setuptools >= 42.0.2``, otherwise we got ImportErrors.
  Also, since this is higher than 38.2.3, we are sure to have support for wheels.
  Remove support for ``distribute``, which was probably already broken.
  [maurits] (#38)
- Drop support for Python 2.  Require Python 3.8 as minimum.
  [maurits] (#38)


New features:


- Support Python 3.12 and 3.13.
  This only needed a few test fixes.
  [maurits] (#38)
