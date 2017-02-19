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

  Unfortunately, doing this requires :ref:`using a bootstrap script
  <using-a-bootstrap-script>`.

Local bootstrapping using the ``buildout`` subcommand
=====================================================

You can use the :ref:`bootstrap subcommand <bootstrap-subcommand>` of a
``buildout`` script installed in your Python environment to boostrap
the buildout in the current directory:

.. code-block:: console

  buildout bootstrap

If you have any other buildouts that have local ``buildout`` scripts, you
can use their ``buildout`` scripts:

.. code-block:: console

  /path/to/some/buildout/bin/buildout bootstrap

In this case, the buildout being bootstrapped will have the same
Python environment as the buildout that was used to bootstrap it.

.. _using-a-bootstrap-script:

Using a bootstrapping script
============================

If you download::

  https://bootstrap.pypa.io/bootstrap-buildout.py

And then run it:

.. code-block:: console

   python bootstrap-buildout.py

It will download the software needed to run Buildout and install it in
the current directory.

This has been the traditional approach to bootstrapping Buildout.
It was the best approach for a long time because the ``pip`` and
``easy_install`` commands usually weren't available.  In the early
days, if ``easy_install`` was installed, it was likely to have an
incompatible version of setuptools, because Buildout and setuptools
were evolving rapidly, sometimes in lock step.

This approach fails from time to time, due to changes in setuptools or
`the package index <https://pypi.python.org/pypi>`_ and has been a
source of breakage when automated systems depended on it.

It's also possible that this approach will stop being supported.
Buildout's bootstrapping script relies on setuptools' bootstrap
script, which was used to bootstrap ``easy_install``.  Now that pip is
ubiquitous, there's no reason to bootstrap ``easy_install`` and
setuptools' bootstrapping script exists solely to support Buildout.
At some point, that may become too much of a maintenance burden, and
there may not be Buildout volunteers motivated to create a new
bootstrapping solution.

.. _init-generates-buildout.cfg:

bootstrapping requires a ``buildout.cfg``, ``init`` creates one
==================================================================

Normally, when bootstrapping, the local directory must have a
``buildout.cfg`` file.

If you don't have one, you can use the :ref:`init subcommand
<init-subcommand>` instead:

.. code-block:: console

   buildout init

This can be used with the bootstrapping script as well:

.. code-block:: console

   python bootstrap-buildout.py init

This creates an empty Buildout configuration:

.. code-block:: ini

  [buildout]
  parts =

If you know you're going to use some packages, you can supply
requirements on the command line after ``init``:

.. code-block:: console

   buildout init ZODB six

In which case it will generate and run a buildout that uses them.  The
command above would generate a buildout configuration file:

.. code-block:: ini

  [buildout]
  parts = py

  [py]
  recipe = zc.recipe.egg
  interpreter = py
  eggs =
    ZODB
    six

This can provide an easy way to experiment with a package without
adding it to your Python environment or creating a virtualenv.

