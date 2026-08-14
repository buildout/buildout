********************************
Buildout Egg-Installation Recipe
********************************

.. contents::

The egg-installation recipe installs eggs into a buildout eggs
directory.  It also generates scripts in a buildout bin directory with
egg paths baked into them.

The ``zc.recipe.egg`` code is linked closely to ``zc.buildout`` and is developed in the same git repository.
This means ``zc.recipe.egg`` is not tested with older ``zc.buildout`` versions.
So when there is a new ``zc.buildout`` major release, we make a new major release of ``zc.recipe.egg`` as well, requiring this new version.
Since version 6, we keep these major versions in sync for clarity:

* ``zc.recipe.egg`` 4.0.0 requires ``zc.buildout>=5.0.0``.
* We skip ``zc.recipe.egg`` 5.
* ``zc.recipe.egg`` 6.0.0a1 requires ``zc.buildout>=6.0.0a1``.
