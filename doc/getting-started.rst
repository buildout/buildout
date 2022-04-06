=============================
Getting started with Buildout
=============================

.. note::

   In the Buildout documentation, we'll use the word
   *buildout* to refer to:

   - The Buildout software

     We'll capitalize the word when we do this.

   - A particular use of Buildout, a directory having a Buildout
     configuration file.

     We'll use lower case to refer to these.

   - A ``buildout`` section in a Buildout configuration (in a
     particular buildout).

     We'll use a lowercase fixed-width font for these.

First steps
===========

The recommended way to install Buildout is to use pip within a virtual environment:

.. code-block:: console

  virtualenv mybuildout
  cd mybuildout
  bin/pip install zc.buildout



To use Buildout, you need to provide a Buildout configuration. Here is
a minimal configuration:

.. code-block:: ini

  [buildout]
  parts =

.. -> src

   >>> write(src, 'buildout.cfg')

By default, Buildout looks for a file named ``buildout.cfg`` to find its configuration.
The configuration hereabove is thus stored in ``buildout.cfg``.

A minimal (and useless) Buildout configuration has a ``buildout`` section
with a ``parts`` option.  If we run Buildout:

.. code-block:: console

  buildout

.. -> src

   >>> run_buildout(src)

   >>> import os
   >>> eqs(ls(), 'buildout.cfg', 'bin', 'eggs', 'develop-eggs', 'parts', 'out')

   >>> eqs(ls('bin'))
   >>> eqs(ls('develop-eggs'))
   >>> eqs(ls('parts'))

   TODO: fix upgrading so eggs is empty

   >>> nope('bobo' in ls('eggs'))

Four directories are created:

bin
  A directory to hold executables.

develop-eggs
  A directory to hold develop egg links. More about these later.

eggs
  A directory that hold installed packages in egg [#egg]_ format.

parts
  A directory that provides a default location for installed parts.

Buildout configuration files use an `INI syntax
<https://en.wikipedia.org/wiki/INI_file>`_ [#configparser]_.
Configuration is arranged in sections, beginning with section names in square
brackets. Section options are names, followed by equal signs, followed
by values.  Values may be continued over multiple lines as long as the
continuation lines start with whitespace.

Buildout is all about building things and the things to be built are
specified using *parts*.  The parts to be built are listed in the
``parts`` option.  For each part, there must be a section with the same
name that specifies the software to build the part and provides
parameters to control how the part is built.

Installing software
===================

In this tutorial, we're going to install a simple web server.
The details of the server aren't important.  It just provides a useful
example that illustrates a number of ways that Buildout can make
things easier.

We'll start by adding a part to install the server software.  We'll
update our Buildout configuration to add a ``bobo`` part:

.. code-block:: ini

  [buildout]
  parts = bobo

  [bobo]
  recipe = zc.recipe.egg
  eggs = bobo

.. -> src

   >>> write(src, 'buildout.cfg')

We added the part name, ``bobo`` to the ``parts`` option in the
``buildout`` section.  We also added a ``bobo`` section with two
options:

recipe
  The standard ``recipe`` option names the software component that
  will implement the part.  The value is a Python distribution
  requirement, as would be used with ``pip``.  In this case, we've
  specified `zc.recipe.egg
  <https://pypi.org/project/zc.recipe.egg/>`_ which is the name of
  a Python project that provides a number of recipe implementations.

eggs
  A list of distribution requirements, one per
  line. [#requirements-one-per-line]_ (The name of this option is
  unfortunate, because the values are requirements, not egg names.)
  Listed requirements are installed, along with their dependencies. In
  addition, any scripts provided by the listed requirements (but not
  their dependencies) are installed in the ``bin`` directory.

If we run this:

.. code-block:: console

  buildout

.. -> src

   >>> run_buildout(src)

Then a number of things will happen:

- ``zc.recipe.egg`` will be downloaded and installed in your ``eggs``
  directory.

- ``bobo`` and its dependencies will be downloaded and installed. (bobo
  is a small Python database server.)

  After this, the eggs directory will look something like:

  .. code-block:: console

    $ ls -l eggs
    total 0
    drwxr-xr-x  4 jim  staff  136 Feb 23 09:01 WebOb-1.7.1-py2.7.egg
    drwxr-xr-x  9 jim  staff  306 Feb 23 09:10 bobo-2.3.0-py2.7.egg

  .. bobo in eggs:

     >>> yup([n for n in ls('eggs') if n.startswith('bobo-2.3.0-')])

- A ``bobo`` script will be installed in the ``bin`` directory:

  .. code-block:: console

    $ ls -l bin
    total 8
    -rwxr-xr-x  1 jim  staff  391 Feb 23 09:10 bobo

  This script is used to `run a bobo server
  <http://bobo.readthedocs.io/en/latest/reference.html#the-bobo-server>`_.

.. Really?

   >>> yup('bobo' in ls('bin'))

Generating configuration and custom scripts
===========================================

The ``bobo`` program doesn't daemonize itself. Rather, it's meant to
be used with a dedicated daemonizer like `zdaemon
<https://pypi.org/project/zdaemon>`_ or `supervisord
<http://supervisord.org/>`_.  We'll use a `recipe to set up zdaemon
<https://pypi.org/project/zc.zdaemonrecipe>`_.  Our Buildout
configuration becomes:

.. code-block:: ini

  [buildout]
  parts = bobo server

  [bobo]
  recipe = zc.recipe.egg
  eggs = bobo

  [server]
  recipe = zc.zdaemonrecipe
  program =
    ${buildout:bin-directory}/bobo
      --static /=${buildout:directory}
      --port 8200

.. -> src

   >>> write(src, 'buildout.cfg')

Here we've added a new ``server`` part that uses ``zc.zdaemonrecipe``.
We used a ``program`` option to define what program should be run.
There are a couple of interesting things to note about this option:

- We used :doc:`variable substitutions
  <topics/variables-extending-and-substitutions>`:

  ``${buildout:directory}``
      Expands to the full path of the buildout directory.

  ``${buildout:bin-directory}``
      Expands to the full path of the buildout's ``bin`` directory.

  Variable substitution provides a way to access Buildout settings and
  share information between parts and avoid repetition.

  See the :doc:`reference <reference>` to see what buildout settings
  are available.

- We spread the program over multiple lines.  A configuration value
  can be spread over multiple lines as long as the continuation lines
  begin with whitespace.

  The interpretation of a value is up to the recipe that uses it. The
  ``zc.zdaemonrecipe`` recipe combines the program value into a single
  line.

If we run Buildout:

.. code-block:: console

  buildout

.. -> src

    >>> run_buildout(src)
    >>> print(read('bin/server')) # doctest: +ELLIPSIS
    #!...python...
    <BLANKLINE>
    import sys
    sys.path[0:0] = [
      '.../eggs/zdaemon...
    <BLANKLINE>
    import zdaemon.zdctl
    <BLANKLINE>
    if __name__ == '__main__':
        sys.exit(zdaemon.zdctl.main([
            '-C', '.../parts/server/zdaemon.conf',
            ]+sys.argv[1:]
            ))
    <BLANKLINE>

- The ``zc.zdaemonrecipe`` recipe will be downloaded and installed in
  the ``eggs`` directory.

- A ``server`` script is added to the ``bin`` directory.  This script
  is generated by the recipe.  It can be run like:

  .. code-block:: console

    bin/server start

  to start a server and:

  .. code-block:: console

    bin/server stop

  to stop it.  The script references a zdaemon configuration file
  generated by the recipe in ``parts/server/zdaemon.conf``.

- A zdaemon configuration script is generated in
  ``parts/server/zdaemon.conf`` that looks something like:

  .. code-block:: xml

    <runner>
      daemon on
      directory /Users/jim/t/0214/parts/server
      program /Users/jim/t/0214/bin/bobo --static /=/Users/jim/t/0214 --port 8200
      socket-name /Users/jim/t/0214/parts/server/zdaemon.sock
      transcript /Users/jim/t/0214/parts/server/transcript.log
    </runner>

    <eventlog>
      <logfile>
        path /Users/jim/t/0214/parts/server/transcript.log
      </logfile>
    </eventlog>

  .. -> expect

     >>> expect = expect.replace('/Users/jim/t/0214', os.getcwd()).strip()
     >>> eq(expect, read('parts/server/zdaemon.conf').strip())

  The **details aren't important**, other than the fact that the
  configuration file reflects part options and the actual buildout
  location.

Version control
===============

In this example, the only file that needs to be checked into version
control is the configuration file, ``buildout.cfg``.  Everything else
is generated.  Someone else could check out the project, and get the
same result [#if-same-environment]_.

More than just a package installer
==================================

The example shown above illustrates how Buildout is more than just a
package installer such as ``pip``. Using Buildout recipes, we can
install custom scripts and configuration files, and much more. For
example, we could use `configure and make
<https://pypi.org/project/zc.recipe.cmmi>`_ to install non-Python
software from source, we could run JavaScript builders, or do anything
else that can be automated with Python.

Buildout is a simple automation framework.  There are hundreds of
recipes to choose from [#finding-hundreds]_ and :doc:`writing new
recipes is easy <topics/writing-recipes>`.

Repeatability
=============

A major goal of Buildout is to provide repeatability.  But what does
this mean exactly?

  If two buildouts with the same configuration are built in the same
  environments at the same time, they should produce the same result,
  regardless of their build history.

That definition is rather dense. Let's look at the pieces:

Buildout environment
--------------------

A Buildout environment includes the operating system and the Python
installation Buildout is run with. The more a buildout depends on its
environment, the more variation is likely between builds.

If a Python installation is shared, packages installed by one
application affect other applications, including buildouts. This can
lead to unexpected errors.   This is why it's recommended to use a
`virtual environment <https://virtualenv.pypa.io/en/stable/>`_ or a
"clean python" built from source with no third-party packages
installed [#hypocritical]_.

To limit dependence on the operating system, people sometimes install
libraries or even database servers as Buildout parts.

Modern Linux container technology (e.g. `Docker
<https://www.docker.com/>`_) makes it a lot easier to control the
environment.  If you develop entirely with respect to a particular
container image, you can have repeatability with respect to that
image, which is usually good enough because the environment, defined
by the image, is itself repeatable and unshared with other
applications.

Python requirement versions
---------------------------

Another potential source of variation is the versions of Python
dependencies used.

Newest versions
_______________

If you don't specify versions, Buildout will always try to get the
most recent version of everything it installs.  This is a major reason
that Buildout can be slow. It checks for new versions every time it
runs.  It does this to satisfy the repeatability requirement above.
If it didn't do this, then an older buildout would likely have
different versions of Python packages than newer buildouts.

To speed things up, you can use the ``-N`` Buildout option to tell
Buildout to *not* check for newer versions of Python requirements:

.. code-block:: console

  buildout -N

.. -> src

   >>> run_buildout(src)

This relaxes repeatability, but with little risk if there was a recent
run without this option.

.. _pinned-versions:

Pinned versions
_______________

You can also pin required versions, and do so in two ways.  You can specify them
where you list them, as in:

.. code-block:: ini

  [bobo]
  recipe = zc.recipe.egg
  eggs = bobo <5.0

.. -> src

   >>> prefix = """
   ... [buildout]
   ... parts = bobo
   ... """
   >>> with open('buildout.cfg', 'w') as f:
   ...     _ = f.write(prefix)
   ...     _ = f.write(src)

   >>> import shutil
   >>> shutil.rmtree('eggs')
   >>> run_buildout('buildout show-picked-versions=true')
   >>> yup([n for n in ls('eggs') if n.startswith('bobo-2.3.0-')])
   >>> yup('bobo==2.3.0' in read('out'))

In this example, we've requested a version of bobo less than 5.0.

You can also add `environment markers <https://python.org/dev/peps/pep-0496>`_
to restrict some requirements to i.e. a certain platform or python version:

.. code-block:: ini

  [bobo]
  recipe = zc.recipe.egg
  eggs =
      bobo ==2.2.0; python_version < '3.0'
      bobo ==2.3.0; python_version >= '3.0'

.. -> src

The more common way to pin a version is using a ``versions`` section:

.. code-block:: ini

  [buildout]
  parts = bobo server

  [bobo]
  recipe = zc.recipe.egg
  eggs = bobo

  [server]
  recipe = zc.zdaemonrecipe
  program =
    ${buildout:bin-directory}/bobo
      --static /=${buildout:directory}
      --port 8200

  [versions]
  bobo = 2.3.0

.. -> src

   >>> write(src, 'buildout.cfg')
   >>> shutil.rmtree('eggs')
   >>> run_buildout('buildout show-picked-versions=true')
   >>> yup([n for n in ls('eggs') if n.startswith('bobo-2.3.0-')])
   >>> nope('bobo = 2.3.0' in read('out'))

Larger projects may need to pin many versions, so it's common to put
version requirements in their own file:

.. code-block:: ini

  [buildout]
  extends = versions.cfg
  parts = bobo server

  [bobo]
  recipe = zc.recipe.egg
  eggs = bobo

  [server]
  recipe = zc.zdaemonrecipe
  program =
    ${buildout:bin-directory}/bobo
      --static /=${buildout:directory}
      --port 8200

.. -> src

   >>> write(src, 'buildout.cfg')

Here, we've used the Buildout ``extends`` option to say that
configurations should be read from ``versions.cfg`` (it's
allowed to specify several files in ``extend``). Cconfigurations
should be read from the named file (or files) and the
configuration in the current file should override configuration in the
extended files.
To continue the example, our ``versions.cfg`` file
might look like:

.. code-block:: ini

  [versions]
  bobo = 2.3.0

.. -> versions_cfg

   >>> write(versions_cfg, 'versions.cfg')
   >>> shutil.rmtree('eggs')
   >>> run_buildout('buildout show-picked-versions=true')
   >>> yup([n for n in ls('eggs') if n.startswith('bobo-2.3.0-')])
   >>> nope('bobo = 2.3.0' in read('out'))

We can use the ``update-versions-file`` option to ask Buildout to
maintain our ``versions.cfg`` file for us:

.. code-block:: ini

  [buildout]
  extends = versions.cfg
  show-picked-versions = true
  update-versions-file = versions.cfg

  parts = bobo server

  [bobo]
  recipe = zc.recipe.egg
  eggs = bobo

  [server]
  recipe = zc.zdaemonrecipe
  program =
    ${buildout:bin-directory}/bobo
      --static /=${buildout:directory}
      --port 8200

.. -> src

   >>> write(src, 'buildout.cfg')
   >>> eq(versions_cfg, read('versions.cfg'))
   >>> run_buildout('buildout show-picked-versions=true')
   >>> yup([n for n in ls('eggs') if n.startswith('bobo-2.3.0-')])
   >>> yup('WebOb = ' in read('versions.cfg'))

With ``update-versions-file``, whenever Buildout gets the newest
version for a requirement (subject to requirement constraints), it
appends the version to the named file, along with a comment saying
when and why the requirement is installed.  If you later want to
upgrade a dependency, edi this file with the new version. Alternatively,
remove the entry altogether and Buildout will add a new entry the next
time it runs.

We also used the ``show-picked-versions`` to tell Buildout to tell us
when it got (picked) the newest version of a requirement.

When versions are pinned, Buildout doesn't look for new versions of
the requirements, which can speed buildouts quite a bit. In fact, The
``-N`` option doesn't provide any speedup for projects whose
requirement versions are all pinned.

When should you pin versions?
_____________________________

The rule of thumb is that you should pin versions for a whole system,
such as an application or service.  You do this because after
integration tests, you want to be sure that you can reproduce the
tested configuration.

You shouldn't pin versions for a component, such as a library, because
doing so inhibits the ability of users of your component to integrate it
with their dependencies, which may overlap with yours.  If you know
that your component only works for a specific range of versions of some dependency,
set the range in your project requirements. Don't require
specific versions.

.. _unpinning-versions:

Unpinning versions
__________________

You can unpin a version by just removing it (or commenting it out of)
your ``versions`` section.

You can also unpin a version by setting the version to an empty
string:

.. code-block:: ini

  [versions]
  ZEO =

In an extending configuration (``buildout.cfg`` in the example above), or
:ref:`on the buildout command line <unpinning-on-command-line>`.

You might do this if pins are shared between projects and you want to
unpin a requirement for one of the projects, or want to remove a pin
while using a requirement in :ref:`development mode
<python-development-projects>`.

Buildout versions and automatic upgrade
---------------------------------------

In the interest of repeatability, Buildout can upgrade itself or its
dependencies to use the newest versions or downgrade to respect pinned
versions.  This only happens if you run Buildout from a buildout's own
``bin`` directory.

We can use Buildout's ``bootstrap`` command to install a local
buildout script:

.. code-block:: console

  buildout bootstrap

.. -> src

   >>> nope('buildout' in ls('bin'))
   >>> run_buildout(src)
   >>> yup('buildout' in ls('bin'))

Then, if the installed script is used:

.. code-block:: console

  bin/buildout

.. -> src

   >>> yup(os.path.exists(src.strip()))

Then Buildout will upgrade or downgrade to be consistent with version
requirements.  See the :doc:`bootstrapping topic
<topics/bootstrapping>` to learn more about bootstrapping.

.. _python-development-projects:

Python development projects
===========================

A very common Buildout use case is to manage the development of a
library or main part of an application written in Python.  Buildout
facilitates this with the ``develop`` option:

.. code-block:: ini

   [buildout]
   develop = .
   ...

.. -> develop_snippet

The ``develop`` option takes one or more paths to project `setup.py
<https://docs.python.org/3.6/distutils/setupscript.html>`_ files or,
more commonly, directories containing them. Buildout then creates
"develop eggs" [#develop-eggs]_ for the corresponding projects.

With develop eggs, you can modify the sources and the modified sources
are reflected in future Python runs (or after `reloads
<https://docs.python.org/3/library/importlib.html#importlib.reload>`_).

For libraries that you plan to distribute using the Python packaging
infrastructure, You'll need to write a setup file, because it's needed
to generate a distribution.

If you're writing an application that won't be distributed as a
separate Python distribution, writing a setup script can feel
like overkill, but it's useful for:

- naming your project, so you can refer to it like any Python
  requirement in your Buildout configuration, and for

- specifying the requirements your application code uses, separate
  from requirements your buildout might have.

Fortunately, an application setup script can be minimal. Here's an
example::

  from setuptools import setup
  setup(name='main', py_modules='main', install_requires = ['bobo', 'six'])

.. -> src

   >>> write(src, 'setup.py')
   >>> write('pass', 'main.py')

We suggest copying and modifying the example above, using it as
boilerplate.  As is probably clear, the setup arguments used are:

name
   The name of your application. This is the name you'll use in
   Buildout configuration where you want to refer to application
   code.

install_requires
   A list of requirement strings for Python distributions your
   application depends on directly.

A *minimal* [#typical-dev-project]_ development Buildout configuration
for a project with a setup script like the one above might look
something like this:

.. code-block:: ini

   [buildout]
   develop = .
   parts = py

   [py]
   recipe = zc.recipe.egg
   eggs = main
   interpreter = py

.. -> src

   >>> eq(src.strip().split('\n')[:2], develop_snippet.strip().split('\n')[:2])
   >>> write(src, 'buildout.cfg')
   >>> run_buildout()
   >>> yup('Develop: ' in read('out'))

   >>> eq(os.getcwd(), read('develop-eggs/main.egg-link').split()[0])

There's a new option, ``interpreter``, which names an *interpreter*
script to be generated. An interpreter script [#interpreter-script]_
mimics a Python interpreter with its path set to include the
requirements specified in the eggs option and their (transitive)
dependencies.  We can run the interpreter:

.. code-block:: console

  bin/py

.. -> path

   >>> yup(os.getcwd() in read(path.strip()))

To get an interactive Python prompt, or you can run a script with it:

.. code-block:: console

  bin/py somescript.py

.. -> path

   >>> yup(os.path.exists(path.split()[0]))

If you need to work on multiple interdependent projects at the same
time, you can name multiple directories in the ``develop`` option,
typically pointing to multiple check outs.  A popular Buildout
extension, `mr.developer <https://pypi.org/project/mr.developer>`_,
automates this process.

Where to go from here?
======================

This depends on what you want to do. We suggest perusing the :doc:`topics
<topics/index>` based on your needs and interest.

The :doc:`reference <reference>` section can give you important
details, as well as let you know about features not touched on here.



.. [#egg] You may have heard bad things about eggs.  This stems in
   part from the way that eggs were applied to regular Python
   installs.  We think eggs, which were inspired by `jar files
   <https://en.wikipedia.org/wiki/JAR_(file_format)>`_, when used as
   an installation format, are a good fit for Buildout's goals.  Learn
   more in the topic on :ref:`Buildout and packaging
   <buildout_and_packaging>`.

.. [#configparser] Buildout uses a variation (fork) of the standard
   ``ConfigParser`` module and follows (mostly) the same parsing
   rules.

.. [#requirements-one-per-line] Requirements can have whitespace
   characters as in ``bobo <3``, so they're separated by newlines.

.. [#if-same-environment] This assumes the same environment and that
   dependencies haven't changed.  We'll explain further in the
   section on repeatability.

.. [#finding-hundreds] You can list Buildout-related software,
   consisting mostly of Buildout recipes, using the
   `Framework :: Buildout
   <https://pypi.org/search/?q=&o=&c=Framework+%3A%3A+Buildout>`_
   classifier search. These results miss recipes that don't provide
   classifier meta data.  Generally you can find a recipe for a task by
   searching the name of the task and the "recipe" in the `package
   index <https://pypi.org/>`_.

.. [#hypocritical] It's a little hypocritical to recommend installing
   Buildout into an otherwise clean environment, which is why Buildout
   provides a :doc:`bootstrapping mechanism <topics/bootstrapping>`
   which allows setting up a buildout without having to contaminate a
   virtual environment or clean Python install.)

.. [#develop-eggs] pip calls these `"editable" installs
   <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_.

.. [#typical-dev-project] A more typical development buildout will
   include at least a part to specify a test runner.  A development
   buildout might define other support parts, like JavaScript
   builders, database servers, development web-servers and
   so on.

.. [#interpreter-script] An interpreter script is similar to the
   ``bin/python`` program included in a virtual environment, except
   that it's lighter weight and has exactly the packages
   listed in the ``eggs`` option and their dependencies, plus whatever
   comes from the Python environment.
