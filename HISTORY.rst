Change History -- Old changes
*****************************

2.0.0 (2013-02-10)
==================

This is a backward incompatible release of buildout that attempts to
correct mistakes made in buildout 1.

- Buildout no-longer tries to provide full or partial isolation from
  system Python installations. If you want isolation, use buildout
  with virtualenv, or use a clean build of Python to begin with.

  Providing isolation was a noble goal, but it's implementation
  complicated buildout's implementation too much.

- Buildout no-longer supports using multiple versions of Python in a
  single buildout.  This too was a noble goal, but added too much
  complexity to the implementation.

- Changed the configuration file format:

  - Relative indentation in option values is retained if the first
    line is blank. (IOW, if the non-blank text is on the continuation
    lines.) As in::

       [mysection]
       tree =
         /root
           branch

    In such cases, internal blank lines are also retained.

  - The configuration syntax is more tightly defined, allowing fewer
    syntax definitions.

    Buildout 1 configuration files were parsed with the Python
    ConfigParser module. The ConfigParser module's format is poorly
    documented and wildly flexible. For example:

    - Any characters other than left square brackets were allowed in
      section names.

    - Arbitrary text was allowed and ignored after the closing bracket on
      section header lines.

    - Any characters other than equal signs or colons were allowed in an
      option name.

    - Configuration options could be spelled as RFC 822 mail headers
      (using a colon, rather than an equal sign).

    - Comments could begin with "rem".

    - Semicolons could be used to start inline comments, but only if
      preceded by a whitespace character.

  See `Configuration file syntax`_.

- Buildout now prefers final releases by default
  (buildout:prefer-final now defaults to true, rather than false.)

  However, if buildout is bootstrapped with a non-final release, it
  won't downgrade itself to a final release.

- Buildout no-longer installs zipped eggs. (Distribute may still
  install a zipped egg of itself during the bootstrapping process.)
  The ``buildout:unzip`` option has been removed.

- Buildout no-longer supports setuptools. It now uses distribute
  exclusively.

- Integrated the `buildout-versions
  <http://packages.python.org/buildout-versions/>`_ extension into buildout
  itself. For this, a few options were added to buildout:

  - If ``show-picked-versions`` is set to true, all picked versions are
    printed at the end of the buildout run. This saves you from running
    buildout in verbose mode and extracting the picked versions from the
    output.

  - If ``update-versions-file`` is set to a filename (relative to the buildout
    directory), the ``show-picked-versions`` output is appended to that file.

- Buildout options can be given on the command line using the form::

    option_name=value

  as a short-hand for::

    buildout:option_name=value

- The ``versions`` option now defaults to ``versions``, so you no
  longer need to include::

     versions = versions

  in a ``buildout`` section when pinning versions.

  A ``versions`` section is added, if necessary, if a ``versions``
  option isn't used.

- Buildout-defined default versions are included in the versions
  section, if there is one.

- The ``buildout:zc.buildout-version`` and
  ``buildout:distribute-version`` options have been removed in favor
  of providing version constraints in a versions section.

- Error if install-from-cache and offline are used together, because
  offline largely means "don't install".

- Provide better error messages when distributions can't be installed
  because buildout is run in offline mode.

- Versions in versions sections can now be simple constraints, like
  >=2.0dev in addition to being simple versions.

  Buildout 2 leverages this to make sure it uses
  zc.recipe.egg>=2.0.0a3, which mainly matters for Python 3.

- The buildout init command now accepts distribution requirements and
  paths to set up a custom interpreter part that has the distributions
  or parts in the path. For example::

     python bootstrap.py init BeautifulSoup

- Added buildout:socket-timeout option so that socket timeout can be configured
  both from command line and from config files. (gotcha)

- Distutils-style scripts are also installed now (for instance pyflakes' and
  docutils' scripts).  https://bugs.launchpad.net/zc.buildout/+bug/422724

- Avoid sorting the working set and requirements when it won't be
  logged.  When profiling a simple buildout with 10 parts with
  identical and large working sets, this resulted in a decrease of run
  time from 93.411 to 15.068 seconds, about a 6 fold improvement.  To
  see the benefit be sure to run without any increase in verbosity
  ("-v" option).  (rossp)

- Introduce a cache for the expensive `buildout._dir_hash` function.

- Remove duplicate path from script's sys.path setup.

- Make sure to download extended configuration files only once per buildout
  run even if they are referenced multiple times (patch by Rafael Monnerat).

- Removed any traces of the implementation of ``extended-by``. Raise a
  UserError if the option is encountered instead of ignoring it, though.

Fixed: relative-paths weren't honored when bootstrapping or upgrading
       (which is how the buildout script gets generated).

Fixed: initialization code wasn't included in interpreter scripts.

Fixed: macro inheritance bug, https://github.com/buildout/buildout/pull/37

Fixed: In the download module, fixed the handling of directories that
       are pointed to by file-system paths and ``file:`` URLs.

Fixed if you have a configuration with an extends entry in the [buildout]
      section which points to a non-existing URL the result is not very
      user friendly. https://bugs.launchpad.net/zc.buildout/+bug/566167

Fixed: https://bugs.launchpad.net/bugs/697913 : Buildout doesn't honor exit code
       from scripts. Fixed.

1.4.4 (2010-08-20)
==================

The 1.4.4 release is a release for people who encounter trouble
with the 1.5 line.  By switching to `the associated bootstrap script
<https://raw.github.com/buildout/buildout/master/bootstrap/bootstrap.py>`_
you can stay on 1.4.4 until you are ready to migrate.

1.4.3 (2009-12-10)
==================

Bugs fixed:

- Using pre-detected setuptools version for easy_installing tgz files.  This
  prevents a recursion error when easy_installing an upgraded "distribute"
  tgz.  Note that setuptools did not have this recursion problem solely
  because it was packaged as an ``.egg``, which does not have to go through
  the easy_install step.


1.4.2 (2009-11-01)
==================

New Feature:

- Added a --distribute option to the bootstrap script, in order
  to use Distribute rather than Setuptools. By default, Setuptools
  is used.

Bugs fixed:

- While checking for new versions of setuptools and buildout itself,
  compare requirement locations instead of requirement objects.

- Incrementing didn't work properly when extending multiple files.
  https://bugs.launchpad.net/zc.buildout/+bug/421022

- The download API computed MD5 checksums of text files wrong on Windows.

1.4.1 (2009-08-27)
==================

New Feature:

- Added a debug built-in recipe to make writing some tests easier.

Bugs fixed:

- (introduced in 1.4.0) option incrementing (-=) and decrementing (-=)
  didn't work in the buildout section.
  https://bugs.launchpad.net/zc.buildout/+bug/420463

- Option incrementing and decrementing didn't work for options
  specified on the command line.

- Scripts generated with relative-paths enabled couldn't be
  symbolically linked to other locations and still work.

- Scripts run using generated interpreters didn't have __file__ set correctly.

- The standard Python -m option didn't work for custom interpreters.

1.4.0 (2009-08-26)
==================

- When doing variable substitutions, you can omit the section name to
  refer to a variable in the same section (e.g. ${:foo}).

- When doing variable substitution, you can use the special option,
  ``_buildout_section_name_`` to get the section name.  This is most handy
  for getting the current section name (e.g. ${:_buildout_section_name_}).

- A new special option, ``<`` allows sections to be used as macros.

- Added annotate command for annotated sections. Displays sections
  key-value pairs along with the value origin.

- Added a download API that handles the download cache, offline mode etc and
  is meant to be reused by recipes.

- Used the download API to allow caching of base configurations (specified by
  the buildout section's 'extends' option).

1.3.1 (2009-08-12)
==================

- Bug fixed: extras were ignored in some cases when versions were specified.

1.3.0 (2009-06-22)
==================

- Better Windows compatibility in test infrastructure.

- Now the bootstrap.py has an optional --version argument,
  that can be used to force buildout version to use.

- ``zc.buildout.testing.buildoutSetUp`` installs a new handler in the
  python root logging facility. This handler is now removed during
  tear down as it might disturb other packages reusing buildout's
  testing infrastructure.

- fixed usage of 'relative_paths' keyword parameter on Windows

- Added an unload entry point for extensions.

- Fixed bug: when the relative paths option was used, relative paths
  could be inserted into sys.path if a relative path was used to run
  the generated script.

1.2.1 (2009-03-18)
==================

- Refactored generation of relative egg paths to generate simpler code.

1.2.0 (2009-03-17)
==================

- Added a relative_paths option to zc.buildout.easy_install.script to
  generate egg paths relative to the script they're used in.

1.1.2 (2009-03-16)
==================

- Added Python 2.6 support. Removed Python 2.3 support.

- Fixed remaining deprecation warnings under Python 2.6, both when running
  our tests and when using the package.

- Switched from using os.popen* to subprocess.Popen, to avoid a deprecation
  warning in Python 2.6.  See:

  http://docs.python.org/library/subprocess.html#replacing-os-popen-os-popen2-os-popen3

- Made sure the 'redo_pyc' function and the doctest checkers work with Python
  executable paths containing spaces.

- Expand shell patterns when processing the list of paths in `develop`, e.g::

    [buildout]
    develop = ./local-checkouts/*

- Conditionally import and use hashlib.md5 when it's available instead
  of md5 module, which is deprecated in Python 2.6.

- Added Jython support for bootstrap, development bootstrap
  and buildout support on Jython

- Fixed a bug that would cause buildout to break while computing a
  directory hash if it found a broken symlink (Launchpad #250573)

1.1.1 (2008-07-28)
==================

- Fixed a bug that caused buildouts to fail when variable
  substitutions are used to name standard directories, as in::

    [buildout]
    eggs-directory = ${buildout:directory}/develop-eggs

1.1.0 (2008-07-19)
==================

- Added a buildout-level unzip option to change the default policy for
  unzipping zip-safe eggs.

- Tracebacks are now printed for internal errors (as opposed to user
  errors) even without the -D option.

- pyc and pyo files are regenerated for installed eggs so that the
  stored path in code objects matches the install location.

1.0.6 (2008-06-13)
==================

- Manually reverted the changeset for the fix for
  https://bugs.launchpad.net/zc.buildout/+bug/239212 to verify thet the test
  actually fails with the changeset:
  http://svn.zope.org/zc.buildout/trunk/src/zc/buildout/buildout.py?rev=87309&r1=87277&r2=87309
  Thanks tarek for pointing this out. (seletz)

- fixed the test for the += -= syntax in buildout.txt as the test
  was actually wrong. The original implementation did a split/join
  on whitespace, and later on that was corrected to respect the original
  EOL setting, the test was not updated, though. (seletz)

- added a test to verify against https://bugs.launchpad.net/zc.buildout/+bug/239212
  in allowhosts.txt (seletz)

- further fixes for """AttributeError: Buildout instance has no
  attribute '_logger'""" by providing reasonable defaults
  within the Buildout constructor (related to the new 'allow-hosts' option)
  (patch by Gottfried Ganssauge) (ajung)


1.0.5 (2008-06-10)
==================

- Fixed wrong split when using the += and -= syntax (mustapha)

1.0.4 (2008-06-10)
==================

- Added the `allow-hosts` option (tarek)

- Quote the 'executable' argument when trying to detect the python
  version using popen4. (sidnei)

- Quote the 'spec' argument, as in the case of installing an egg from
  the buildout-cache, if the filename contains spaces it would fail (sidnei)

- Extended configuration syntax to allow -= and += operators (malthe, mustapha).

1.0.3 (2008-06-01)
==================

- fix for """AttributeError: Buildout instance has no attribute '_logger'"""
  by providing reasonable defaults within the Buildout constructor.
  (patch by Gottfried Ganssauge) (ajung)

1.0.2 (2008-05-13)
==================

- More fixes for Windows. A quoted sh-bang is now used on Windows to make the
  .exe files work with a Python executable in 'program files'.

- Added "-t <timeout_in_seconds>" option for specifying the socket timeout.
  (ajung)

1.0.1 (2008-04-02)
==================

- Made easy_install.py's _get_version accept non-final releases of Python,
  like 2.4.4c0. (hannosch)

- Applied various patches for Windows (patch by Gottfried Ganssauge). (ajung)

- Applied patch fixing rmtree issues on Windows (patch by
  Gottfried Ganssauge).  (ajung)

1.0.0 (2008-01-13)
==================

- Added a French translation of the buildout tutorial.

1.0.0b31 (2007-11-01)
=====================

Feature Changes
---------------

- Added a configuration option that allows buildouts to ignore
  dependency_links metadata specified in setup. By default
  dependency_links in setup are used in addition to buildout specified
  find-links. This can make it hard to control where eggs come
  from. Here's how to tell buildout to ignore URLs in
  dependency_links::

    [buildout]
    use-dependency-links = false

  By default use-dependency-links is true, which matches the behavior
  of previous versions of buildout.

- Added a configuration option that causes buildout to error if a
  version is picked. This is a nice safety belt when fixing all
  versions is intended, especially when creating releases.

Bugs Fixed
----------

- 151820: Develop failed if the setup.py script imported modules in
  the distribution directory.

- Verbose logging of the develop command was omitting detailed
  output.

- The setup command wasn't documented.

- The setup command failed if run in a directory without specifying a
  configuration file.

- The setup command raised a stupid exception if run without arguments.

- When using a local find links or index, distributions weren't copied
  to the download cache.

- When installing from source releases, a version specification (via a
  buildout versions section) for setuptools was ignored when deciding
  which setuptools to use to build an egg from the source release.

1.0.0b30 (2007-08-20)
=====================

Feature Changes
---------------

- Changed the default policy back to what it was to avoid breakage in
  existing buildouts.  Use::

    [buildout]
    prefer-final = true

  to get the new policy.  The new policy will go into effect in
  buildout 2.

1.0.0b29 (2007-08-20)
=====================

Feature Changes
---------------

- Now, final distributions are preferred over non-final versions.  If
  both final and non-final versions satisfy a requirement, then the
  final version will be used even if it is older.  The normal way to
  override this for specific packages is to specifically require a
  non-final version, either specifically or via a lower bound.

- There is a buildout prefer-final version that can be used with a
  value of "false"::

    prefer-final = false

  To prefer newer versions, regardless of whether or not they are
  final, buildout-wide.

- The new simple Python index, http://cheeseshop.python.org/simple, is
  used as the default index.  This will provide better performance
  than the human package index interface,
  http://pypi.python.org/pypi. More importantly, it lists hidden
  distributions, so buildouts with fixed distribution versions will be
  able to find old distributions even if the distributions have been
  hidden in the human PyPI interface.

Bugs Fixed
----------

- 126441: Look for default.cfg in the right place on Windows.

1.0.0b28 (2007-07-05)
=====================

Bugs Fixed
----------

- When requiring a specific version, buildout looked for new versions
  even if that single version was already installed.

1.0.0b27 (2007-06-20)
=====================

Bugs Fixed
----------

- Scripts were generated incorrectly on Windows.  This included the
  buildout script itself, making buildout completely unusable.

1.0.0b26 (2007-06-19)
=====================

Feature Changes
---------------

- Thanks to recent fixes in setuptools, I was able to change buildout
  to use find-link and index information when searching extensions.

  Sadly, this work, especially the timing, was motivated my the need
  to use alternate indexes due to performance problems in the cheese
  shop (http://www.python.org/pypi/).  I really home we can address
  these performance problems soon.

1.0.0b25 (2007-05-31)
=====================

Feature Changes
---------------

- buildout now changes to the buildout directory before running recipe
  install and update methods.

- Added a new init command for creating a new buildout. This creates
  an empty configuration file and then bootstraps.

- Except when using the new init command, it is now an error to run
  buildout without a configuration file.

- In verbose mode, when adding distributions to fulfil requirements of
  already-added distributions, we now show why the new distributions
  are being added.

- Changed the logging format to exclude the logger name for the
  buildout logger.  This reduces noise in the output.

- Clean up lots of messages, adding missing periods and adding quotes around
  requirement strings and file paths.

Bugs Fixed
----------

- 114614: Buildouts could take a very long time if there were
  dependency problems in large sets of pathologically interdependent
  packages.

- 59270: Buggy recipes can cause failures in later recipes via chdir

- 61890: file:// urls don't seem to work in find-links

  setuptools requires that file urls that point to directories must
  end in a "/".  Added a workaround.

- 75607: buildout should not run if it creates an empty buildout.cfg

1.0.0b24 (2007-05-09)
=====================

Feature Changes
---------------

- Improved error reporting by showing which packages require other
  packages that can't be found or that cause version conflicts.

- Added an API for use by recipe writers to clean up created files
  when recipe errors occur.

- Log installed scripts.

Bugs Fixed
----------

- 92891: bootstrap crashes with recipe option in buildout section.

- 113085: Buildout exited with a zero exist status when internal errors
  occurred.


1.0.0b23 (2007-03-19)
=====================

Feature Changes
---------------

- Added support for download caches.  A buildout can specify a cache
  for distribution downloads.  The cache can be shared among buildouts
  to reduce network access and to support creating source
  distributions for applications allowing install without network
  access.

- Log scripts created, as suggested in:
  https://bugs.launchpad.net/zc.buildout/+bug/71353

Bugs Fixed
----------

- It wasn't possible to give options on the command line for sections
  not defined in a configuration file.

1.0.0b22 (2007-03-15)
=====================

Feature Changes
---------------

- Improved error reporting and debugging support:

  - Added "logical tracebacks" that show functionally what the buildout
    was doing when an error occurs.  Don't show a Python traceback
    unless the -D option is used.

  - Added a -D option that causes the buildout to print a traceback and
    start the pdb post-mortem debugger when an error occurs.

  - Warnings are printed for unused options in the buildout section and
    installed-part sections.  This should make it easier to catch option
    misspellings.

- Changed the way the installed database (.installed.cfg) is handled
  to avoid database corruption when a user breaks out of a buildout
  with control-c.

- Don't save an installed database if there are no installed parts or
  develop egg links.

1.0.0b21 (2007-03-06)
=====================

Feature Changes
---------------

- Added support for repeatable buildouts by allowing egg versions to
  be specified in a versions section.

- The easy_install module install and build functions now accept a
  versions argument that supplied to mapping from project name to
  version numbers.  This can be used to fix version numbers for
  required distributions and their dependencies.

  When a version isn't fixed, using either a versions option or using
  a fixed version number in a requirement, then a debug log message is
  emitted indicating the version picked.  This is useful for setting
  versions options.

  A default_versions function can be used to set a default value for
  this option.

- Adjusted the output for verbosity levels.  Using a single -v option
  no longer causes voluminous setuptools output.  Using -vv and -vvv
  now triggers extra setuptools output.

- Added a remove testing helper function that removes files or directories.

1.0.0b20 (2007-02-08)
=====================

Feature Changes
---------------

- Added a buildout newest option, to control whether the newest
  distributions should be sought to meet requirements.  This might
  also provide a hint to recipes that don't deal with
  distributions. For example, a recipe that manages subversion
  checkouts might not update a checkout if newest is set to "false".

- Added a *newest* keyword parameter to the
  zc.buildout.easy_install.install and zc.buildout.easy_install.build
  functions to control whether the newest distributions that need
  given requirements should be sought.  If a false value is provided
  for this parameter and already installed eggs meet the given
  requirements, then no attempt will be made to search for newer
  distributions.

- The recipe-testing support setUp function now adds the name
  *buildout* to the test namespace with a value that is the path to
  the buildout script in the sample buildout.  This allows tests to
  use

    >>> print system(buildout),

  rather than:

    >>> print system(join('bin', 'buildout')),


Bugs Fixed
----------

- Paths returned from update methods replaced lists of installed files
  rather than augmenting them.

1.0.0b19 (2007-01-24)
=====================

Bugs Fixed
----------

- Explicitly specifying a Python executable failed if the output of
  running Python with the -V option included a 2-digit (rather than a
  3-digit) version number.

1.0.0b18 (2007-01-22)
=====================

Feature Changes
---------------

- Added documentation for some previously undocumented features of the
  easy_install APIs.

- By popular demand, added a -o command-line option that is a short
  hand for the assignment buildout:offline=true.

Bugs Fixed
----------

- When deciding whether recipe develop eggs had changed, buildout
  incorrectly considered files in .svn and CVS directories.

1.0.0b17 (2006-12-07)
=====================

Feature Changes
---------------

- Configuration files can now be loaded from URLs.

Bugs Fixed
----------

- https://bugs.launchpad.net/products/zc.buildout/+bug/71246

  Buildout extensions installed as eggs couldn't be loaded in offline
  mode.


1.0.0b16 (2006-12-07)
=====================

Feature Changes
---------------

- A new command-line argument, -U, suppresses reading user defaults.

- You can now suppress use of an installed-part database
  (e.g. .installed.cfg) by specifying an empty value for the buildout
  installed option.

Bugs Fixed
----------

- When the install command is used with a list of parts, only
  those parts are supposed to be installed, but the buildout was also
  building parts that those parts depended on.

1.0.0b15 (2006-12-06)
=====================

Bugs Fixed
----------

- Uninstall recipes weren't loaded correctly in cases where
  no parts in the (new) configuration used the recipe egg.

1.0.0b14 (2006-12-05)
=====================

Feature Changes
---------------

- Added uninstall recipes for dealing with complex uninstallation
  scenarios.

Bugs Fixed
----------

- Automatic upgrades weren't performed on Windows due to a bug that
  caused buildout to incorrectly determine that it wasn't running
  locally in a buildout.

- Fixed some spurious test failures on Windows.

1.0.0b13 (2006-12-04)
=====================

Feature Changes
---------------

- Variable substitutions now reflect option data written by recipes.

- A part referenced by a part in a parts list is now added to the parts
  list before the referencing part.  This means that you can omit
  parts from the parts list if they are referenced by other parts.

- Added a develop function to the easy_install module to aid in
  creating develop eggs with custom build_ext options.

- The build and develop functions in the easy_install module now
  return the path of the egg or egg link created.

- Removed the limitation that parts named in the install command can
  only name configured parts.

- Removed support ConfigParser-style variable substitutions
  (e.g. %(foo)s). Only the string-template style of variable
  (e.g. ${section:option}) substitutions will be supported.
  Supporting both violates "there's only one way to do it".

- Deprecated the buildout-section extendedBy option.

Bugs Fixed
----------

- We treat setuptools as a dependency of any distribution that
  (declares that it) uses namespace packages, whether it declares
  setuptools as a dependency or not.  This wasn't working for eggs
  installed by virtue of being dependencies.


1.0.0b12 (2006-10-24)
=====================

Feature Changes
---------------

- Added an initialization argument to the
  zc.buildout.easy_install.scripts function to include initialization
  code in generated scripts.

1.0.0b11 (2006-10-24)
=====================

Bugs Fixed
----------

`67737 <https://launchpad.net/products/zc.buildout/+bug/67737>`_
     Verbose and quite output options caused errors when the
     develop buildout option was used to create develop eggs.

`67871 <https://launchpad.net/products/zc.buildout/+bug/67871>`_
     Installation failed if the source was a (local) unzipped
     egg.

`67873 <https://launchpad.net/products/zc.buildout/+bug/67873>`_
     There was an error in producing an error message when part names
     passed to the install command weren't included in the
     configuration.

1.0.0b10 (2006-10-16)
=====================

Feature Changes
---------------

- Renamed the runsetup command to setup. (The old name still works.)

- Added a recipe update method. Now install is only called when a part
  is installed for the first time, or after an uninstall. Otherwise,
  update is called.  For backward compatibility, recipes that don't
  define update methods are still supported.

- If a distribution defines namespace packages but fails to declare
  setuptools as one of its dependencies, we now treat setuptools as an
  implicit dependency.  We generate a warning if the distribution
  is a develop egg.

- You can now create develop eggs for setup scripts that don't use setuptools.

Bugs Fixed
----------

- Egg links weren't removed when corresponding entries were removed
  from develop sections.

- Running a non-local buildout command (one not installed in the
  buildout) led to a hang if there were new versions of buildout or
  setuptools were available.  Now we issue a warning and don't
  upgrade.

- When installing zip-safe eggs from local directories, the eggs were
  moved, rather than copied, removing them from the source directory.

1.0.0b9 (2006-10-02)
====================

Bugs Fixed
----------

Non-zip-safe eggs were not unzipped when they were installed.

1.0.0b8 (2006-10-01)
====================

Bugs Fixed
----------

- Installing source distributions failed when using alternate Python
  versions (depending on the versions of Python used.)

- Installing eggs wasn't handled as efficiently as possible due to a
  bug in egg URL parsing.

- Fixed a bug in runsetup that caused setup scripts that introspected
  __file__ to fail.

1.0.0b7
=======

Added a documented testing framework for use by recipes. Refactored
the buildout tests to use it.

Added a runsetup command run a setup script.  This is handy if, like
me, you don't install setuptools in your system Python.

1.0.0b6
=======

Fixed https://launchpad.net/products/zc.buildout/+bug/60582
Use of extension options caused bootstrapping to fail if the eggs
directory didn't already exist.  We no longer use extensions for
bootstrapping.  There really isn't any reason to anyway.


1.0.0b5
=======

Refactored to do more work in buildout and less work in easy_install.
This makes things go a little faster, makes errors a little easier to
handle, and allows extensions (like the sftp extension) to influence
more of the process. This was done to fix a problem in using the sftp
support.

1.0.0b4
=======

- Added an **experimental** extensions mechanism, mainly to support
  adding sftp support to buildouts that need it.

- Fixed buildout self-updating on Windows.

1.0.0b3
=======

- Added a help option (-h, --help)

- Increased the default level of verbosity.

- Buildouts now automatically update themselves to new versions of
  buildout and setuptools.

- Added Windows support.

- Added a recipe API for generating user errors.

- No-longer generate a py_zc.buildout script.

- Fixed some bugs in variable substitutions.

  The characters "-", "." and " ", weren't allowed in section or
  option names.

  Substitutions with invalid names were ignored, which caused
  misleading failures downstream.

- Improved error handling.  No longer show tracebacks for user errors.

- Now require a recipe option (and therefore a section) for every part.

- Expanded the easy_install module API to:

  - Allow extra paths to be provided

  - Specify explicit entry points

  - Specify entry-point arguments

1.0.0b2
=======

Added support for specifying some build_ext options when installing eggs
from source distributions.

1.0.0b1
=======

- Changed the bootstrapping code to only install setuptools and
  buildout. The bootstrap code no-longer runs the buildout itself.
  This was to fix a bug that caused parts to be recreated
  unnecessarily because the recipe signature in the initial buildout
  reflected temporary locations for setuptools and buildout.

- Now create a minimal setup.py if it doesn't exist and issue a
  warning that it is being created.

- Fixed bug in saving installed configuration data.  %'s and extra
  spaces weren't quoted.

1.0.0a1
=======

Initial public version
