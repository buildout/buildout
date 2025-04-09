======================================================================
Staying DRY with value substitutions, extending, and macros
======================================================================

A buildout configuration is a collection of sections, each holding a
collection of options.  It's common for option values to be repeated
across options.  For examples, many file-path options might start
with common path prefixes. Configurations that include clients and
servers might share server-address options.  This topic presents
various ways you can reuse option values without repeating yourself.

.. _value-substitutions:

Value substitutions
======================

When supplying values in a configuration, you can include values from
other options using the syntax::

  ${SECTION:OPTION}

For example: ``${buildout:directory}`` refers to the value of the
``directory`` option in the in the ``buildout`` section of the
configuration.  The value of the referenced option will be substituted
for the referencing text.

You can simplify references to options in the current section by omitting the
section name.  If we wanted to use the ``buildout`` ``directory``
option from within the ``buildout`` section itself, we could use
``${:directory}``.  This convenience is especially useful in
:ref:`macros <macros-label>`, which we'll discuss later in this topic.

There's a special value that's also useful in macros, named
``_buildout_section_name_``, which has the name of the current
section. We'll show how this is used when we discuss :ref:`macros
<macros-label>`.

Default and computed option values
===================================

Many sections have option values that can be used in substitutions
without being defined in a configuration.

The ``buildout`` section, where settings for the buildout as a whole
are provided has many default option values. For example, the
directory where scripts are installed is configurable and the value is
available as ``${buildout:bin-directory}``.  See the :ref:`Buildout
options reference <buildout-configuration-options-reference>` for a
complete list of Buildout options that can be used in substitutions.

Many recipes also have options that have defaults or that are computed and
are available for substitutions.

Sources of configuration options
====================================

Configuration option values can come from a number of sources (in
increasing precedence):

software default values
  These are defined by buildout and recipe sources.

user default values
  These are set in :ref:`per-user default configuration files
  <user-default-configuration>` and override default values.

options from one or more configuration files
  These override user defaults and each other, as described below.

option assignments in the :ref:`buildout command line <buildout-command-line>`
  These override configuration-file options.

.. _extends_option:

Extending configuration files
================================

The :ref:`extends <extends-option-ref>` option in a ``buildout``
section can be used to extend one or more configuration files.  There
are a number of applications for this. For example, common options for
a set of projects might be kept in a common base configuration.  A
production buildout could extend a development buildout, or they could
both extend a common base.

The option values in the extending configuration file override those
in the files being extended.  If multiple configurations are named in
the ``extends`` option (separated by whitespace), then the
configurations are processed in order from left/top to right/bottom,
with the later (right/bottom) configurations overriding earlier
(left/top) ones. For example, in:

.. code-block:: ini

   extends = base1.cfg base2.cfg
             base3.cfg

.. -> src

    >>> write("[buildout]\na=11\nb=12\n", 'base1.cfg')
    >>> write("[buildout]\nb=21\nc=22\n", 'base2.cfg')
    >>> write("[buildout]\nc=31\nd=32\n", 'base3.cfg')
    >>> write("[buildout]\nparts=\n" + src, 'buildout.cfg')
    >>> run_buildout("buildout -vv")
    >>> print(read()) # doctest: +ELLIPSIS
    Creating ...
    [buildout]
    a = 11
    allow-hosts = *
    allow-picked-versions = true
    allow-unknown-extras = false
    b = 21
    bin-directory = ...
    c = 31
    d = 32
    develop-eggs-directory = ...

    >>> clear_here()

The options in the configuration using the extends option override the
options in ``base3.cfg``, which override the options in ``base2.cfg``,
which override the options in ``base1.cfg``.

Base configurations may be extended multiple times. For example, in
the example above, ``base1.cfg`` might, itself, extend ``base3.cfg``,
or they might both extend a common base configuration.  Of course, cycles
are not allowed.

Configurations may be named with URLs in the ``extends`` option, in
which case they may be downloaded from remote servers.  See :ref:`The
extends-cache buildout option <extends-cache-buildout-option>`.

When a relative path is used in an extends option, it's interpreted
relative to the path of the extending configuration.

.. _conditional-sections:

Conditional configuration sections
==================================

Sometimes, you need different configuration in different environments
(different operating systems, or different versions of Python).  To
make this easier, you can define environment-specific options by
providing conditional sections:

.. code-block:: ini

    [ctl]
    suffix =

    [ctl:windows]
    suffix = .bat

.. -> conf

    >>> import zc.buildout.configparser
    >>> import six
    >>> zc.buildout.configparser.parse(
    ...     six.StringIO(conf), 'test', lambda : dict(windows=True))
    {'ctl': {'suffix': '.bat'}}
    >>> zc.buildout.configparser.parse(
    ...     six.StringIO(conf), 'test', lambda : dict(windows=False))
    {'ctl': {'suffix': ''}}

In this tiny example, we've defined a ``ctl:suffix`` option that's
``.bat`` on Windows and an empty string elsewhere.

A conditional section has a colon and then a Python expression after
the name.  If the Python expression result is true, the section
options from the section are included.  If the value is false, the
section is ignored.

Some things to note:

- If there is no exception, then options from the section are
  included.

- Sections and options can be repeated.  If an option is repeated, the
  last value is used. In the example above, on Windows, the second
  ``suffix`` option overrides the first.  If the order of the sections
  was reversed, the conditional section would have no effect.

In addition to the normal built-ins, the expression has access to
global variables that make common cases short and descriptive as shown
below

=============  ====================================================
Name           Value
=============  ====================================================
sys            ``sys`` module
os             ``os`` module
platform       ``platform`` module
re             ``re`` module
python2        True if running Python 2
python3        True if running Python 3
python26       True if running Python 2.6
python27       True if running Python 2.7
python32       True if running Python 3.2
python33       True if running Python 3.3
python34       True if running Python 3.4
python35       True if running Python 3.5
python36       True if running Python 3.6
python37       True if running Python 3.7
python38       True if running Python 3.8
python39       True if running Python 3.9
python310      True if running Python 3.10
sys_version    ``sys.version.lower()``
pypy           True if running PyPy
jython         True if running Jython
iron           True if running Iron Python
cpython        True if not running PyPy, Jython, or Iron Python
sys_platform   ``str(sys.platform).lower()``
linux          True if running on Linux
windows        True if running on Windows
cygwin         True if running on Cygwin
solaris        True if running on Solaris
macosx         True if running on Mac OS X
posix          True if running on a POSIX-compatible system
bits32         True if running on a 32-bit system.
bits64         True if running on a 64-bit system.
little_endian  True if running on a little-endian system
big_endian     True if running on a big-endian system
=============  ====================================================

Expressions must not contain either the ``#`` or the ``;`` character.

.. _user-default-configuration:

User-default configuration
==============================

A per-user default configuration may be defined in the ``default.cfg``
file in the ``.buildout`` subdirectory of a user's home directory
(``~/.buildout/default.cfg`` on Mac OS and Linux).  This configuration
is typically used to set up a shared egg or cache directory, as in:

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

See the section on :doc:`optimizing buildouts with shared eggs and
download caches <optimizing>` for an explanation of the options
used in the example above.

.. _merge-values-with-existing-values:

Merging, rather than overriding values
========================================

Normally, values in extending configurations override values in
extended configurations by replacing them, but it's also possible to
augment or trim overridden values.  If ``+=`` is used rather than
``=``, the overriding option value is appended to the original. So,
for example if we have a base configuration, ``buildout.cfg``:

.. code-block:: ini

   [buildout]
   parts =
     py
     test
     server
   ...

.. -> src

   >>> py_part = """
   ... [{name}]
   ... recipe = zc.recipe.egg
   ... eggs = bobo
   ... scripts = {name}
   ... interpreter = {name}
   ... """
   >>> parts = (py_part.format(name='py')
   ...        + py_part.format(name='test')
   ...        + py_part.format(name='server'))
   >>> write(src.replace('...', parts), 'buildout.cfg')
   >>> run_buildout()
   >>> eqs(ls('bin'), 'py', 'test', 'server')

And a production configuration ``prod.cfg``, we can add another part,
``monitor``, like this:

.. code-block:: ini

   [buildout]
   extends = buildout.cfg
   parts += monitor
   ...

.. -> src

   >>> write(src.replace('...', py_part.format(name='monitor')), 'e.cfg')
   >>> run_buildout("buildout -N -c e.cfg")
   >>> eqs(ls('bin'), 'py', 'test', 'server', 'monitor')

In this example, we didn't have to repeat (or necessarily know) the
base parts to add the ``monitor`` part.

We can also subtract values using ``-=``, so if we wanted to exclude
the ``test`` part in production:

.. code-block:: ini

   [buildout]
   extends = buildout.cfg
   parts += monitor
   parts -= test
   ...

.. -> src

   >>> write(src.replace('...', py_part.format(name='monitor')), 'e.cfg')
   >>> run_buildout("buildout -N -c e.cfg")
   >>> eqs(ls('bin'), 'py', 'server', 'monitor')

   >>> clear_here()

Something to keep in mind is that this works by *lines*.  The ``+=``
form adds the lines in the new data to the lines of the
old. Similarly, ``-=`` removes *lines* in the overriding option from the
original *lines*. This is a bit delicate.  In the example above,
we were careful to put the base values on separate lines, in
anticipation of using ``-=``.

Merging values also works with option assignments provided via the
:ref:`buildout command line <buildout-command-line>`.  For example, if
you want to temporarily use a :ref:`development version
<python-development-projects>` of another project, you can augment the
buildout :ref:`develop option <develop-option>` on the command-line
when running buildout:

.. code-block:: console

   buildout develop+=/path/to/other/project

.. -> src

   >>> write("import setuptools; setuptools.setup(name='a', py_modules=['a'])", "setup.py")
   >>> write('pass', 'a.py')
   >>> write("""
   ... [buildout]
   ... develop=.
   ... parts=py
   ... [py]
   ... recipe=zc.recipe.egg
   ... eggs = a
   ...        b
   ... [versions]
   ... b=1
   ... """, "buildout.cfg")
   >>> os.mkdir('b')
   >>> write("import setuptools; setuptools.setup(name='b', py_modules=['b'], version=1)",
   ...       "b", "setup.py")
   >>> write('pass', 'b.py')
   >>> run_buildout(src.replace('/path/to/other/project', 'b'))
   >>> eqs(ls('develop-eggs'), 'b.egg-link', 'a.egg-link')

.. _unpinning-on-command-line:

Although, if you've pinned the version of that project, you'll need to
:ref:`unpin it <unpinning-versions>`, which you can also do on the command-line:

.. code-block:: console

   buildout develop+=/path/to/other/project versions:projectname=

.. -> src

   >>> write("import setuptools; setuptools.setup(name='b', version=2)",
   ...       "b", "setup.py")
   >>> run_buildout(src.replace('/path/to/other/project', 'b')
   ...                 .replace('projectname', 'b'))
   >>> eqs(ls('develop-eggs'), 'b.egg-link', 'a.egg-link')

   >>> clear_here()

.. _macros-label:

Extending sections using macros
===============================

We can extend other sections in a configuration as macros by naming
then using the ``<`` option.  For example, perhaps we have to create
multiple server processes that listen on different ports.  We might
have a base ``server`` section, and some sections that use it as a
macro:

.. code-block:: ini

   [server]
   recipe = zc.zdaemonrecipe
   port = 8080
   program =
     ${buildout:bin-directory}/serve
        --port ${:port}
        --name ${:_buildout_section_name_}

   [server1]
   <= server
   port = 8081

   [server2]
   <= server
   port = 8082

.. -> src

   >>> write("[buildout]\nparts=server server1 server2\n" + src, "buildout.cfg")
   >>> run_buildout("buildout -vv")
   >>> print(read()) # doctest: +ELLIPSIS
   Creating ...
   [server]
   ...
   port = 8080
   program = .../bin/serve...--port 8080...--name server
   ...
   recipe = zc.zdaemonrecipe
   ...
   [server1]
   ...
   port = 8081
   program = .../bin/serve...--port 8081...--name server1
   ...
   recipe = zc.zdaemonrecipe
   ...
   [server2]
   ...
   port = 8082
   program = .../bin/serve...--port 8082...--name server2
   ...
   recipe = zc.zdaemonrecipe
   ...

In the example above, the ``server1`` and  ``server2`` sections use the
``server`` section, getting its ``recipe`` and ``program`` options.
The resulting configuration is equivalent to:

.. code-block:: ini

   [server]
   recipe = zc.zdaemonrecipe
   port = 8080
   program =
     ${buildout:bin-directory}/serve
        --port ${:port}
        --name ${:_buildout_section_name_}

   [server1]
   recipe = zc.zdaemonrecipe
   port = 8081
   program =
     ${buildout:bin-directory}/serve
        --port ${:port}
        --name ${:_buildout_section_name_}

   [server2]
   recipe = zc.zdaemonrecipe
   port = 8082
   program =
     ${buildout:bin-directory}/serve
        --port ${:port}
        --name ${:_buildout_section_name_}

.. -> src

   >>> write("[buildout]\nparts=server server1 server2\n" + src, "buildout.cfg")
   >>> run_buildout("buildout -vv")
   >>> print(read()) # doctest: +ELLIPSIS
   Installing ...
   [server]
   ...
   port = 8080
   program = .../bin/serve...--port 8080...--name server
   ...
   recipe = zc.zdaemonrecipe
   ...
   [server1]
   ...
   port = 8081
   program = .../bin/serve...--port 8081...--name server1
   ...
   recipe = zc.zdaemonrecipe
   ...
   [server2]
   ...
   port = 8082
   program = .../bin/serve...--port 8082...--name server2
   ...
   recipe = zc.zdaemonrecipe
   ...

Value substitutions in the base section are applied after its
application as a macro, so the substitutions are applied using data
from the sections that used the macro (using the ``<`` option).

You can extend multiple sections by listing them in the ``<`` option
on separate lines, as in:

.. code-block:: ini

   [server2]
   <= server
      monitored
   port = 8082

.. -> src

   >>> old = read('buildout.cfg')
   >>> write(old + src + """
   ... [monitored]
   ... name = ${:_buildout_section_name_}
   ... mport = 1${:port}
   ... """, "buildout.cfg")
   >>> run_buildout("buildout -vv")
   >>> print(read()) # doctest: +ELLIPSIS
   Installing ...
   [server2]
   ...
   mport = 18082
   name = server2
   port = 8082
   program = .../bin/serve...--port 8082...--name server2
   ...
   recipe = zc.zdaemonrecipe
   ...

If multiple sections are extended, they're processed in order, with
later ones taking precedence.  In the example above, if both
``server`` and ``monitored`` provided an option, then the value from
``monitored`` would be used.

A section that's used as a macro can extend another section.
