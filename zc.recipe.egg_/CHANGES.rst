Change History
**************

4.0.0 (2025-11-12)
==================

- Require ``zc.buildout`` 5.0.0 or higher.


4.0.0a1 (2025-09-11)
====================

- Require ``zc.buildout`` 5.0.0a1 or higher.
- Switch from ``pkg_resources`` namespaces to native namespaces for ``zc.recipe.egg``.


3.0.0 (2025-04-03)
==================

- Drop support for Python 2.  Require Python 3.9 as minimum.
  Require ``zc.buildout`` 4.0.0 as minimum.

- Removed tests for the 'offline' mode of buildout, which were broken since setuptools 59.
  This option was deprecated long time ago, and its current working is not defined.
  See the `reference documentation <https://www.buildout.org/en/latest/reference.html>`_, which adds:
  "If you think you want an offline mode, you probably want either the non-newest mode or the install-from-cache mode instead."

- Removed tests for demoing usage of a custom egg, which were broken since setuptools 49.6.0.
  It is not clear what this means for how well custom egg creation currently works, but the remaining base tests still pass.
  This is when you are using ``recipe = zc.recipe.egg:custom`` or ``recipe = zc.recipe.egg:develop``, which should be rare.


2.0.7 (2018-07-02)
==================

- For the 2.0.6 change, we require zc.buildout 2.12.0. The `install_requires`
  in `setup.py` now also says that.


2.0.6 (2018-07-02)
==================

- Added extra keyword argument ``allow_unknown_extras`` to support zc.buildout
  2.12.0.


2.0.5 (2017-12-04)
==================

- Fixed #429: added sorting of working set by priority of different
  type of paths (develop-eggs-directory, eggs-directory, other paths).


2.0.4 (2017-08-17)
==================

- Fixed #153: buildout should cache working set environments
  [rafaelbco]


2.0.3 (2015-10-02)
==================

- Releasing zc.recipe.egg as a wheel in addition to only an sdist. No
  functional changes.
  [reinout]

2.0.2 (2015-07-01)
==================

- Fixed: In ``zc.recipe.egg#custom`` recipe's ``rpath`` support, don't
  assume path elements are buildout-relative if they start with one of the
  "special" tokens (e.g., ``$ORIGIN``).  See:
  https://github.com/buildout/buildout/issues/225.
  [tseaver]

2.0.1 (2013-09-05)
==================

- Accomodated ``zc.buildout`` switch to post-merge ``setuptools``.

2.0.0 (2013-04-02)
==================

- Enabled 'prefer-final' option by default.

2.0.0a3 (2012-11-19)
====================

- Added support for Python 3.2 / 3.3.

- Added 'MANIFEST.in'.

- Support non-entry-point-based scripts.

- Honor exit codes from scripts (https://bugs.launchpad.net/bugs/697913).

2.0.0a2 (2012-05-03)
====================

- Always unzip installed eggs.

- Switched from using 'setuptools' to 'distribute'.

- Removed multi-python support.

1.3.2 (2010-08-23)
==================

- Bugfix for the change introduced in 1.3.1.

1.3.1 (2010-08-23)
==================

- Support recipes that are using zc.recipe.egg by passing in a dict, rather
  than a zc.buildout.buildout.Options object as was expected/tested.

1.3.0 (2010-08-23)
==================

- Small further refactorings past 1.2.3b1 to be compatible with
  zc.buildout 1.5.0.

1.2.3b1 (2010-04-29)
====================

- Refactored to be used with z3c.recipe.scripts and zc.buildout 1.5.0.
  No new user-visible features.

1.2.2 (2009-03-18)
==================

- Fixed a dependency information. zc.buildout >1.2.0 is required.

1.2.1 (2009-03-18)
==================

- Refactored generation of relative egg paths to generate simpler code.

1.2.0 (2009-03-17)
==================

- Added the `dependent-scripts` option.  When set to `true`, scripts will
  be generated for all required eggs in addition to the eggs named
  specifically.  This idea came from two forks of this recipe,
  `repoze.recipe.egg` and `pylons_sandbox`, but the option name is
  spelled with a dash instead of underscore and it defaults to `false`.

- Added a relative-paths option. When true, egg paths in scripts are generated
  relative to the script names.

1.1.0 (2008-07-19)
==================

- Refactored to work honor the new buildout-level unzip option.


1.1.0b1 (2008-06-27)
====================

- Added `environment` option to custom extension building options.

1.0.0 (2007-11-03)
==================

- No code changes from last beta, just some small package meta-data
  improvements.

1.0.0b5 (2007-02-08)
====================

Feature Changes
---------------

- Added support for the buildout newest option.

1.0.0b4 (2007-01-17)
====================

Feature Changes
---------------

- Added initialization and arguments options to the scripts recipe.

- Added an eggs recipe that *just* installs eggs.

- Advertized the scripts recipe for creating scripts.

1.0.0b3 (2006-12-04)
====================

Feature Changes
---------------

- Added a develop recipe for creating develop eggs.

  This is useful to:

  - Specify custom extension building options,

  - Specify a version of Python to use, and to

  - Cause develop eggs to be created after other parts.

- The develop and build recipes now return the paths created, so that
  created eggs or egg links are removed when a part is removed (or
  changed).


1.0.0b2 (2006-10-16)
====================

Updated to work with (not get a warning from) zc.buildout 1.0.0b10.

1.0.0b1
=======

Updated to work with zc.buildout 1.0.0b3.

1.0.0a3
=======

- Extra path elements to be included in generated scripts can now be
  set via the extra-paths option.

- No longer implicitly generate "py\_" scripts for each egg. There is
  now an interpreter option to generate a script that, when run
  without arguments, launches the Python interactive interpreter with
  the path set based on a parts eggs and extra paths.  If this script
  is run with the name of a Python script and arguments, then the
  given script is run with the path set.

- You can now specify explicit entry points.  This is useful for use
  with packages that don't declare their own entry points.

- Added Windows support.

- Now-longer implicitly generate "py\_" scripts for each egg.  You can
  now generate a script for launching a Python interpreter or for
  running scripts based on the eggs defined for an egg part.

- You can now specify custom entry points for packages that don't
  declare their entry points.

- You can now specify extra-paths to be included in generated scripts.


1.0.0a2
=======

Added a custom recipe for building custom eggs using custom distutils
build_ext arguments.

1.0.0a1
=======

Initial public version
