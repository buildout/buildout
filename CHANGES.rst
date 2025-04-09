Change History
**************

.. You should *NOT* be adding new change log entries to this file.
   You should create a file in the news directory instead.
   For helpful instructions, please see:
   https://github.com/buildout/buildout/blob/master/doc/ADD-A-NEWS-ITEM.rst

.. towncrier release notes start

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


3.3 (2024-10-17)
----------------

New features:

- Allow the ``-I`` option in the Python interpreter wrapper installed by
  buildout when using the ``zc.recipe.egg`` recipe's `interpreter =` directive.
  This solves the issue when VSCode calls the designated Python interpreter for
  a workspace with this option to determine the Python version etc.
  (`#627 <https://github.com/buildout/buildout/issues/627>`_)


3.2.0 (2024-09-26)
------------------

New features:

- Add config option: ``optional-extends``. This is the same as the ``extends``
  option, but then for optional files. The names must be file paths, not URLs.
  If the path does not exist,  it is silently ignored. This is useful for
  optionally loading a ``local.cfg`` or ``custom.cfg`` with options specific
  for the developer or the server.
  [maurits] (`#665 <https://github.com/buildout/buildout/issues/665>`_)


3.1.1 (2024-09-20)
------------------

Bug fixes:

- Fix: a variable defined with initial ``+=`` was undefined and would lead to a
  corrupted ``.installed.cfg``.
  Fixes `issue 641 <https://github.com/buildout/buildout/issues/641>`_.
  [distributist]
- Fix: extends with increments could result in missing values.
  Buildout processes them in the correct order now and combines them correctly.
  Fixes `issue 176 <https://github.com/buildout/buildout/issues/176>`_ and
  `issue 629 <https://github.com/buildout/buildout/issues/629>`_.
  [distributist] (#644)
- Fix: Multiple ``+=`` or ``/-=`` in one file would lose assignment in a
  previous file.
  Fixes `issue 656 <https://github.com/buildout/buildout/issues/656>`_.
  [distributist]


3.1.0 (2024-08-29)
------------------

Breaking changes:


- Drop support for Python 3.5.  It is unsupported, and testing it is too hard.
  [maurits] (#35)


Bug fixes:


- Normalize package names when gathering packages.
  This should help find all distributions for package ``name.space``, whether
  they are called ``name.space-1.0.tar.gz`` with a dot or
  ``name_space-1.0.tar.gz`` with an underscore (created with ``setuptools``
  69.3 or higher).
  [maurits] (#647)
- Fix ImportError: cannot import name ``packaging`` from ``pkg_resources`` with
  setuptools 70.
  Done by adding a compatibility module that tries to import `packaging` from
  several places.
  Fixes `issue 648 <https://github.com/buildout/buildout/issues/648>`_.
  [maurits] (#648)


3.0.1 (2022-11-08)
------------------

Bug fixes:


- Fixed import of packaging.markers.  [maurits] (#621)


3.0.0 (2022-11-07)
------------------

New features:


- Add support for PEP 508 markers in section condition expressions.
  For example: ``[versions:python_version <= "3.9"]``.
  [maurits] (#621)


Bug fixes:


- Command-line 'extends' now works with dirs in file names
  [gotcha] (cli-extends)
- Add support for python311-315 in conditional section expressions. (#311)
- Make compatible with pip 22.2+, restoring Requires-Python functionality there.
  Fixes `issue 613 <https://github.com/buildout/buildout/issues/613>`_.
  [maurits] (#613)


3.0.0rc3 (2022-04-07)
---------------------

Bug fixes:


- Fix `TypeError: dist must be a Distribution instance` due to issue between
  `setuptools` and `pip`. (#600)


3.0.0rc2 (2022-03-04)
---------------------

New features:


- add support for PEP496 environment markers (pep496)


Bug fixes:


- Fix TypeError for missing required `use_deprecated_html5lib` with pip 22.
  Keep compatible with earlier pip versions. (#598)


3.0.0rc1 (2021-12-16)
---------------------

Bug fixes:


- Call pip via `python -m pip`. (#569)


3.0.0b5 (2021-11-29)
--------------------

Bug fixes:


- Fix when c extension implements namespace packages without the corresponding
  directories. (#589)
- Honor command-line buildout:extends (#592)


3.0.0b4 (2021-11-25)
--------------------

New features:


- Allow to run buildout in FIPS enabled environments. (#570)
- Proper error message if extends-cache tries to expand ${section:variable} (#585)


Bug fixes:


- Forward verbose option to pip (#576)
- Check that file top_level.txt exists before opening.
  Add check for other files as well. (#582)
- Return code of pip install subprocess is now properly returned to buildout. (#586)


3.0.0b3 (2021-10-08)
--------------------

New features:


- Improve warning message when a section contains unused options. (#483)


Bug fixes:


- Fix support of ``pip>=21.1`` (#567)
- Fix confusion when using multiple Python versions and
  installing packages with C extensions
  without proper binary wheel available. (#574)


Development:


- Avoid broken jobs on Travis because of security on PRs (travis-pr)


3.0.0b2 (2021-03-09)
--------------------

New features:


- Improve error message when a package version is not pinned and `allow-picked-versions = false`. (#481)


Bug fixes:


- Fix FileNotFoundError when installing eggs with top-level directory without code (like doc). (#556)


Development:


- Login to docker hub to avoid pull limits (travis)
- Initialize towncrier (#519)


3.0.0b1 (2021-03-07)
====================

- Fix issue with combination of `>` specs and `extras` and recent `setuptools`.

- Fix issue with incrementing options from `.buildout/default.cfg`.

- Support python37, python38 and python39 in conditional section expressions.

- Fix bootstrapping for python27 and python35.


3.0.0a2 (2020-05-25)
====================

- Ignore `.git` when computing signature of a recipe develop egg

- Warn when the name passed to `zc.recipe.egg:scripts`
  is not defined in egg entry points.

- Show pip warning about Python version only once.

- Better patch for ``pkg_resources.Distribution.hashcmp`` performance.


3.0.0a1 (2020-05-17)
====================

- Scripts: ensure eggs are inserted before ``site-packages`` in ``sys.path``.

- Fix forever loop when changing ``zc.buildout`` version via ``buildout``.

- Add support for ``Requires-Python`` metadata.
  Fragile monkeypatch that relies on ``pip._internal``.
  Emits a warning when support is disabled due to changes in ``pip``.

- Use ``pip install`` instead of deprecated ``setuptools.easy_install``.

- Patch ``pkg_resources.Distribution`` to make install of unpinned versions quicker.
  Most obvious with ``setuptools``.


2.13.3 (2020-02-11)
===================

- Fix DeprecationWarning about MutableMapping.
  (`#484 <https://github.com/buildout/buildout/issues/484>`_)


2.13.2 (2019-07-03)
===================

- Fixed DeprecationWarning on python 3.7: "'U' mode is deprecated".


2.13.1 (2019-01-29)
===================

- Documentation update for the new ``buildout query`` command.


2.13.0 (2019-01-17)
===================

- Get information about the configuration with new command ``buildout query``.


2.12.2 (2018-09-04)
===================

- Upon an error, buildout exits with a non-zero exit code. This now also works
  when running with ``-D``.

- Fixed most 'Deprecation' and 'Resource' warnings.


2.12.1 (2018-07-02)
===================

- zc.buildout now explicitly requests zc.recipe.egg >=2.0.6 now.


2.12.0 (2018-07-02)
===================

- Add a new buildout option ``allow-unknown-extras`` to enable
  installing requirements that specify extras that do not exist. This
  needs a corresponding update to zc.recipe.egg. See `issue 457
  <https://github.com/buildout/buildout/issues/457>`_.

  zc.recipe.egg has been updated to 2.0.6 for this change.


2.11.5 (2018-06-19)
===================

- Fix for `issue 295 <https://github.com/buildout/buildout/issues/295>`_. On
  windows, deletion of temporary egg files is more robust now.


2.11.4 (2018-05-14)
===================

- Fix for `issue 451 <https://github.com/buildout/buildout/issues/451>`_:
  distributions with a version number that normalizes to a shorter version
  number (3.3.0 to 3.3, for instance) can be installed now.


2.11.3 (2018-04-13)
===================

- Update to use the new PyPI at https://pypi.org/.


2.11.2 (2018-03-19)
===================

- Fix for the #442 issue: AttributeError on
  ``pkg_resources.SetuptoolsVersion``.


2.11.1 (2018-03-01)
===================

- Made upgrade check more robust. When using extensions, the improvement
  introduced in 2.11 could prevent buildout from restarting itself when it
  upgraded setuptools.


2.11.0 (2018-01-21)
===================

- Installed packages are added to the working set immediately. This helps in
  some corner cases that occur when system packages have versions that
  conflict with our specified versions.


2.10.0 (2017-12-04)
===================

- Setuptools 38.2.0 started supporting wheels. Through setuptools, buildout
  now also supports wheels! You need at least version 38.2.3 to get proper
  namespace support.

  This setuptools change interfered with buildout's recent support for
  `buildout.wheel <https://github.com/buildout/buildout.wheel>`_, resulting in
  a sudden "Wheels are not supported" error message (see `issue 435
  <https://github.com/buildout/buildout/issues/425>`_). Fixed by making
  setuptools the default, though you can still use the buildout.wheel if you
  want.


2.9.6 (2017-12-01)
==================

- Fixed: could not install eggs when sdist file name and package name had different
  case.


2.9.5 (2017-09-22)
==================

- Use HTTPS for PyPI's index.  PyPI redirects HTTP to HTTPS by default
  now so using HTTPS directly avoids the potential for that redirect
  being modified in flight.


2.9.4 (2017-06-20)
==================

- Sort the distributions used to compute ``__buildout_signature__`` to
  ensure reproducibility under Python 3 or under Python 2 when ``-R``
  is used on ``PYTHONHASHSEED`` is set to ``random``. Fixes `issue 392
  <https://github.com/buildout/buildout/issues/392>`_.

  **NOTE**: This may cause existing ``.installed.cfg`` to be
  considered outdated and lead to parts being reinstalled spuriously
  under Python 2.

- Add support code for doctests to be able to easily measure code
  coverage. See `issue 397 <https://github.com/buildout/buildout/issues/397>`_.

2.9.3 (2017-03-30)
==================

- Add more verbosity to ``annotate`` results with ``-v``

- Select one or more sections with arguments after ``buildout annotate``.


2.9.2 (2017-03-06)
==================

- Fixed: We unnecessarily used a function from newer versions of
  setuptools that caused problems when older setuptools or pkg_resources
  installs were present (as in travis.ci).


2.9.1 (2017-03-06)
==================

- Fixed a minor packaging bug that broke the PyPI page.


2.9.0 (2017-03-06)
==================

- Added new syntax to explicitly declare that a part depends on other part.
  See http://docs.buildout.org/en/latest/topics/implicit-parts.html

- Internal refactoring to work with `buildout.wheel
  <https://github.com/buildout/buildout.wheel>`_.

- Fixed a bugs in ``zc.buildout.testing.Buildout``. It was loading
  user-default configuration.  It didn't support calling the
  ``created`` method on its sections.

- Fixed a bug (windows, py 3.4)
  When processing metadata on "old-style" distutils scripts, .exe stubs
  appeared in ``metadata_listdir``, in turn reading those burped with
  ``UnicodeDecodeError``. Skipping .exe stubs now.


2.8.0 (2017-02-13)
==================

- Added a hook to enable a soon-to-be-released buildout extension to
  provide wheel support.

2.7.1 (2017-01-31)
==================

- Fixed a bug introduced in 2.6.0:
  zc.buildout and its dependeoncies were reported as picked even when
  their versions were fixed in a ``versions`` section.  Worse, when the
  ``update-versions-file`` option was used, the ``versions`` section was
  updated needlessly on every run.


2.7.0 (2017-01-30)
==================

- Added a buildout option, ``abi-tag-eggs`` that, when true, causes
  the `ABI tag <https://www.python.org/dev/peps/pep-0425/#abi-tag>`_
  for the buildout environment to be added to the eggs directory name.

  This is useful when switching Python implementations (e.g. CPython
  vs PyPI or debug builds vs regular builds), especially when
  environment differences aren't reflected in egg names.  It also has
  the side benefit of making eggs directories smaller, because eggs
  for different Python versions are in different directories.

2.6.0 (2017-01-29)
==================

- Updated to work with the latest setuptools.

- Added (verified) Python 3.6 support.

2.5.3 (2016-09-05)
==================

- After a dist is fetched and put into its final place, compile its
  python files.  No longer wait with compiling until all dists are in
  place.  This is related to the change below about not removing an
  existing egg.  [maurits]

- Do not remove an existing egg.  When installing an egg to a location
  that already exists, keep the current location (directory or file).
  This can only happen when the location at first did not exist and
  this changed during the buildout run.  We used to remove the
  previous location, but this could cause problems when running two
  buildouts at the same time, when they try to install the same new
  egg.  Fixes #307.  [maurits]

- In ``zc.buildout.testing.system``, set ``TERM=dumb`` in the environment.
  This avoids invisible control characters popping up in some terminals,
  like ``xterm``.  Note that this may affect tests by buildout recipes.
  [maurits]

- Removed Python 2.6 and 3.2 support.
  [do3cc]


2.5.2 (2016-06-07)
==================

- Fixed ``-=`` and ``+=`` when extending sections. See #161.
  [puittenbroek]


2.5.1 (2016-04-06)
==================

- Fix python 2 for downloading external config files with basic auth in the
  URL. Fixes #257.


2.5.0 (2015-11-16)
==================

- Added more elaborate version and requirement information when there's a
  version conflict. Previously, you could get a report of a version conflict
  without information about which dependency requested the conflicing
  requirement.

  Now all this information is logged and displayed in case of an error.
  [reinout]

- Dropped 3.2 support (at least in the automatic tests) as setuptools will
  soon stop supporting it. Added python 3.5 to the automatic tests.
  [reinout]


2.4.7 (2015-10-29)
==================

- Fix for #279. Distutils script detection previously broke on windows with
  python 3 because it errored on ``.exe`` files.
  [reinout]


2.4.6 (2015-10-28)
==================

- Relative paths are now also correctly generated for the current directory
  ("develop = .").
  [youngking]


2.4.5 (2015-10-14)
==================

- More complete fix for #24. Distutils scripts are now also generated for
  develop eggs.
  [reinout]


2.4.4 (2015-10-02)
==================

- zc.buildout is now also released as a wheel. (Note: buildout itself doesn't
  support installing wheels yet.)
  [graingert]


2.4.3 (2015-09-03)
==================

- Added nested directory creation support
  [guyzmo]


2.4.2 (2015-08-26)
==================

- If a downloaded config file in the "extends-cache" gets corrupted, buildout
  now tells you the filename in the cache. Handy for troubleshooting.
  [reinout]


2.4.1 (2015-08-08)
==================

- Check the ``use-dependency-links`` option earlier.  This can give
  a small speed increase.
  [maurits]

- When using python 2, urllib2 is used to work around Python issue 24599, which
  affects downloading from behind a proxy.
  [stefano-m]


2.4.0 (2015-07-01)
==================

- Buildout no longer breaks on packages that contain a file with a non-ascii
  filename. Fixes #89 and #148.
  [reinout]

- Undo breakage on Windows machines where ``sys.prefix`` can also be a
  ``site-packages`` directory:  don't remove it from ``sys.path``.  See
  https://github.com/buildout/buildout/issues/217 .

- Remove assumption that ``pkg_resources`` is a module (untrue since
  release of `setuptools 8.3``).  See
  https://github.com/buildout/buildout/issues/227 .

- Fix for #212. For certain kinds of conflict errors you'd get an UnpackError
  when rendering the error message. Instead of a nicely formatted version
  conflict message.
  [reinout]

- Making sure we use the correct easy_install when setuptools is installed
  globally. See https://github.com/buildout/buildout/pull/232 and
  https://github.com/buildout/buildout/pull/222 .
  [lrowe]

- Updated buildout's `travis-ci <https://travis-ci.org/buildout/buildout>`_
  configuration so that tests run much quicker so that buildout is easier and
  quicker to develop.
  [reinout]

- Note: zc.recipe.egg has also been updated to 2.0.2 together with this
  zc.buildout release. Fixed: In ``zc.recipe.egg#custom`` recipe's ``rpath``
  support, don't assume path elements are buildout-relative if they start with
  one of the "special" tokens (e.g., ``$ORIGIN``).  See:
  https://github.com/buildout/buildout/issues/225.
  [tseaver]

- ``download-cache``, ``eggs-directory`` and ``extends-cache`` are now
  automatically created if their parent directory exists. Also they can be
  relative directories (relative to the location of the buildout config file
  that defines them). Also they can now be in the form ``~/subdir``, with the
  usual convention that the ``~`` char means the home directory of the user
  running buildout.
  [lelit]

- A new bootstrap.py file is released (version 2015-07-01).

- When bootstrapping, the ``develop-eggs/`` directory is first removed. This
  prevents old left-over ``.egg-link`` files from breaking buildout's careful
  package collection mechanism.
  [reinout]

- The bootstrap script now accepts ``--to-dir``. Setuptools is installed
  there. If already available there, it is reused. This can be used to
  bootstrap buildout without internet access. Similarly, a local
  ``ez_setup.py`` is used when available instead of it being downloaded. You
  need setuptools 14.0 or higher for this functionality.
  [lrowe]

- The bootstrap script now uses ``--buildout-version`` instead of
  ``--version`` to pick a specific buildout version.
  [reinout]

- The bootstrap script now accepts ``--version`` which prints the bootstrap
  version. This version is the date the bootstrap.py was last changed. A date
  is handier or less confusing than either tracking zc.buildout's version or
  having a separate bootstrap version number.
  [reinout]

2.3.1 (2014-12-16)
==================

- Fixed: Buildout merged single-version requirements with
  version-range requirements in a way that caused it to think there
  wasn't a single-version requirement.  IOW, buildout through that
  versions were being picked when they weren't.

- Suppress spurious (and possibly non-spurious) version-parsing warnings.

2.3.0 (2014-12-14)
==================

- Buildout is now compatible with (and requires) setuptools 8.

2.2.5 (2014-11-04)
==================

- Improved fix for #198: when bootstrapping with an extension, buildout was
  too strict on itself, resulting in an inability to upgrade or downgrade its
  own version.
  [reinout]

- Setuptools must be at 3.3 or higher now. If you use the latest bootstrap
  from http://downloads.buildout.org/2/bootstrap.py you're all set.
  [reinout]

- Installing *recipes* that themselves have dependencies used to fail with a
  VersionConflict if such a dependency was installed globally with a lower
  version. Buildout now ignores the version conflict in those cases and simply
  installs the correct version.
  [reinout]

2.2.4 (2014-11-01)
==================

- Fix for #198: buildout 2.2.3 caused a version conflict when bootstrapping a
  buildout with a version pinned to an earlier one. Same version conflict
  could occur with system-wide installed packages that were newer than the
  pinned version.
  [reinout]

2.2.3 (2014-10-30)
==================

- Fix #197, Python 3 regression
  [aclark4life]

2.2.2 (2014-10-30)
==================

- Open files for ``exec()`` in universal newlines mode.  See
  https://github.com/buildout/buildout/issues/130

- Add ``BUILDOUT_HOME`` as an alternate way to control how the user default
  configuration is found.

- Close various files when finished writing to them. This avoids
  ResourceWarnings on Python 3, and better supports doctests under PyPy.

- Introduce improved easy_install Install.install function. This is present
  in 1.5.X and 1.7X but was never merged into 2.X somehow.

2.2.1 (2013-09-05)
==================

- ``distutils`` scripts: correct order of operations on ``from ... import``
  lines (see https://github.com/buildout/buildout/issues/134).

- Add an ``--allow-site-packges`` option to ``bootstrap.py``, defaulting
  to False.  If the value is false, strip any "site packages" (as defined by
  the ``site`` module) from ``sys.path`` before attempting to import
  ``setuptools`` / ``pkg_resources``.

- Updated the URL used to fetch ``ez_setup.py`` to the official, non-version-
  pinned version.

2.2.0 (2013-07-05)
==================

- Handle both addition and subtraction of elements (+= and -=) on the same key
  in the same section. Forward-ported from buildout 1.6.

- Suppress the useless ``Link to <URL> ***BLOCKED*** by --allow-hosts``
  error message being emitted by distribute / setuptools.

- Extend distutils script generation to support module docstrings and
  __future__ imports.

- Refactored picked versions logic to make it easier to use for plugins.

- Use ``get_win_launcher`` API to find Windows launcher (falling back to
  ``resource_string`` for ``cli.exe``).

- Remove ``data_files`` from ``setup.py``:  it was installing ``README.txt``
  in current directory during installation (merged from 1.x branch).

- Switch dependency from ``distribute 0.6.x`` to ``setuptools 0.7.x``.

2.1.0 (2013-03-23)
==================

- Meta-recipe support

- Conditional sections

- Buildout now accepts a ``--version`` command-line option to print
  its version.

Fixed: Builout didn't exit with a non-zero exit status if there was a
       failure in combination with an upgrade.

Fixed: We now fail with an informative error when an old bootstrap
       script causes buildout 2 to be used with setuptools.

Fixed: An error incorrectly suggested that buildout 2 implemented all
       of the functionality of dumppickedversions.

Fixed: Buildout generated bad scripts when no eggs needed to be added
       to ``sys.path``.

Fixed: Buildout didn't honour Unix umask when generating scripts.
       https://bugs.launchpad.net/zc.buildout/+bug/180705

Fixed: ``update-versions-file`` didn't work unless
       ``show-picked-versions`` was also set.
       https://github.com/buildout/buildout/issues/71

2.0.1 (2013-02-16)
==================

- Fixed: buildout didn't honor umask settings when creating scripts.

- Fix for distutils scripts installation on Python 3, related to
  ``__pycache__`` directories.

- Fixed: encoding data in non-entry-point-based scripts was lost.
