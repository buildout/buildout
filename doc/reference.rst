=========
Reference
=========

.. _buildout-command-line:

The Buildout command line
=========================

A Buildout execution is of the form:

.. code-block:: console

  buildout [buildout-options] [settings] [subcommand [subcommand-arguments]]

Settings take the form ``section:option=value`` and override (or
augment) settings in configuration files.  For example, to pin a
version of ZEO you could use ``versions:ZEO=4.3.1``.  The section
defaults to the ``buildout`` section.  So, for example: ``parts=test``
sets the ``buildout`` section ``parts`` option.

Command-line settings overrides can use ``+=`` and ``-=`` to
:ref:`merge values with existing values <merge-values-with-existing-values>`

Buildout options
----------------

Buildout subcommands
--------------------

.. _bootstrap-subcommand:

bootstrap
_________

Install a local ``bootstrap`` script.  The ``bootstrap`` subcommand
doesn't take any arguments.

See :doc:`Bootstrapping <topics/bootstrapping>` for information on why
you might want to do this.

.. _init-subcommand:

init [requirements]
____________________

Generate a Buildout configuration file and bootstrap the resulting buildout.

If requirements are given, the generated configuration will have a
``py`` part that uses the ``zc.recipe.egg`` recipe to install the
requirements and generate an interpreter script that can import them.
It then runs the resulting buildout.

See :ref:`Bootstrapping <init-generates-buildout.cfg>` for examples.


.. _buildout-configuration-options-reference:

Buildout configuration options
===============================

The standard buildout options are shown below.  Values of options with
defaults shown can be used in :ref:`value substitutions
<value-substitutions>`.

abi-tag-eggs
  A flag (true/false) indicating whether the eggs directory should be
  divided into subdirectories by `ABI tag
  <https://www.python.org/dev/peps/pep-0425/#abi-tag>`_.  This may be
  useful if you use multiple Python builds with different build
  options or different Python implementations.  It's especially
  useful if you switch back and forth between PyPy and C Python.

allow-hosts, default: '*'
  Specify which hosts (as globs) you're willing to download
  distributions from when following :ref:`dependency links
  <use-dependency-links>`.

allow-picked-versions, default: 'true'
  Indicate whether it should be possible to install requirements whose
  `versions aren't pinned <pinned-versions>`.

bin-directory, default: bin
  The directory where generated scripts should be installed. If this
  is a relative path, it's evaluated relative to the buildout
  directory.

.. _develop-option:

develop
  One or more (whitespace-separated) paths to `distutils setup scripts
  <https://docs.python.org/3.6/distutils/setupscript.html>`_ or (more
  commonly) directories containing setup scripts named ``setup.py``.

  See: :ref:`Python development projects <python-development-projects>`.

develop-eggs-directory, default: 'develop-eggs'
  The directory where :ref:`develop eggs
  <python-development-projects>` should be installed. If this is a
  relative path, it's evaluated relative to the buildout directory.

directory, default: directory containing top-level buildout configuration
  The top of the buildout.  Other directories specified (or
  defaulting) with relative paths are created relative to this directory.

.. _download-cache:

download-cache
  An optional directory in which to cache downloads. Python
  distributions are cached in the ``dist`` subdirectory of this
  directory.  Recipes may also cache downloads in this directory, or
  in a subdirectory.

  This is often set in a :ref:`User-default configuration
  <user-default-configuration>` to share a cache between buildouts.
  See the section on :doc:`Optimizing buildouts with shared eggs and
  download caches <topics/optimizing>`.

  If the value is a relative path and doesn't contain value
  substitutions, it's interpreted relative to the directory containing
  the configuration file that defined the value. (If it contains value
  substitutions, and the result is a relative path, then it will be
  interpreted relative to the buildout directory.)

eggs-directory, default: 'eggs'
  The directory where :ref:`eggs <eggs-label>` are installed.

  This is often set in a :ref:`User-default configuration
  <user-default-configuration>` to share eggs between buildouts.
  See the section on :doc:`Optimizing buildouts with shared eggs and
  download caches <topics/optimizing>`.

  If the value is a relative path and doesn't contain value
  substitutions, it's interpreted relative to the directory containing
  the configuration file that defined the value. (If it contains value
  substitutions, and the result is a relative path, then it will be
  interpreted relative to the buildout directory.)

executable, default: sys.executable, read-only
  The full path to the Python executable used to run the buildout.

.. _extends-option-ref:

extends
  The names, separated by whitespace, of one or more configurations
  that the configuration containing the ``extends`` option should
  :ref:`extend <extends_option>`. The names may be file paths, or
  URLs.  If they are relative paths, they are interpreted relative to
  the configuration containing the ``extends`` option.

.. _extends-cache-buildout-option:

extends-cache
  An optional directory to cache remote configurations in.  Remote
  configuration is configuration specified using a URL in an
  :ref:`extends option <extends_option>` or as the argument to the
  :ref:`-C buildout command-line option <-C-option>`. How the
  extends-cache behaves depends on the buildout mode:

  +---------------------------------+------------------------------+
  | Mode                            | Behavior                     |
  +=================================+==============================+
  | :ref:`install-from-cache        | Configuration is retrieved   |
  | <install-from-cache-mode>` or   | from cache if possible. If   |
  | :ref:`offline <offline-mode>`   | configuration isn't cached,  |
  |                                 | the buildout fails.          |
  +---------------------------------+------------------------------+
  | :ref:`non-newest                | Configuration is retrieved   |
  | <non-newest-mode>`              | from cache if possible. If   |
  |                                 | configuration isn't cached,  |
  |                                 | then it is downloaded        |
  |                                 | and saved in the cache.      |
  +---------------------------------+------------------------------+
  | Default                         | Configuration is downloaded  |
  | (:ref:`newest <newest-mode>`)   | and saved in the cache, even |
  |                                 | if it is already cached, and |
  |                                 | the previously cached value  |
  |                                 | is replaced.                 |
  +---------------------------------+------------------------------+

  If the value is a relative path and doesn't contain value
  substitutions, it's interpreted relative to the directory containing
  the configuration file that defined the value. (If it contains value
  substitutions, and the result is a relative path, then it will be
  interpreted relative to the buildout directory.)

find-links, default: ''
  Extra locations to search for distributions to download.

  These may be file paths or URLs.  These may name individual
  distributions or directories containing
  distributions. Subdirectories aren't searched.

index
  An alternate index location.

  This can be a local directory name or an URL.  It can be a flat
  collection of distributions, but should be a "simple" index, with
  subdirectories for distribution `project names
  <https://packaging.python.org/distributing/#name>`_ containing
  distributions for those projects.

  If this isn't set, then ``https://pypi.python.org/simple/`` is used.

.. _install-from-cache-mode:

install-from-cache, default: 'false'
  Enable install-from-cache mode.

  In install-from-cache mode, no network requests should be made.

  It's a responsibility of recipes to adhere to this.  Recipes that
  would need to download files may use the :ref:`download cache
  <download-cache>`.

  The original purpose of the install-from-cache mode was to support
  source-distribution of buildouts that could be built without making
  network requests (mostly for security reasons).

  This mode may only be used if a :ref:`download-cache
  <download-cache>` is specified.

installed, default: '.installed.cfg'
  The name of the file used to store information about what's installed.

  Buildout keeps information about what's been installed so it can
  remove files created by parts that are removed and so it knows
  whether to update or install new parts from scratch.

  If this is a relative path, then it's interpreted relative to the
  buildout directory.

log-format, default: ''
  `Format
  <https://docs.python.org/3/library/logging.html#formatter-objects>`_
  to use for log messages.

  If ``log-format`` is blank, the default, Buildout will use the format::

    %(message)s

  for its own messages, and::

    %(name)s: %(message)s

  for the root logger [#root-logger]_.

  If ``log-format`` is non-blank, then it will be used for the root logger
  [#root-logger]_ (and for Buildout's messages).

log-level, default: 'INFO'
  The `logging level
  <https://docs.python.org/3/library/logging.html#logging-levels>`_.

  This may be adjusted with the :ref:`-v option <-v-option>` or the
  :ref:`-q option <-q-option>`, which are the more common ways to control
  the logging level.

  The ``log-level`` option is rarely used.

.. _newest-mode:

.. _non-newest-mode:

newest, default: 'true'
  If true, check for newer distributions.  If false, then only look
  for distributions when installed distributions don't satisfy requirements.

  The goal of non-newest mode is to speed Buildout runs by avoiding
  network requests.

.. _offline-mode:

offline, default: 'false'
  If true, then offline mode is enabled.

  .. Warning:: Offline mode is deprecated.

     Its purpose has evolved over time and the end result doesn't
     make much sense, but it is retained for backward compatibility.

     If you think you want an offline mode, you probably want the
     :ref:`install-from-cache <install-from-cache-mode>` mode instead.

  In offline mode, no network requests should be made.  It's the
  responsibility of recipes to adhere to this.  Recipes that would
  need to download files may use the :ref:`download
  cache <download-cache>`.

  No distributions are installed in offline mode. If installed
  distributions don't satisfy requirements, the the buildout will
  error in offline mode.

parts-directory, default: 'parts'
  The directory where generated part artifacts should be installed. If this
  is a relative path, it's evaluated relative to the buildout
  directory.

  If a recipe creates a file or directory, it will normally create it
  in the parts directory with a name that's the same as the part name.

prefer-final, default: 'true'
  If true, then only `final distribution releases
  <https://www.python.org/dev/peps/pep-0440/#final-releases>`_ will be
  used unless no final distributions satisfy requirements.

show-picked-versions, default: 'false'
  If true, when Buildout finds a newest distribution for a
  requirement that `wasn't pinned <pinned-versions>`, it will print
  lines it would write to a versions configuration if the
  :ref:`update-versions-file <update-versions-file>` option was used.

socket-timeout, default: ''
  Specify a socket timeout [#socket-timeout]_, in seconds, to use when
  downloading distributions and other artifacts.  If non-blank, the
  value must be a positive non-zero integer. If left blank, the socket
  timeout is system dependent.

  This may be useful if downloads are attempted from very slow
  sources.

.. _update-versions-file:

update-versions-file, default: ''
  If non-blank, this is the name of a file to write versions to when
  selecting a distribution for a requirement whose version `wasn't
  pinned <pinned-versions>`.  This file, typically ``versions.cfg``,
  should end with a ``versions`` section (or whatever name is
  specified by the ``versions`` option).

.. _use-dependency-links:

use-dependency-links, default: true
  Distribution meta-data may include URLs, called dependency links, of
  additional locations to search for distribution dependencies.  If
  this option is set to ``false``, then these URLs will be ignored.

versions, default 'versions'
  The name of a section that contains :ref:`version pins <pinned-versions>`.

.. [#root-logger] Generally, the root logger format is used for all
   messages unless it is overridden by a lower-level logger.

.. [#socket-timeout] This timeout reflects how long to wait on
   individual socket operations. A slow request may take much longer
   than this timeout.
