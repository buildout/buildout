=========================================
History, motivation, and Python packaging
=========================================

Isolation from environment
==========================

In the early 2000s, Zope Corporation was helping customers build
Zope-based applications.  A major difficulty was helping people deploy
the applications in their own environments, which varied not just
between customers, but also between customer machines. The customer
environments, including operating system versions, libraries and
Python modules installed were not well defined and subject to change
over time.

We realized that we needed to insulate ourselves from the customer
environments [#ultimately-not-enough]_ to have any chance of
predictable success.

We decided to provide our own Python builds into which we
installed the application.  These were automated with `make
<https://en.wikipedia.org/wiki/Make_(software)>`_.  Customers would
receive `tar <https://en.wikipedia.org/wiki/Tar_(computing)>`_ files,
expand them and run ``make``.  We referred to these as "build outs".

Python
======

Later, as the applications we were building became more complex, some
of us wanted to be able to use Python, rather than make, to automate
deployments.  In 2005, we created an internal prototype that used
builds defined using `ConfigParser-formatted configuration files
<https://docs.python.org/2/library/configparser.html>`_.  File
sections described things to be built and there were a few built-in
build recipes and eventually facilities for implementing custom
recipes.

By this time, we were hosting most of the applications we were
building, but we were still building Python and critical libraries
ourselves as part of deployment, to isolate ourselves from system
Python and library packages.

After several months of successful experience with the prototype, we
decided to build what became zc.buildout based on our experience,
making a recipe framework a main idea.

.. _buildout_and_packaging:

Buildout and packaging
======================

Around this time, `setuptools and easy_install
<https://en.wikipedia.org/wiki/Setuptools>`_ were released, providing
automated download and installation of Python packages *and their
dependencies*.  Because we built large applications, this was
something we'd wanted for some time and had even begun building a
package manager ourselves.  Part of the rationale for creating a new
Buildout version, beyond the initial prototype, was to take advantage of
the additional automation that setuptools promised.

Initially, we tried to leverage the ``easy_install`` command
[#easy_install_module]_, but the goals of ``easy_install`` and
Buildout were at odds.  ``easy_install`` sought to make it easy for
humans to install and upgrade packages manually, in an ad hoc manner.
While it installed dependencies, it didn't upgrade them.  It didn't
provide ways of managing an installation as a whole.  Buildout, on the
other hand, was all about automation and repeatability.

To achieve Buildout's goals, it was necessary to interact with
setuptools at a much lower level and to write quite a bit more
packaging logic than planned.

.. _eggs-label:

Eggs
----

Setuptools defined a packaging format, `eggs
<http://peak.telecommunity.com/DevCenter/PythonEggs>`_, used for
package distribution and installation.  Their design was based on Java
`jar files <https://en.wikipedia.org/wiki/JAR_(file_format)>`_, which
bundle software together with supporting resources, including
meta-data.

Eggs presented a number of challenges, and have a bad reputation as a
result:

- As an installation format:

  - They needed to be added to the Python path. The ``easy_install``
    command did this by generating complex `.pth files
    <https://docs.python.org/2/library/site.html>`_.  This often
    led to hard to diagnose bugs and frustration.

  - By default, eggs were installed as `zip files
    <https://en.wikipedia.org/wiki/Zip_(file_format)>`_.  Software
    development tools used by most Python developers
    [#java-loves-zip]_ made working with zip files difficult.  Also,
    importing from zip files was much slower on Unix-like systems.

- As a distribution format, eggs names carry insufficient meta data
  to distinguish incompatible builds of extensions on Linux.

-----------------------------------
Buildout uses eggs very differently
-----------------------------------

.. sidebar:: Script generation

   When Buildout generates a script, it's usually generating a wrapper
   script.  Python package distributions define scripts in two ways,
   via `entry points
   <https://setuptools.readthedocs.io/en/latest/setuptools.html#automatic-script-creation>`_,
   or as `scripts
   <https://docs.python.org/2/distutils/setupscript.html#installing-scripts>`_
   in a separate ``scripts`` area of the distribution.

   Entry points are meta data that define a main function to be run
   when a user invokes a generated script. Entry points make it easier
   to control how a script is run, including what version of Python is
   used and the Python path.  Initially, Buildout only supported
   installing entry-point-based scripts.

   The older way of packaging scripts is harder to deal with, because
   Buildout has to edit scripts to use the correct Python installation
   and to set the Python path.

Buildout doesn't use ``.pth`` files. Instead, when Buildout generates
a script, it generates a Python path that names the eggs needed, and
only the eggs needed, for a particular script based on its
requirements.  When Buildout is run, scripts are regenerated if
versions of any of their dependencies change.  Scripts defined by
different parts can use different versions, because they have
different Python paths. Changing a version used often requires only
updating the path generated for a script.

Buildout's approach to assembling applications should be familiar to
anyone who's worked with Java applications, which are assembled the
same way, using jars and class paths.

Buildout uses eggs almost exclusively as an **installation** format
[#unzipped]_, in a way that leverages eggs' strengths.  Eggs provide
Buildout with the ability to efficiently control which dependencies a
script uses, providing repeatability and predictability.

.. [#ultimately-not-enough] Ultimately, we moved to a model where we
   hosted software ourselves for customers, because we needed control
   over operation, as well as installation and upgrades, and because
   with the technology of the time, we still weren't able to
   sufficiently insulate ourselves from the customers' environments.

.. [#easy_install_module] The ``zc.buildout.easy_install`` module
   started out as a thin wrapper around the ``easy_install``
   command. Although it has (almost) nothing to do with the
   ``easy_install`` command today, its name has remained, because it
   provides some public APIs.

.. [#java-loves-zip] Java tools have no problem working with zip
   files, because of the prominence of jar files, which like eggs, use
   zip format.

.. [#unzipped] Buildout always unzips eggs into ordinary directories,
   by default.
