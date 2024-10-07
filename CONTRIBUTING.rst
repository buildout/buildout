How To Contribute
*****************

Thank you for considering contributing to ``buildout``!


Workflow
========

- No contribution is too small!
- Please make sure to create one pull request for one change.
- Please try to add tests for your code.
- Make sure your changes pass **continuous integration**.
When CI fails, please try to fix it or ask for help.


Developing buildout itself and running the test suite
=====================================================

When you're developing buildout itself, you need to know a few things:

- The presence of ``~/.buildout/default.cfg`` may interfere with the tests.
  If you suspect this, you may want to temporarily rename it so that it does
  not get in the way.

- Similarly, if you manually run ``bin/buildout`` you can run it with ``-U``.
  This ignores user (default) settings which can interfere with using the
  development version.

For your convenience we provide a Makefile to create a Python virtual
environment in the ``venvs`` subdirectory of the buildout checkout.
You can have several venvs next to each other, but easiest is to use only one:
the venvs are quick to recreate.

To start, simply run ``make``.
This uses ``python3``, so you get a venv with whatever your default ``python3`` version is.

* It creates a venv named after this Python, for example ``venvs/python3.10``.
* This has our dependencies: ``pip``, ``setuptools``, ``wheel``, ``packaging``.
  Plus ``build``, which may become a dependency, and that we need for the next step.
* Using this venv, it creates a ``bin/buildout`` script in the main repository directory.
* It then calls ``bin/buildout`` and this creates a ``bin/test`` script.
* Then it calls ``bin/test`` to run the tests.

You can call ``make clean`` to remove everything that was created.

You can use environment variables to influence used versions:

* Python, for example: ``PYTHON_VERSION=3.12``
* pip, for example: ``PIP_VERSION=24.2``
* setuptools, for example: ``SETUPTOOLS_VERSION=70.0.0``
* Use ``PIP_ARGS`` for extra arguments.
  The default is ``PIP_ARGS=-U``, so upgrade packages to the latest available version.

So you can use this on the command line::

    PYTHON_VERSION=3.12 PIP_VERSION=24.2 SETUPTOOLS_VERSION=70.0.0 make


Releases: zc.buildout, zc.recipe.egg
====================================

Buildout consists of two Python packages that are released separately:
zc.buildout and zc.recipe.egg. zc.recipe.egg is changed much less often than
zc.buildout.

zc.buildout's setup.py and changelog is in the same directory as this
``CONTRIBUTING.txt`` and the code is in ``src/zc/buildout``.

zc.recipe.egg, including setup.py and a separate changelog, is in the
``zc.recipe.egg_`` subdirectory.

When releasing, make sure you also build a (universal) wheel in addition to
the regular .tar.gz::

    $ ./venvs/python3.10/bin/python -m build .

You can also use zest.releaser to release it. If you've installed it as
``zest.releaser[recommended]`` it builds the wheel for you and uploads using ``twine``.


Roadmap
=======

Currently, there are two active branches:

- master (development branch for the upcoming version 4)
- 3.x (development branch for the current version 3)

Active feature development and bug fixes only happen on the **master** branch.


Supported Python Versions
=========================

We align the support of Python versions with
`Zope <https://www.zope.dev/releases.html>`_ and
`Plone <https://plone.org/download/release-schedule>`_ development.

This means, the upcoming version 4 will support Python 3.8-3.13.
If you need support for Python 2.7 or older Python 3 versions, use version 3.


Licensing
=========

This project is licensed under the Zope Public License.
Unlike contributing to the Zope and Plone projects,
you do not need to sign a contributor agreement to contribute to **buildout**.
