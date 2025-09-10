********
Buildout
********

.. image:: https://github.com/buildout/buildout/actions/workflows/run-tests.yml/badge.svg
   :alt: GHA tests report
   :target: https://github.com/buildout/buildout/actions/workflows/run-tests.yml

Buildout is a project designed to solve 2 problems:

1. Application-centric assembly and deployment

   *Assembly* runs the gamut from stitching together libraries to
   create a running program, to production deployment configuration of
   applications, and associated systems and tools (e.g. run-control
   scripts, cron jobs, logs, service registration, etc.).

   Buildout might be confused with build tools like make or ant, but
   it is a little higher level and might invoke systems like make or
   ant to get its work done.

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
https://www.buildout.org/.


Native namespaces and breaking changes in 5.x
*********************************************

Summary: ``zc.buildout`` 5.x installs most distributions with pip, even editable installs (with some remarks).
It automatically uses native namespaces for all packages, except editable installs.
Eggs go to directory ``eggs/v5`` to avoid compatibility problems.

If a package name has a dot in it, it is a namespace package.
``zc.buildout`` has ``zc`` as namespace.
Namespaces can be implemented in three ways:
native namespaces (PEP 420, since Python 3.3), pkg_resources style (with ``__init__.py`` files that call ``pkg_resources.declare_namespace``) and pkgutil style (with ``__init__.py`` files that call ``pkgutil.extend_path``).

Native namespaces are the modern way to do it. They work better with pip and other modern tools.
The pkg_resources style depends on setuptools and is considered deprecated: setuptools is scheduled to drop support for it at the end of 2025, removing its foundational ``pkg_resources`` module.

Problems start when you have multiple packages in the same namespace, that use different implementations.
But it depends on what you use to install the packages.
In the following examples, we have two packages in the same namespace, say ``ns.native`` (using native namespaces) and ``ns.deprecated`` (using pkg_resources style).

* Make editable installs of both packages (``pip install -e`` or in buildout, ``develop =``):

  - This works neither in pip nor in buildout.
  - You can install the `horse-with-no-namespace <https://pypi.org/project/horse-with-no-namespace/>`_ package to get this working.

* Make a normal install of both packages:

  - This works fine in pip.
  - This fails in buildout 4.x.
  - This works fine in buildout 5.x.

* Make a normal install of one package and an editable install of the other:

  - This works fine in pip.
  - This fails in buildout 4.x.
  - This fails in buildout 5.x as well.  But again, you can use ``horse-with-no-namespace`` to get this working.

So the big difference between buildout 4.x and 5.x is that with 5.x you can mix namespace styles when you do normal installs.
This is possible due to the following major changes in 5.x:

* The ``zc.buildout`` package itself uses native namespaces now.
* ``zc.buildout`` 5.x installs most packages with pip, with only rare exceptions.
* The tests have mostly been changed to use wheels instead of eggs, so they more closely resemble real life.
* Buildout now automatically treats all namespace packages as having native namespaces.
  Previously, after we installed a ``pkg_resources-style`` namespace package with pip, the ``__init__.py`` files would be missing, so we would explicitly add them again.
  Now we no longer do this. In fact, in some cases these files *are* there after installation, and we explicitly *remove* them.
* This means that "eggs" created by this Buildout version are not compatible with eggs from a previous Buildout version, at least for namespace packages.
  So Buildout now stores the eggs in a sub directory: ``eggs/v5``.
  Or with abi tags for example: ``eggs/v5/cp313``.
  So it should be fine to keep using the same shared eggs cache, even if you are using different zc.buildout versions.
* Development eggs (editable installs) are now also installed by pip.
  Previously, zc.buildout would call ``python setup.py develop`` to install them, failing if there was no ``setup.py`` file.
  Now this file is no longer needed.
  Theoretically this means that you could develop a package that uses for example ``hatchling`` as build system.
  In practice this does not work yet, but the foundation is there.

The Plone project is a major user of buildout, although alternative installation methods are becoming more popular.
So what does this mean for Plone?

* Plone 6.1 and earlier will keep using ``zc.buildout`` 4.x and ``pkg_resources``-style namespaces
* Plone 6.2 will switch to ``zc.buildout`` 5.x.
* Plone 6.2 will temporarily use ``horse-with-no-namespace`` both when installed with ``pip`` and with ``zc.buildout``.
* This combination means that each package in Plone 6.2 can switch to native namespaces at its own pace.
  Previously, all packages in a namespace had to switch at the same time, and the tests would be broken until that happened.
* In your own projects on any Plone 6 version, you are free to use any buildout and setuptools version you want.
  If Buildout 5 works on your Plone 6.0 project, or Buildout 4 works on your Plone 6.2 project, that is fine.
