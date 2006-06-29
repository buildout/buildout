Test-Runner Recipe
==================

This recipe generates zope.testing test-runenr scripts for testing a
collection of eggs.  The eggs must already be installed (using the
zc.recipe.egg recipe)

The test-runner recipe has 2 options:

- The eggs option takes the names of the eggs to be
  tested.  These are not installed by the recipe. They must be
  installed by some other recipe (or using the buildout develop
  option).  The distributions are in the form os setuptools
  requirements.  Multiple distributions must be listed on separate
  lines. This option is required.

- The script option gives the name of the script to generate, in the
  buildout bin directory.  Of the option isn't used, the part name
  will be used.


To do
-----

- Don't require eggs to be installed by the egg recipe.  Go ahead
  and try to install them.

- Let the egg recipe do more of the heavy lifting internally.

- Support specifying testrunner defaults (e.g. verbosity, test file 
  patterns, etc.)

