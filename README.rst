********
Buildout
********

.. image:: https://secure.travis-ci.org/buildout/buildout.png?branch=master
   :width: 82px
   :height: 13px
   :alt: Travis CI build report
   :target: https://travis-ci.org/buildout/buildout

Buildout is a project designed to solve 2 problems:

1. Application-centric assembly and deployment

   *Assembly* runs the gamut from stitching together libraries to
   create a running program, to production deployment configuration of
   applications, and associated systems and tools (e.g. run-control
   scripts, cron jobs, logs, service registration, etc.).

   Buildout might be confused with build tools like make or ant, but
   it is a little higher level and might invoke systems like make or
   ant to get it's work done.

   Buildout might be confused with systems like puppet or chef, but it
   is more application focused.  Systems like puppet or chef might
   use buildout to get their work done.

   Buildout is also somewhat Python-centric, even though it can be
   used to assemble and deploy non-python applications.  It has some
   special features for assembling Python programs. It's scripted with
   Python, unlike, say puppet or chef, which are scripted with Ruby.

2. Repeatable assembly of programs from Python software distributions

   Buildout puts great effort toward making program assembly a highly
   repeatable process, whether in a very open-ended development mode,
   where dependency versions aren't locked down, or in a deployment
   environment where dependency versions are fully specified.  You
   should be able to check buildout into a VCS and later check it out.
   Two checkouts built at the same time in the same environment should
   always give the same result, regardless of their history.  Among
   other things, after a buildout, all dependencies should be at the
   most recent version consistent with any version specifications
   expressed in the buildout.

   Buildout supports applications consisting of multiple programs,
   with different programs in an application free to use different
   versions of Python distributions.  This is in contrast with a
   Python installation (real or virtual), where, for any given
   distribution, there can only be one installed.

To learn more about buildout, including how to use it, see
http://buildout.org/.

Installation
************

There are a number of ways to install buildout.  You can install it as
you would any other package, using pip or easy_install.  In this case,
you'll get a buildout command that you can use to build projects.  To
build a project, just use::

  buildout

from a project directory.

Buildout's (stubborn) philosophy, however, is that projects should be
self-contained, and not require changes to a shared Python
installation. To avoid changing a shared Python installation you can
download a bootstrap script that, when run, will install buildout
locally in your project.

The bootstrap script for buildout version 2 is at:

  http://downloads.buildout.org/2/bootstrap.py

So, for example, to install buildout 2 in a project, you might::

  wget http://downloads.buildout.org/2/bootstrap.py
  python bootstrap.py

Then to build your project, you can just run::

  bin/buildout

from the project directory.

The bootstrap script is often checked into version control.

buildout 2 is somewhat backward-incompatible with version 1.  Most
projects will probably work fine with either.  If you need to keep
using version 1, however, specify a version requirement when you use
pip or easy_install, or use the version 1 bootstrap script at:

  http://downloads.buildout.org/1/bootstrap.py
