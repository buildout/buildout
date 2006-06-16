Zope Buildout
=============

The Zope Buildout project provides support for creating applications,
especially Pyton applications.  It provides tools for assembling
applications from multiple parts, Python or otherwise.  An application
may actually contain multiple programs, processes, and configuration
settings.

Here's an example of such an application that we built with an earlier
prototype of the buildout system. We have a Zope application consisting of:

- Multiple Zope instances

- 4 ZEO servers

- An ldap server

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

The detailed documentation for the various parts of buildout can be
found in the following files:

bootstrap.txt 
   Describes how to use the bootstrapping script

buildout.txt
   Describes how to define and run buildouts.  It also describes how
   to write recipes.

recipes.txt
   Documents the few built-in recipes.
