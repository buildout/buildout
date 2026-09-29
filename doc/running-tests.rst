Running the test suite
----------------------

Use the ``Makefile`` at the root of the repository.

Prerequisite
============

On Linux, you should have ``libffi`` installed.

For ubuntu, use::

   sudo apt-get install -y libffi-dev

Running tests
=============

By default, tests are run with Python 3 and whatever pip and setuptools versions are available::

   make test

You can speficy specific versions.
The help text explains this::

   $ make help
   ./prepare.sh --help
   Prepare a virtual environment for testing zc.buildout.

   Using:
   * Python: 3 (override with PYTHON_VERSION environment variable)
   * pip:  (override with PIP_VERSION environment variable)
   * setuptools:  (override with SETUPTOOLS_VERSION environment variable)

   An empty version means: use whatever is already available, or install latest.
   Extra arguments for pip install: -U (override with PIP_ARGS environment variable)

We support the following versions.

- 3.13
- 3.12
- 3.11
- 3.10
- 3.9

Iterating on Windows-only failures
==================================

The Windows CI leg cannot be reproduced on a Linux or macOS checkout.
Pushing a branch to trigger the full CI matrix on every attempt is
slow, so a fast iteration loop exists instead.

Push the tree under test to the scratch branch named
``windows-iter`` on a remote where GitHub Actions run::

   git push <remote> HEAD:windows-iter

That push runs only the static checks and the Windows leg; the full
matrix deliberately ignores the ``windows-iter`` branch. The scratch
ref is disposable. Overwrite it freely on the next attempt (prefix
the refspec with ``+``), and delete it when done. Since the workflow
file lives on the default branch, manual dispatch also works against
any branch::

   gh workflow run windows-iter.yml --ref <branch>
