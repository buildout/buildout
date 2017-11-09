Working set caching
===================

Working sets are cached, to improve speed on buildouts with multiple similar
parts based on ``zc.recipe.egg``.

The egg-recipe instance's ``_working_set`` helper method is used to make
the caching easier. It does the same job as ``working_set()`` but with some
differences:

- The signature is different: all information needed to build the working set
  is passed as parameters.
- The return value is simpler: only an instance of ``pkg_resources.WorkingSet``
  is returned.

Here's an example:

    >>> from zc.buildout import testing
    >>> from zc.recipe.egg.egg import Eggs
    >>> import os
    >>> import pkg_resources
    >>> recipe = Eggs(buildout=testing.Buildout(), name='fake-part', options={})
    >>> eggs_dir = os.path.join(sample_buildout, 'eggs')
    >>> develop_eggs_dir = os.path.join(sample_buildout, 'develop-eggs')
    >>> testing.install_develop('zc.recipe.egg', develop_eggs_dir)
    >>> ws = recipe._working_set(
    ...     distributions=['zc.recipe.egg', 'demo<0.3'],
    ...     eggs_dir=eggs_dir,
    ...     develop_eggs_dir=develop_eggs_dir,
    ...     index=link_server,
    ... )
    Getting...
    >>> isinstance(ws, pkg_resources.WorkingSet)
    True
    >>> sorted(dist.project_name for dist in ws)
    ['demo', 'demoneeded', 'setuptools', 'zc.buildout', 'zc.recipe.egg']

We'll monkey patch a method in the ``easy_install`` module in order to verify if
the cache is working:

    >>> import zc.buildout.easy_install
    >>> old_install = zc.buildout.easy_install.Installer.install
    >>> def new_install(*args, **kwargs):
    ...     print('Building working set.')
    ...     return old_install(*args, **kwargs)
    >>> zc.buildout.easy_install.Installer.install = new_install

Now we check if the caching is working by verifying if the same working set is
built only once.

    >>> ws_args_1 = dict(
    ...     distributions=['demo>=0.1'],
    ...     eggs_dir=eggs_dir,
    ...     develop_eggs_dir=develop_eggs_dir,
    ...     offline=True,
    ... )
    >>> ws_args_2 = dict(ws_args_1)
    >>> ws_args_2['distributions'] = ['demoneeded']
    >>> recipe._working_set(**ws_args_1)
    Building working set.
    <pkg_resources.WorkingSet object at ...>
    >>> recipe._working_set(**ws_args_1)
    <pkg_resources.WorkingSet object at ...>
    >>> recipe._working_set(**ws_args_2)
    Building working set.
    <pkg_resources.WorkingSet object at ...>
    >>> recipe._working_set(**ws_args_1)
    <pkg_resources.WorkingSet object at ...>
    >>> recipe._working_set(**ws_args_2)
    <pkg_resources.WorkingSet object at ...>

Undo monkey patch:

    >>> zc.buildout.easy_install.Installer.install = old_install

Since ``pkg_resources.WorkingSet`` instances are mutable, we must ensure that
``working_set()`` always returns a pristine copy. Otherwise callers would be
able to modify instances inside the cache.

Let's create a working set:

    >>> ws = recipe._working_set(**ws_args_1)
    >>> sorted(dist.project_name for dist in ws)
    ['demo', 'demoneeded']

Now we add a distribution to it:

    >>> dist = pkg_resources.get_distribution('zc.recipe.egg')
    >>> ws.add(dist)
    >>> sorted(dist.project_name for dist in ws)
    ['demo', 'demoneeded', 'zc.recipe.egg']

Let's call the working_set function again and see if the result remains valid:

    >>> ws = recipe._working_set(**ws_args_1)
    >>> sorted(dist.project_name for dist in ws)
    ['demo', 'demoneeded']
