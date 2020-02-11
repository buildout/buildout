Change History
**************

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

- A new boostrap.py file is released (version 2015-07-01).

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
  wasn't a single-version requirement.  IOW, buildout throught that
  versions were being picked when they weren't.

- Suppress spurios (and possibly non-spurious) version-parsing warnings.

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
