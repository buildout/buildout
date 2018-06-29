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

Local bootstrapping using the ``bootstrap`` command
===================================================

You can use the :ref:`bootstrap command <bootstrap-command>` of a
``buildout`` script installed in your Python environment to boostrap
the buildout in the current directory:

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

.. _using-a-bootstrap-script:

Using a bootstrapping script
============================

If you download::

  https://bootstrap.pypa.io/bootstrap-buildout.py

.. -> url

And then run it:

.. code-block:: console

   python bootstrap-buildout.py

.. -> src

   >>> os.mkdir('fresh'); os.chdir('fresh')
   >>> eqs(os.listdir("."))
   >>> from six.moves.urllib import request
   >>> f = request.urlopen(url)
   >>> write(f.read().decode('ascii'), 'bootstrap-buildout.py')
   >>> f.close()
   >>> write("[buildout]\nparts=\n", 'buildout.cfg')
   >>> import subprocess, sys
   >>> src = src.replace('python', sys.executable).split()
   >>> p = subprocess.Popen(
   ...     src, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
   ...     env=dict(HOME='zzzzz'))
   >>> if p.wait():
   ...     print(p.stderr.read())
   >>> eqs(os.listdir("."), 'bootstrap-buildout.py',
   ...     'buildout.cfg', 'eggs', 'bin', 'develop-eggs', 'parts')
   >>> os.chdir('..')
   >>> p.stdout.close()
   >>> p.stderr.close()

It will download the software needed to run Buildout and install it in
the current directory.

This has been the traditional approach to bootstrapping Buildout.
It was the best approach for a long time because the ``pip`` and
``easy_install`` commands usually weren't available.  In the early
days, if ``easy_install`` was installed, it was likely to have an
incompatible version of setuptools, because Buildout and setuptools
were evolving rapidly, sometimes in lock step.

This approach fails from time to time, due to changes in setuptools or
`the package index <https://pypi.org/>`_ and has been a
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


This can be used with the bootstrapping script as well:

.. code-block:: console

   python bootstrap-buildout.py init

.. -> src

   >>> os.mkdir('fresh2'); os.chdir('fresh2')
   >>> eqs(os.listdir("."))
   >>> f = request.urlopen(url)
   >>> write(f.read().decode('ascii'), 'bootstrap-buildout.py')
   >>> f.close()
   >>> src = src.replace('python', sys.executable).split()
   >>> p = subprocess.Popen(
   ...     src, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
   ...     env=dict(HOME='zzzzz'))
   >>> if p.wait():
   ...     print(p.stderr.read())
   >>> eqs(os.listdir("."), 'bootstrap-buildout.py',
   ...     'buildout.cfg', 'eggs', 'bin', 'develop-eggs', 'parts')
   >>> p.stdout.close()
   >>> p.stderr.close()

This creates an empty Buildout configuration:

.. code-block:: ini

  [buildout]
  parts =

.. -> src

   >>> eq(src, read('buildout.cfg'))
   >>> os.chdir('..')
   >>> os.chdir('init')
   >>> eq(src, read('buildout.cfg'))
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
