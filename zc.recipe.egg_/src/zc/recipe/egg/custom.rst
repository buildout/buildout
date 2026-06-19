Creating eggs with extensions needing custom build settings
=============================================================

**Warning**: this section used to contain some tests that were broken since setuptools 49.6.0.
It is not clear what this means for how well custom egg creation still works.
But the remaining tests pass.

Sometimes, it's necessary to provide extra control over how an egg is
created.  This is commonly true for eggs with extension modules that
need to access libraries or include files.

The zc.recipe.egg:custom recipe can be used to define an egg with
custom build parameters.  The currently defined parameters are:

include-dirs
   A new-line separated list of directories to search for include
   files.

library-dirs
   A new-line separated list of directories to search for libraries
   to link with.

rpath
   A new-line separated list of directories to search for dynamic libraries
   at run time.

define
   A comma-separated list of names of C preprocessor variables to
   define.

undef
   A comma-separated list of names of C preprocessor variables to
   undefine.

libraries
   The name of an additional library to link with.  Due to limitations
   in distutils and despite the option name, only a single library
   can be specified.

link-objects
   The name of an link object to link against.  Due to limitations
   in distutils and despite the option name, only a single link object
   can be specified.

debug
   Compile/link with debugging information

force
   Forcibly build everything (ignore file timestamps)

compiler
   Specify the compiler type

swig
   The path to the swig executable

swig-cpp
   Make SWIG create C++ files (default is C)

swig-opts
   List of SWIG command line options

In addition, the following options can be used to specify the egg:

egg
    An specification for the egg to be created, to install given as a
    setuptools requirement string.  This defaults to the part name.

find-links
   A list of URLs, files, or directories to search for distributions.

index
   The URL of an index server, or almost any other valid URL. :)

   If not specified, the Python Package Index,
   https://pypi.org/simple/, is used.  You can specify an
   alternate index with this option.  If you use the links option and
   if the links point to the needed distributions, then the index can
   be anything and will be largely ignored.  In the examples, here,
   we'll just point to an empty directory on our link server.  This
   will make our examples run a little bit faster.

environment
   The name of a section with additional environment variables. The
   environment variables are set before the egg is built.

To illustrate this, we'll define a buildout that builds an egg for a
package that has a simple extension module::

  #include <Python.h>
  #include <extdemo.h>

  static PyMethodDef methods[] = {};

  PyMODINIT_FUNC
  initextdemo(void)
  {
      PyObject *m;
      m = Py_InitModule3("extdemo", methods, "");
  #ifdef TWO
      PyModule_AddObject(m, "val", PyInt_FromLong(2));
  #else
      PyModule_AddObject(m, "val", PyInt_FromLong(EXTDEMO));
  #endif
  }

The extension depends on a system-dependent include file, extdemo.h,
that defines a constant, EXTDEMO, that is exposed by the extension.

The extension module is available as a source distribution,
extdemo-1.4.tar.gz, on a distribution server.

We have a sample buildout that we'll add an include directory to with
the necessary include file:

    >>> mkdir('include')
    >>> write('include', 'extdemo.h',
    ... """
    ... #define EXTDEMO 42
    ... """)

We'll also update the buildout configuration file to define a part for
the egg:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... parts = extdemo
    ...
    ... [extdemo]
    ... recipe = zc.recipe.egg:custom
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... include-dirs = include
    ...
    ... """ % dict(server=link_server))

    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Installing extdemo...

The egg is created in the develop-eggs directory *not* the eggs
directory because it depends on buildout-specific parameters and the
eggs directory can be shared across multiple buildouts.

    >>> ls(sample_buildout, 'develop-eggs')
    d  extdemo-1.4-py2.4-unix-i686.egg
    -  zc.recipe.egg.egg-link

Note that no scripts or dependencies are installed.  To install
dependencies or scripts for a custom egg, define another part and use
the zc.recipe.egg recipe, listing the custom egg as one of the eggs to
be installed.  The zc.recipe.egg recipe will use the installed egg.

Let's define a script that uses our ext demo:

    >>> mkdir('demo')
    >>> write('demo', 'demo.py',
    ... """
    ... import extdemo, sys
    ... def print_(*args):
    ...     sys.stdout.write(' '.join(map(str, args)) + '\\n')
    ... def main():
    ...     print_(extdemo.val)
    ... """)

    >>> write('demo', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='demo')
    ... """)

    >>> write('broken_buildout.cfg',
    ... """
    ... [buildout]
    ... develop = demo
    ... parts = extdemo demo
    ...
    ... [extdemo]
    ... recipe = zc.recipe.egg:custom
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... include-dirs = include
    ...
    ... [demo]
    ... recipe = zc.recipe.egg
    ... eggs = demo
    ...        extdemo
    ... entry-points = demo=demo:main
    ... """ % dict(server=link_server))

Calling buildout with the above config fails since setuptools 49.6.0, due to this change:
https://github.com/pypa/setuptools/pull/2153
Problem is that our egg in the develop-eggs directory is no longer recognised as an egg,
because it has no EGG-INFO directory with a PKG_INFO file inside.
Instead, it has these files, depending on your Python version and machine:

* ``extdemo.cpython-310-darwin.so``
* ``extdemo-1.4-py3.10-macosx-14.7-x86_64.dist-info``

So either our custom egg generation has never worked, or our test setup needs adapting.
But I sometimes see such a dist-info directory instead of an EGG-INFO in normal usage (no custom eggs) as well,
highly dependent on the Python, Buildout, and setuptools versions.  So maybe that is fine.

We could patch ``pkg_resources._is_unpacked_egg(path)`` to:  ``return path.lower().endswith('.egg')``.
Then the tests here actually pass.  But that is unlikely to be a good idea.
``pkg_resources.find_on_path`` calls ``_is_unpacked_egg``, and if this returns true,
the code tries using the ``EGG-INFO`` directory, which will give an error because it does not exist.

So: in the rest of this section, some tests have been removed.
The remaining ones pass though.

Updating
--------

The custom recipe will normally check for new source distributions
that meet the given specification.  This can be suppressed using the
buildout non-newest and offline modes.  We'll generate a new source
distribution for extdemo:

    >>> update_extdemo()

If we run the buildout in non-newest or offline modes:

    >>> print_(system(buildout+' -N'), end='')
    Updating extdemo.

    >>> print_(system(buildout+' -o'), end='')
    Updating extdemo.

We won't get an update.

    >>> ls(sample_buildout, 'develop-eggs')
    d  extdemo-1.4-py2.4-unix-i686.egg
    -  zc.recipe.egg.egg-link

But if we run the buildout in the default on-line and newest modes, we
will.

    >>> print_(system(buildout), end='')
    Updating extdemo.

    >>> ls(sample_buildout, 'develop-eggs')
    d  extdemo-1.4-py2.4-linux-i686.egg
    d  extdemo-1.5-py2.4-linux-i686.egg
    -  zc.recipe.egg.egg-link


Controlling environment variables
+++++++++++++++++++++++++++++++++

To set additional environment variables, the `environment` option is used.

Let's create a recipe which prints out environment variables. We need this to
make sure the set environment variables are removed after the egg:custom
recipe was run.

    >>> mkdir(sample_buildout, 'recipes')
    >>> write(sample_buildout, 'recipes', 'environ.py',
    ... """
    ... import logging, os, zc.buildout
    ...
    ... class Environ:
    ...
    ...     def __init__(self, buildout, name, options):
    ...         self.name = name
    ...
    ...     def install(self):
    ...         logging.getLogger(self.name).info(
    ...             'test_environment_variable left over: %s' % (
    ...                 'test_environment_variable' in os.environ))
    ...         return []
    ...
    ...     def update(self):
    ...         self.install()
    ... """)
    >>> write(sample_buildout, 'recipes', 'setup.py',
    ... """
    ... from setuptools import setup
    ...
    ... setup(
    ...     name = "recipes",
    ...     entry_points = {'zc.buildout': ['environ = environ:Environ']},
    ...     )
    ... """)


Create our buildout:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = recipes
    ... parts = extdemo checkenv
    ...
    ... [extdemo-env]
    ... test_environment_variable = foo
    ...
    ... [extdemo]
    ... recipe = zc.recipe.egg:custom
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... include-dirs = include
    ... environment = extdemo-env
    ...
    ... [checkenv]
    ... recipe = recipes:environ
    ...
    ... """ % dict(server=link_server))
    >>> print_(system(buildout+' -vvv'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'wheel', 'pip', 'setuptools'.
    ...
    Develop: '/sample-buildout/recipes'
    Making editable install of /sample-buildout/recipes
    Running pip install:
    ...
    Uninstalling extdemo.
    ...
    Installing extdemo.
    ...Have environment test_environment_variable: foo
    ...
    Installing checkenv.
    ...

The setup.py also printed out that we have set the environment `test_environment_variable`
to foo. After the buildout the variable is reset to its original value (i.e.
removed).

When an environment variable has a value before zc.recipe.egg:custom is run,
the original value will be restored:

    >>> import os
    >>> os.environ['test_environment_variable'] = 'bar'
    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Updating extdemo.
    Updating checkenv.
    checkenv: test_environment_variable left over: True

    >>> os.environ['test_environment_variable']
    'bar'


Sometimes it is required to prepend or append to an existing environment
variable, for instance for adding something to the PATH. Therefore all variables
are interpolated with os.environ before the're set:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = recipes
    ... parts = extdemo checkenv
    ...
    ... [extdemo-env]
    ... test_environment_variable = foo:%%(test_environment_variable)s
    ...
    ... [extdemo]
    ... recipe = zc.recipe.egg:custom
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... include-dirs = include
    ... environment = extdemo-env
    ...
    ... [checkenv]
    ... recipe = recipes:environ
    ...
    ... """ % dict(server=link_server))
    >>> print_(system(buildout+' -vvv'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'wheel', 'pip', 'setuptools'.
    ...
    Develop: '/sample-buildout/recipes'
    Making editable install of /sample-buildout/recipes
    Running pip install:
    ...
    Uninstalling extdemo.
    ...
    Installing extdemo.
    ...Have environment test_environment_variable: foo:bar
    ...
    Updating checkenv.
    ...

    >>> os.environ['test_environment_variable']
    'bar'
    >>> del os.environ['test_environment_variable']


Create a clean buildout.cfg w/o the checkenv recipe, and delete the recipe:

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... develop = recipes
    ... parts = extdemo
    ...
    ... [extdemo]
    ... recipe = zc.recipe.egg:custom
    ... find-links = %(server)s
    ... index = %(server)s/index
    ... include-dirs = include
    ...
    ... """ % dict(server=link_server))
    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Develop: '/sample-buildout/recipes'
    Uninstalling checkenv.
    Uninstalling extdemo.
    Installing extdemo...

    >>> rmdir(sample_buildout, 'recipes')


Controlling develop-egg generation
==================================

If you want to provide custom build options for a develop egg, you can
use the develop recipe.  The recipe has the following options:

setup
   The path to a setup script or directory containing a startup
   script. This is required.

include-dirs
   A new-line separated list of directories to search for include
   files.

library-dirs
   A new-line separated list of directories to search for libraries
   to link with.

rpath
   A new-line separated list of directories to search for dynamic libraries
   at run time.

define
   A comma-separated list of names of C preprocessor variables to
   define.

undef
   A comma-separated list of names of C preprocessor variables to
   undefine.

libraries
   The name of an additional library to link with.  Due to limitations
   in distutils and despite the option name, only a single library
   can be specified.

link-objects
   The name of an link object to link against.  Due to limitations
   in distutils and despite the option name, only a single link object
   can be specified.

debug
   Compile/link with debugging information

force
   Forcibly build everything (ignore file timestamps)

compiler
   Specify the compiler type

swig
   The path to the swig executable

swig-cpp
   Make SWIG create C++ files (default is C)

swig-opts
   List of SWIG command line options

To illustrate this, we'll use a directory containing the extdemo
example from the earlier section.
Depending on which setuptools version you use, there may be different files or directories in there.
We will check that the most important ones are there:

    >>> "extdemo.c" in os.listdir(extdemo)
    True
    >>> "setup.py" in os.listdir(extdemo)
    True

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... parts = extdemo
    ...
    ... [extdemo]
    ... setup = %(extdemo)s
    ... recipe = zc.recipe.egg:develop
    ... include-dirs = include
    ... define = TWO
    ... """ % dict(extdemo=extdemo))

Note that we added a define option to cause the preprocessor variable
TWO to be defined.  This will cause the module-variable, 'val', to be
set with a value of 2.

    >>> print_(system(buildout), end='')
    Uninstalling extdemo.
    Installing extdemo.

Our develop-eggs now includes an egg link for extdemo:

    >>> ls('develop-eggs')
    -  extdemo.egg-link
    -  zc.recipe.egg.egg-link

and the extdemo now has a built extension:

    >>> contents = os.listdir(extdemo)
    >>> bool([f for f in contents if f.endswith('.so') or f.endswith('.pyd')])
    True
