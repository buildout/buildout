*************
Zope Buildout
*************

.. contents::

The Zope Buildout project provides support for creating applications,
especially Python applications.  It provides tools for assembling
applications from multiple parts, Python or otherwise.  An application
may actually contain multiple programs, processes, and configuration
settings.

Here's an example of such an application that we built with an earlier
prototype of the buildout system. We have a Zope application consisting of:

- Multiple Zope instances

- 4 ZEO servers

- An LDAP server

- Cache-invalidation and Mail delivery servers

- Dozens of add-on packages

- Multiple test runners

- Multiple deployment modes, including dev, stage, and prod, 
  with prod deployment over multiple servers

Parts installed include:

- Application software installs, including Zope, ZEO and LDAP
  software

- Add-on packages

- Bundles of configuration that define Zope, ZEO and LDAP instances

- Utility scripts such as test runners, server-control
  scripts, cron jobs.

This is all defined using configuration files and recipes, which are
software that build and installs parts based on configuration data.
The prototype system has minimal documentation and no tests and
has no egg support.  (It build on earlier make-based systems that had
no documentation or tests.)  

This project provides a non-prototype implementation of the ideas and
knowledge gained from earlier efforts and leverages setuptools to make
recipe management cleaner and to provide better Python package and
script management.

The word "buildout" refers to a description of a set of parts and the
software to create and assemble them.  It is often used informally to
refer to an installed system based on a buildout definition.  For
example, if we are creating an application named "Foo", then "the Foo
buildout" is the collection of configuration and application-specific
software that allows an instance of the application to be created.  We
may refer to such an instance of the application informally as "a Foo
buildout".  

I expect that, for many Zope packages, we'll arrange the package
projects in subversion as buildouts.  To work on the package, someone
will check the project out of Subversion and build it.  Building it
will assemble all of packages and programs needed to work on it.  For
example, a buildout for a project to provide a new security policy
will include the source of the policy and specifications to build the
application for working on it, including:

- a test runner

- a web server for running the user interface

- supporting packages

A buildout will typically contain a copy of bootstrap.py.  When
someone checks out the project, they'll run bootstrap.py, which will

- create support directories, like bin, eggs, and work, as needed,

- download and install the zc.buildout and setuptools eggs,

- run bin/build (created by installing zc.buildout) to build the
  application.

Buildouts are defined using configuration files.  These files are
based on the Python ConfigParser module with some variable-definition
and substitution extensions.  

Installation
************

There are two ways to install zc,buildout

1. Install it as an egg using `easy_install
   <http://peak.telecommunity.com/DevCenter/EasyInstall>`_ into a
   Python instaallation. Then just use the buildout script from your
   Python bin or Scripts directory.

2. Use the `bootstrap script
   <http://dev.zope.org/Buildout/bootstrap.py>`_ to install setuptools
   and the buildout software into your buildout.  Typically, you'll
   check the bootstrap script into your project so that, whenever you
   checkout your project, you can turn it into a buildout by just
   running the bootstrap script.

More information
****************

The detailed documentation for the various parts of buildout can be
found in the following files:

`buildout.txt <http://dev.zope.org/Buildout/buildout.html>`_
   Describes how to define and run buildouts.  It also describes how
   to write recipes.

`easy_install.txt <http://dev.zope.org/Buildout/easy_install.html>`_
   Describes an Python APIs for invoking easy_install for generation
   of scripts with paths baked into them.


Download
********

You can download zc.buildout and many buildout recipes from the
`Python Package Index <http://www.python.org/pypi>`_.

Recipes
*******

Existing recipes include:

`zc.recipe.egg <http://dev.zope.org/Buildout/egg.html>`_
   The egg recipe installes one or more eggs, with their
   dependencies.  It installs their console-script entry points with
   the needed eggs included in their paths.

`zc.recipe.testrunner <http://dev.zope.org/Buildout/testrunner.html>`_
   The testrunner egg installs creates a test runner script for one or
   more eggs.

`zc.recipe.zope3checkout <http://dev.zope.org/Buildout/zope3checkout.html>`_
   The zope3checkout recipe installs a Zope 3 checkout into a
   buildout.

`zc.recipe.zope3instance <http://dev.zope.org/Buildout/zope3instance.html>`_
   The zope3instance recipe sets up a Zope 3 instance.

`zc.recipe.filestorage <http://dev.zope.org/Buildout/filestorage.html>`_
   The filestorage recipe sets up a ZODB file storage for use in a
   Zope 3 instance creayed by the zope3instance recipe.

Buildout examples
*****************

Some simple buildout examples:

`The zc.buildout project <http://svn.zope.org/zc.buildout/trunk>`_
   This is the project for the buildout software itself, which is
   developed as a buildout. 

`The zc sharing project <http://svn.zope.org/zc.sharing/trunk>`_
   This project illistrates using the buildout software with Zope 3.
   Note that the bootstrap.py file is checked in so that a buildout
   can be made when the project is checked out.  The buildout.cfg
   specified everything needed to create a Zope 3 installation with
   the zc.sharing package installed in development mode.

Questions and Bug Reporting
***************************

Please send questions and comments to the  
`distutils SIG mailing list <mailto://distutils-sig@python.org>`_.

Report bugs using the `zc.buildout Launchpad Bug Tracker
<https://launchpad.net/products/zc.buildout/+bugs>`_.

