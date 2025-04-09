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
