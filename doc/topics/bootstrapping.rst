=============
Bootstrapping
=============

Bootstrapping a buildout gives its own ``buildout`` script,
independent of its Python environment. There are 2 reasons you might use this:

Enable automatic Buildout upgrade (or downgrade).
  If the ``buildout`` script is local to the buildout, then Buildout
  will check for newest versions of Buildout and its dependencies
  that are consistent with any version pins and install any that are
  different, in which case, it restarts to use the new versions.

  Doing automatic upgrades allows buildouts to be more independent of
  their environments and more repeatable.

  Using a local ``buildout`` script may be necessary for a project that
  pins the version of Buildout itself and the pinned version is
  different from the version in the Python environment.

Avoid modifying the python environment.
  From a philosophical point of view, Buildout has tried to be
  isolated from its environment, and requiring the Python environment
  to be modified, by installing Buildout, was inconsistent.

  Before `virtualenv <https://virtualenv.pypa.io/en/stable/>`_
  existed, it might not have been possible to modify the environment
  without building Python from source.

Installing from scratch
=======================

We recommend to install ``buildout`` via ``pip install`` inside a ``virtualenv``:

.. code-block:: console

  virtualenv my_buildout
  cd my_buildout
  bin/pip install zc.buildout


Local bootstrapping using the ``bootstrap`` command
===================================================

You can use the :ref:`bootstrap command <bootstrap-command>` of a
``buildout`` script installed in your Python environment to bootstrap
a new buildout in the current directory:

.. code-block:: console

  buildout bootstrap

.. -> src

   >>> import os
   >>> eqs(os.listdir("."))
   >>> write("[buildout]\nparts=\n", 'buildout.cfg')
   >>> run_buildout(src)
   >>> eqs(os.listdir("."),
   ...     'buildout.cfg', 'out', 'eggs', 'bin', 'develop-eggs', 'parts')


If you have any other buildouts that have local ``buildout`` scripts, you
can use their ``buildout`` scripts:

.. code-block:: console

  /path/to/some/buildout/bin/buildout bootstrap

In this case, the buildout being bootstrapped will have the same
Python environment as the buildout that was used to bootstrap it.

.. _init-generates-buildout.cfg:

Bootstrapping requires a ``buildout.cfg``, ``init`` creates one
==================================================================

Normally, when bootstrapping, the local directory must have a
``buildout.cfg`` file.

If you don't have one, you can use the :ref:`init command
<init-command>` instead:

.. code-block:: console

   buildout init

.. -> src

   >>> os.mkdir('init'); os.chdir('init')
   >>> eqs(os.listdir("."))
   >>> run_buildout(src)
   >>> eqs(os.listdir("."),
   ...     'buildout.cfg', 'out', 'eggs', 'bin', 'develop-eggs', 'parts')
   >>> os.chdir('..')

If you know you're going to use some packages, you can supply
requirements on the command line after ``init``:

.. code-block:: console

   buildout init bobo six

.. -> src

   >>> os.mkdir('init2'); os.chdir('init2')
   >>> eqs(os.listdir("."))
   >>> run_buildout(src)
   >>> eqs(os.listdir("."), '.installed.cfg',
   ...     'buildout.cfg', 'out', 'eggs', 'bin', 'develop-eggs', 'parts')

In which case it will generate and run a buildout that uses them.  The
command above would generate a buildout configuration file:

.. code-block:: ini

  [buildout]
  parts = py

  [py]
  recipe = zc.recipe.egg
  interpreter = py
  eggs =
    bobo
    six

.. -> src

   >>> eq(src, read('buildout.cfg'))
   >>> os.chdir('..')

This can provide an easy way to experiment with a package without
adding it to your Python environment or creating a virtualenv.
