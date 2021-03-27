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

When you're developing buildout itself, you need to know two things:

- Use a clean Python *without* setuptools installed.  Otherwise many tests
  will find your already-installed setuptools, leading to test differences
  when setuptools' presence is explicitly tested.

- Also the presence of ``~/.buildout/default.cfg`` may interfere with the
  tests so you may want to temporarily rename it so that it does not get in
  the way.

- Bootstrap with with ``python dev.py``.

- Run buildout with -U, to ignore user (default) settings which can interfere
  with using the development version

For your convenience we provide a Makefile to build various Python versions
in subdirectories of the buildout checkout. To use these and run the tests
with them do::

    make PYTHON_VER=2.7 build
    make PYTHON_VER=2.7 test

    make PYTHON_VER=3.9 build
    make PYTHON_VER=3.9 test

The actual Python compilation is only done once and then re-used. So on
subsequent builds, only the development buildout itself needs to be redone.


Releases: zc.buildout, zc.recipe.egg and bootstrap.py
=====================================================

Buildout consists of two Python packages that are released separately:
zc.buildout and zc.recipe.egg. zc.recipe.egg is changed much less often than
zc.buildout.

zc.buildout's setup.py and changelog is in the same directory as this
``DEVELOPERS.txt`` and the code is in ``src/zc/buildout``.

zc.recipe.egg, including setup.py and a separate changelog, is in the
``zc.recipe.egg_`` subdirectory.

When releasing, make sure you also build a (universal) wheel in addition to
the regular .tar.gz::

    $ python setup.py sdist bdist_wheel upload

You can also use zest.releaser to release it. If you've installed it as
``zest.releaser[recommended]`` it builds the wheel for you and uploads it via
https (via twine).


Roadmap
=======

Currently, there are two active branches:

- master (development branch for the upcoming version 3)
- 2.x (development branch for the current version 2)

Active feature development and bug fixes only happen on the **master** branch.


Supported Python Versions
=========================

We align the support of Python versions with
`Zope <https://www.zope.org/developer/roadmap.html>`_ and
`Plone <https://plone.org/download/release-schedule>`_ development.

This means, currently there are no plans to drop Python 2.7 support.


Licensing
=========

This project is licensed under the Zope Public License.
Unlike contributing to the Zope and Plone projects,
you do not need to sign a contributor agreement to contribute to **buildout**.
