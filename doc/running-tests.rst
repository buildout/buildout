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

By default, tests are run with Python 3.8::

   make test


To run tests with another version, use the ``PYTHON_VER`` environment
variable::

   PYTHON_VER=3.9 make test

We still support the following versions.

- 3.10
- 3.9
- 3.8
- 3.7
- 3.6
- 3.5
- 2.7
- (3.11)
