================================
Buildout Egg-Installation Recipe
================================

.. contents::

The egg-installation recipe installes eggs into a buildout eggs
directory.  It also generates scripts in a buildout bin directory with 
egg paths baked into them.

The recipe provides the following options:

eggs
    A list of eggs to install given as one ore more setuptools
    requirement strings.  Each string must be given on a separate
    line.

find-links
    One or more addresses of link servers to be searched for
    distributions.  This is optional.  If not specified, links
    specified in the buildout section will be used, if any.

index
    The optional address of a distribution index server.  If not
    specified, then the option from the buildout section will be
    used.  If not specified in the part data or in the buildout
    section, then http://www.python.org/pypi is used.

python
    The name of a section defining the Python executable to use.
    This defaults to buildout.

scripts
   Control which scripts are generated.  The value should be a list of
   zero or more tokens.  Each token is either a name, or a name
   followed by an '=' and a new name.  Only the named scripts are
   generated.  If no tokens are given, then script generation is
   disabled.  If the option isn't given at all, then all scripts
   defined by the named eggs will be generated.

entry-points
   A list of entry-point identifiers of the form name=module#attrs,
   name is a script name, module is a module name, and a attrs is a
   (possibly dotted) name of an object wihin the module.  This option
   is useful when working with distributions that don't declare entry
   points, such as distributions not written to work with setuptools.

interpreter
   The name of a script to generate that allows access to a Python
   interpreter that has the path set based on the eggs installed.

extra-paths
   Extra paths to include in a generates script.

Custom eggs
-----------

The zc.recipe.egg:custom recipe supports building custom eggs,
currently with specialized options for building extensions.

extra-paths
   Extra paths to include in a generates script.

To do
-----

- Some way to freeze the egg-versions used.  This includes some way to
  record which versions were selected dynamially and then a way to
  require that the recorded versions be used in a later run.

- More control over script generation.  In particular, some way to 
  specify data to be recored in the script.

Change History
==============

1.0.0a3
-------

Extra path elements to be included in generated scripts can now be set
via the extra-paths option. 

No longer implicitly generate py_ scripts fo reach egg. There is now
an interpreter option to generate a script that, when run without
arguments, launches the Python interactive interpreter with the path
set based on a parts eggs and extra paths.  If this script is run with
the name of a Python script and arguments, then the given script is
run with the path set.

You can now specify explicit entry points.  This is useful for use
with packages that don't declare their own entry points.

1.0.0a2
-------

Added a new recipe for building custom eggs from source distributions,
specifying custom distutils build_ext options.

1.0.0a3
-------

- Added Windows support.

- Now-longer implicitly generate "py_" scripts for each egg.  You can
  now generate a script for launching a Python interpreter or for
  running scripts based on the eggs defined for an egg part.

- You can now specify custom entry points for packages that don't
  declare their entry points.

- You can now specify extra-paths to be included in generated scripts.


1.0.0a2
-------

Added a custom recipe for building custom eggs using custom distrutils
build_ext arguments.

1.0.0a1
-------

Initial public version
