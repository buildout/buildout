=========
Reference
=========

.. _buildout-command-line:

The Buildout command line
=========================

A Buildout execution is of the form:

.. code-block:: console

  buildout [buildout-options] [assignments] [command [command arguments]]

Assignments take the form ``section:option=value`` and override (or
augment) options in configuration files.  For example, to pin a
version of ZEO you could use ``versions:ZEO=4.3.1``.  The section
defaults to the ``buildout`` section.  So, for example: ``parts=test``
sets the ``buildout`` section ``parts`` option.

Command-line assignments can use ``+=`` and ``-=`` to
:ref:`merge values with existing values <merge-values-with-existing-values>`

Buildout command-line options
-----------------------------

.. _-c-option:

``-c config_file``
  Specify the path (or URL) to the buildout configuration file to be used.
  This defaults to the file named ``buildout.cfg`` in the current
  working directory.

``-D``
  Debug errors.  If an error occurs, then the post-mortem debugger
  will be started. This is especially useful for debugging recipe
  problems.

``-h``, ``--help``
  Print basic usage information and exit.

``-N``
  Run in :ref:`non-newest mode <non-newest-mode>`.  This is equivalent
  to the command-line assignment ``newest=false``.

``-q``
  Decrease the level of verbosity.  This option can be used multiple
  times.

  Using a single ``-q`` suppresses normal output, but still shows
  warnings and errors.

  Doubling the option ``-qq`` (or equivalently ``-q -q``) suppresses
  normal output and warnings.

  Using the option more than twice suppresses errors, which is a bad idea.

``-t socket_timeout``
  Specify the socket timeout in seconds. See the
  :ref:`socket-timeout option <socket-timeout-option>` for details.

``-U``
  Don't use :ref:`user-default configuration <user-default-configuration>`.

.. _verbosity-level:

``-v``
  Increase the level of verbosity.  This option can be used multiple
  times.

  At the default verbosity, buildout prints messages about significant
  activities.  It also prints warning and error messages.

  At the next, "verbose", level (``-v``), it prints much
  more information. In particular, buildout will show when and why
  it's installing specific distribution versions.

  At the next, "debugging", level, ``-vv`` (or equivalently ``-v
  -v``), buildout prints low-level debugging information, including a
  listing of all configuration options, including: default options,
  computed options and the results of :ref:`value substitutions
  <value-substitutions>` and :ref:`macros <macros-label>`.

  Using this option more than twice has no effect.

``--version``
  Print buildout version number and exit.

Buildout commands
-----------------


.. _annotate-command:

annotate [sections]
___________________

Display the buildout configuration options, including their values and
where they came from. Try it!

.. code-block:: console

   buildout annotate

.. -> command

    >>> write("[buildout]\nparts=\n", "buildout.cfg")
    >>> run_buildout(command)
    >>> print(read()) # doctest: +ELLIPSIS
    Creating directory ...
    <BLANKLINE>
    Annotated sections
    ==================
    <BLANKLINE>
    [buildout]
    allow-hosts= *
        DEFAULT_VALUE
    ...

Increase the verbosity of the output to display all steps that compute the final values used by buildout.

.. code-block:: console

   buildout -v annotate

Pass one or more section names as arguments to display annotation only for the given sections.

.. code-block:: console

   buildout annotate versions


.. _bootstrap-command:

bootstrap
_________

Install a local ``bootstrap`` script.  The ``bootstrap`` command
doesn't take any arguments.

See :doc:`Bootstrapping <topics/bootstrapping>` for information on why
you might want to do this.

.. _init-command:

init [requirements]
____________________

Generate a Buildout configuration file and bootstrap the resulting buildout.

If requirements are given, the generated configuration will have a
``py`` part that uses the ``zc.recipe.egg`` recipe to install the
requirements and generate an interpreter script that can import them.
It then runs the resulting buildout.

See :ref:`Bootstrapping <init-generates-buildout.cfg>` for examples.

.. _install-command:

install
_______

Install the parts specified in the buildout configuration.  This is
the default command if no command is specified.

.. We're not documenting arguments.

   Passing arguments to install is an attractive nuisance, since it
   can lead to parts being installed inconsistently.  The feature
   exists for backward compatibility, but may be dropped in the
   future.

.. _query-command:

query [section:]key
___________________

Display the value of any buildout configuration option

.. code-block:: console

   buildout query buildout:parts

When you query the ``buildout`` section, you can pass the key only. For instance,

.. code-block:: console

   buildout query parts

is equivalent to the command above.

setup PATH SETUP-COMMANDS
_________________________

Run a setuptools-based setup script to build a distribution.

The path must be the path of a `setup script
<https://docs.python.org/3.6/distutils/setupscript.html>`_ or of a
directory containing one named ``setup.py``.  For example, to create a
source distribution using a setup script in the current directory:

.. code-block:: console

   buildout setup . sdist

.. -> command

   >>> write("""from setuptools import setup
   ... setup(name='foo', url='.', author='test', author_email='test@test.com')
   ... """, "setup.py")
   >>> write('test', 'README')
   >>> run_buildout(command.replace('.', '. -q'))
   >>> eqs(ls('dist'), 'foo-0.0.0.tar.gz')

This command is useful when the Python environment you're using
doesn't have setuptools installed.  Normally today, setuptools *is*
installed and you can just run setup scripts that use setuptools directly.

Note that if you want to build and upload a package to the `standard
package index <https://pypi.org>`_ you should consider
using `zest.releaser <https://pypi.org/project/zest.releaser>`_,
which automates many aspects of software release including checking
meta data, building releases and making version-control tags.

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

allow-unknown-extras, default: 'false'
  Specify whether requirements that specify an extra not provided by
  the target distribution should be allowed. When this is false, such
  a requirement is an error.

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

.. _find-links-option:

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

  If this isn't set, then ``https://pypi.org/simple/`` is used.

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

.. _installed-option:

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

     Its purpose has evolved over time and the end result doesn't make
     much sense, but it is retained (indefinitely) for backward
     compatibility.

     If you think you want an offline mode, you probably want either
     the :ref:`non-newest mode <non-newest-mode>` or the
     :ref:`install-from-cache mode <install-from-cache-mode>` instead.

  In offline mode, no network requests should be made.  It's the
  responsibility of recipes to adhere to this.  Recipes that would
  need to download files may use the :ref:`download
  cache <download-cache>`.

  No distributions are installed in offline mode. If installed
  distributions don't satisfy requirements, the the buildout will
  error in offline mode.

optional-extends
  Same as the :ref:`'extends' option <extends_option>`, but for optional files.
  The names must be file paths, not URLs.  If the path does not exist,
  it is silently ignored.

  This is useful for optionally loading a ``local.cfg`` or ``custom.cfg``
  with options specific for the developer or the server.

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

.. _socket-timeout-option:

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

Configuration file syntax
=========================

Buildout configurations use an `INI file format
<https://en.wikipedia.org/wiki/INI_file>`_.

A configuration is a collection of named sections containing named
options.

Section names
-------------

A section begins with a section and, optionally, a condition in
square braces (``[`` and ``]``).

A name can consist of any characters other than whitespace, square
braces, curly braces (``{`` or ``}``), pound signs (``#``), colons
(``:``) or semi-colons (``;``).  The name may be surrounded by leading
and trailing whitespace, which is ignored.

An optional condition is separated from the name by a colon and is a
Python expression.  It may not contain a pound sign or semi-colon.  See
the section on :ref:`conditional sections <conditional-sections>` for
an example and more details.

A comment, preceded by a pound sign or semicolon may follow the
section name, as in:

.. code-block:: ini

   [buildout] # This is the buildout section

.. -> header

Options
-------

Options are specified with an option name followed by an equal sign
and a value:

.. code-block:: ini

   parts = py

.. -> option

    >>> import six
    >>> import zc.buildout.configparser
    >>> def parse(s):
    ...     return zc.buildout.configparser.parse(six.StringIO(s), 'test')
    >>> from pprint import pprint
    >>> pprint(parse(header + option))
    {'buildout': {'parts': 'py'}}

Option names may have any characters other than whitespace, square
braces, curly braces, equal signs, or colons.  There may be and
usually is whitespace between the name and the equal sign and the name
and equal sign must be on the same line.  Names starting with ``<``
are reserved for Buildout's use.

Option values may contain any characters. A consequence of this is
that there can't be comments in option values.

Option values may be continued on multiple lines, and may contain blank lines:

.. code-block:: ini

   parts = py

           test

.. -> option

Whitespace in option values
___________________________

Trailing whitespace is stripped from each line in an option value.
Leading and trailing blank lines are stripped from option values.

Handling of leading whitespace and blank lines internal to values
depend on whether there is data on the first line (containing the
option name).

data on the first line
  Leading whitespace is stripped and blank lines are omitted.

  The resulting option value in the example above is:

  .. code-block:: ini

        py
        test

  .. -> val

      >>> eq(parse(header + option)['buildout']['parts'] + '\n', val)

no data on the first line
  Internal blank lines are retained and common leading white space is stripped.

  For example, the value of the option:

  .. code-block:: ini

     code =
         if x == 1:
             y = 2 # a comment

             return

  .. -> option

  is::

     if x == 1:
         y = 2 # a comment

         return

  .. -> val

       >>> eq(parse(header + option)['buildout']['code'] + '\n', val)

Special "implication" syntax for the ``<part-dependencies>`` option
____________________________________________________________________

An exception to the normal option syntax is the use of ``=>`` as a
short-hand for the ``<part-dependencies>`` option:

.. code-block:: ini

   => part1 part2
      part3

This is equivalent to:

.. code-block:: ini

   <part-dependencies> = part1 part2
      part3

and declares that the named parts are dependencies of the part in
which this option appears.

Comments and blank lines
------------------------

Lines beginning with pound signs or semi-colons (``#`` or ``;``) are
comments::

  # This is a comment
  ; This too

.. -> comment

       >>> eq(parse(comment + header + comment + option + comment )
       ...    ['buildout']['code'] + '\n', val)

As mentioned earlier, comments can also appear after section names.

Blank lines are ignored unless they're within option values that only
have data on continuation lines.

.. [#root-logger] Generally, the root logger format is used for all
   messages unless it is overridden by a lower-level logger.

.. [#socket-timeout] This timeout reflects how long to wait on
   individual socket operations. A slow request may take much longer
   than this timeout.
