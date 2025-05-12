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
