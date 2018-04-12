========================
Writing Buildout recipes
========================

There are two kinds of buildout recipes: *install* and
*uninstall*. Install recipes are by far the most common.  Uninstall
recipes are very rarely needed because most install recipes add files and
directories that can be removed by Buildout.

Install recipes
===============

Install recipes are typically implemented with classes and have 3
important parts:

- A constructor (typically, ``__init__``) initializes a recipe object.

  The constructor plays a very important role, because it may update
  the configuration data it's passed, making information available to
  other parts and controlling whether a part will need to be
  re-installed.

  The constructor performs the first of two phases of recipe work, the
  second phase being the responsibility of either the ``install`` or
  ``update`` methods.

- The ``install`` method installs new parts.

- The ``update`` method updates previously installed parts.  It's
  often an empty method or an alias for ``install``.

Buildout phases
---------------

When buildout is run using the default :ref:`install command
<install-command>`, parts are installed in several phases:

1. Parts are initialized by calling their recipe constructors.  This may
   cause part configuration options to be updated, as described below.

2. Part options are compared to part options from previous runs
   [#installed]_.

   - Parts from previous runs that are no longer part of the buildout
     are uninstalled.

   - Parts from previous runs whose options have changed are also
     uninstalled.

3. Parts are either installed or updated.

   ``install()`` is called on new parts or old parts that were uninstalled.

   ``update()`` is called on old parts whose configuration hasn't changed.


Initialization phase: the constructor
-------------------------------------

The constructor is passed 3 arguments:

``buildout``
   The buildout configuration

   The buildout configuration is a mapping from section names to
   sections.  Sections are mappings from option names to values.  The
   buildout configuration allows the recipe to access configuration
   data in much the same way as configuration files use :ref:`value
   substitutions <value-substitutions>`.

``name``
   The name of the section the recipe was used for

``options``
   The part options

   This is a mapping object and may be written to to save derived
   configuration, to provide information for use by other part
   recipes, or for :ref:`value substitutions <value-substitutions>`.

Nothing should be installed in this phase.

If the part being installed isn't new, options after calling the
constructor are compared to the options from the previous Buildout
run. If they are different, then the part will be uninstalled and then
re-installed by calling the ``install`` method, otherwise, the ``update``
method will be called.

Install or update phase
-----------------------

In this phase, ``install()`` or ``update()`` is called, depending on
whether the part is new or has new configuration.

This is the phase in which the part does its work.  In addition to
affecting changes, these methods have some responsibilities that can
be a little delicate:

- If an error is raised, it is the responsibility of the recipe to
  undo any partial changes.

- If the recipe created any files or directories, the recipe should
  return their paths.  Doing so allows Buildout to take care of
  removing them if the part is uninstalled, making a separate
  uninstall recipe unnecessary.

To make these responsibilities easier to cope with, the ``option``
object passed to the constructor has a helper function, ``created``.
It should be passed one or more paths just before they are created and
returns a list of all of the paths passed as well as any earlier paths
created.  If an exception is raised, any files or directories created
will be removed automatically. When the recipe returns, it can just
return the result of calling ``created()`` with no arguments.

Example: configuration from template recipe
-------------------------------------------

In this example, we'll show a recipe that creates a configuration file
based on a configuration string computed using value substitutions
[#templaterecipes]_.  A sample usage:

.. code-block:: ini

   [buildout]
   develop = src
   parts = server

   [config]
   recipe = democonfigrecipe
   port = 8080
   contents =
      <zeo>
        address ${:port}
      </zeo>
      <mappingstorage>
      </mappingstorage>

   [server]
   recipe = zc.zdaemonrecipe
   program = runzeo -C ${config:path}

.. -> src

   >>> from zc.buildout import testing
   >>> testing.write('buildout.cfg', src)

Some things to note about this example:

- The ``config`` part uses the recipe whose source code we'll show
  below.  It has a ``port`` option, which it uses in its ``contents``
  option.  It could as easily have used options from other sections.

- The ``server`` part uses ``${config:path}`` to get the path to the
  configuration file generated by the ``config`` part. The ``path``
  option value will be computed by the recipe for use in other parts,
  as we've seen here.

- We didn't have to list the ``config`` part in the buildout ``parts``
  option.  It's :doc:`added automatically <implicit-parts>` by virtue of
  its use in the ``server`` part.

- We used the ``develop`` option to specify a ``src`` directory
  containing our recipe.  This allows us to use the recipe locally
  without having to build a distribution file.

If we were to run this buildout, a ``parts/config`` file would be
generated:

.. code-block:: xml

   <zeo>
     address 8080
   </zeo>
   <mappingstorage>
   </mappingstorage>

.. -> config

as would a zdaemon configuration file, ``parts/server/zdaemon.conf``, like:

.. code-block:: xml

    <runner>
      daemon on
      directory /sample/parts/server
      program runzeo -C /sample/parts/config
      socket-name /sample/parts/server/zdaemon.sock
      transcript /sample/parts/server/transcript.log
    </runner>

    <eventlog>
      <logfile>
        path /sample/parts/server/transcript.log
      </logfile>
    </eventlog>

.. -> server

   >>> server = server.replace('/sample', os.getcwd())

Here's the recipe source, ``src/democonfigrecipe.py``::

  import os

  class Recipe:

      def __init__(self, buildout, name, options):
          options['path'] = os.path.join(
             buildout['buildout']['parts-directory'],
             name,
             )
          self.options = options

      def install(self):
          self.options.created(self.options['path'])
          with open(self.options['path'], 'w') as f:
              f.write(self.options['contents'])
          return self.options.created()

      update = install

.. -> src

   >>> testing.mkdir('src')
   >>> testing.write('src', 'democonfigrecipe.py', src)

The constructor computes the ``path`` option.  This is then available
for use by the ``server`` part above.  It's also used later in the
``install`` method.  We use
``buildout['buildout']['parts-directory']`` to get the buildout parts
directory. This is equivalent to using ``${buildout:parts-directory}``
in the configuration.  The parts directory is the standard place for
recipes to create files or directories.  If a recipe uses the parts
directory, it should create only one file or directory whose name is
the part name, which is passed in as the ``name`` argument to the
constructor.

The constructor saves the options so that the data and ``created``
method are available in ``install``.

The ``install`` method calls the option object's ``created`` method
**before** creating a file.  The order is important, because if the
file-creation fails partially, the file will be removed automatically.
The recipe itself doesn't need an exception handler. The configuration
file is then written out. Finally, the ``created`` method is called
again [#boilerplate]_ to return the list of created files (one, in
this case).

The ``update`` method is just an alias for the ``install`` method. We
could have used an empty method, however running install again makes
sure the file contents are as expected, overwriting manual changes, if
any.


Like the ``install`` method, the ``update`` method returns any paths
it created.  These are merged with values returned by the ``install`` or
``update`` in previous runs.

For this recipe to be usable, we need to make it available as a
distribution [#even-though-develop]_, so we need to create a setup
script, ``src/setup.py``::

  from setuptools import setup

  setup(
      name='democonfigrecipe',
      version='0.1.0',
      py_modules = ['democonfigrecipe'],
      entry_points = {"zc.buildout": ["default=democonfigrecipe:Recipe"]},
      )

.. -> src

   >>> testing.write('src', 'setup.py', src)
   >>> testing.run_buildout_in_process()

   >>> config.strip() == testing.read('parts', 'config')
   True
   >>> server == testing.read('parts', 'server', 'zdaemon.conf')
   True

   Run again, nothing changes:

   >>> testing.run_buildout_in_process()
   >>> config.strip() == read('parts', 'config')
   True
   >>> server == testing.read('parts', 'server', 'zdaemon.conf')
   True

The setup script specifies a name and version and lists the module to
be included.

The setup script also uses an ``entry_points`` option.  Entry points
provide a `miniature component systems for setuptools
<https://setuptools.readthedocs.io/en/latest/setuptools.html#extensible-applications-and-frameworks>`_.
A project can supply named components of given types. In the example
above, the type of the component is ``"zc.buildout"``, which is the
type used for Buildout recipes.  A single components named ``default``
is provided.  The component is named as the ``Recipe`` attribute of
the ``democonfigrecipe`` module.  When you specify a recipe in the
``recipe`` option, you name a recipe requirement, which names a
project, and optionally provide a recipe name. The default name is
``default``. Most recipe projects provide a single recipe component
named ``default``.

If we removed the ``server`` part from the configuration, the
two configuration files would be removed, because Buildout recorded
their paths and would remove them automatically.

.. Oh yeah?

   >>> testing.write('buildout.cfg',
   ...               read('buildout.cfg').replace('parts = server', 'parts ='))
   >>> testing.run_buildout_in_process()
   >>> testing.ls('parts')

Uninstall recipes
=================

Uninstall recipes are very rarely needed, because most recipes just
install files and Buildout can handle those automatically.

An uninstall recipe is just a function that takes a name and an
options mapping.  One of the few packages with an uninstall recipe is
`zc.recipe.rhrc
<https://github.com/zopefoundation/zc.recipe.rhrc/blob/master/src/zc/recipe/rhrc/__init__.py#L183>`_.
The ``uninstall`` function there provides the uninstall recipe.
Here's a **highly simplified** version::

  def uninstall(name, options):
     os.system('/sbin/chkconfig --del ' + name)

.. -> src

This was used with a recipe that installed services on older Red Hat
Linux servers.  When the part was uninstalled, it needed to run
``/sbin/chkconfig`` to disable the service.  Uninstall recipes don't
need to return anything.

Like install recipes, uninstall recipes need to be registered using
entry points, using the type ``zc.buildout.uninstall`` as can be seen
in the `zc.recipe.rhrc setup script
<https://github.com/zopefoundation/zc.recipe.rhrc/blob/master/setup.py#L23>`_.

User interaction: logging and UserError
=======================================

Recipes communicate to users through logging and errors. Recipes can
log information using the Python logging library and messages will be
displayed according to buildout's :ref:`verbosity setting <verbosity-level>`.

Errors that a user can potentially correct should be reported by
raising ``zc.buildout.UserError`` exceptions with error messages as
arguments.

Buildout will display these as user errors, rather than printing a
trace back.

Testing recipes
================

The recipe API is fairly simple and standard unit-testing approaches
can be used.  We'll use a helper class,
``zc.buildout.testing.Buildout`` [#helper-class-refined-in-2.9]_ to
provide a minimal buildout environment.

Let's write a test for our configuration recipe.  We need to verify that:

- The recipe generates a ``path`` option.

- The recipe generates a file in the correct place.

- The recipe returns the path it created from ``install``.

.. _recipe-example:

We create a ``testdemoconfigrecipe.py`` file containing our tests::

  import os
  import shutil
  import tempfile
  import unittest
  import zc.buildout.testing

  class RecipeTests(unittest.TestCase):

      def setUp(self):
          self.here = os.getcwd()
          self.tmp = tempfile.mkdtemp(prefix='testdemoconfigrecipe-')
          os.chdir(self.tmp)
          self.buildout = buildout = zc.buildout.testing.Buildout()
          self.config = 'some config text\n'
          buildout['config'] = dict(contents=self.config)
          import democonfigrecipe
          self.recipe = democonfigrecipe.Recipe(
              buildout, 'config', buildout['config'])

      def tearDown(self):
          os.chdir(self.here)
          shutil.rmtree(self.tmp)

      def test_path_option(self):
          buildout = self.buildout
          self.assertEqual(os.path.join(buildout['buildout']['parts-directory'],
                                        'config'),
                           buildout['config']['path'])

      def test_install(self):
          buildout = self.buildout
          self.assertEqual(self.recipe.install(), [buildout['config']['path']])
          with open(buildout['config']['path']) as f:
              self.assertEqual(self.config, f.read())

  if __name__ == '__main__':
      unittest.main()

.. -> src

   >>> testing.write('src', 'testdemoconfigrecipe.py', src)

In the ``setUp`` method, we created a temporary directory and changed
to it.  This is useful to make sure we have a clean working
directory.  We clean it up in the ``tearDown`` method.

Our test uses ``zc.buildout`` so that we can use the
``zc.buildout.testing.Buildout`` helper class.  We did this so we'd
have a more realistic environment, but of course, we could have
stubbed this out ourselves.  Because we're using ``zc.buildout`` in
our test, we'll add it as a test dependency in our setup script::

  from setuptools import setup

  setup(
      name='democonfigrecipe',
      version='0.1.0',
      py_modules = ['democonfigrecipe', 'testdemoconfigrecipe'],
      entry_points = {"zc.buildout": ["default=democonfigrecipe:Recipe"]},
      extras_require = dict(test=['zc.buildout >=2.9']),
      )

.. -> src

   >>> src = src.replace('>=2.9', '>=2.9.dev0') # because we're still at dev0
   >>> testing.write('src', 'setup.py', src)

Here, we defined an "extra" requirement. These are additional
dependencies needed to support optional features. In this case, we're
providing an optional ``test`` feature. (We specified that we want at
least version 2.9, because we're depending on some testing-support
refinements that were added in zc.buildout 2.9.0.)

We'll write a development buildout to run our tests with:

.. code-block:: ini

   [buildout]
   develop = src
   parts = py

   [py]
   recipe = zc.recipe.egg
   eggs = democonfigrecipe [test]
   interpreter = py

.. -> src

    >>> testing.write('buildout.cfg', src)
    >>> testing.run_buildout_in_process()

Running Buildout with this gives is an interpreter script that we can
run our tests with.  The script will make sure that ``zc.buildout``
and our recipe can be imported.

To run our tests:

.. code-block:: console

    bin/py src/testdemoconfigrecipe.py

.. -> src

    >>> print(testing.system(src)) # doctest: +ELLIPSIS
    ..
    ----------------------------------------------------------------------
    Ran 2 tests ...
    OK
    <BLANKLINE>

In this example, we've tried to keep things simple and as free from
external requirements as possible.

More realistically:

- You'd probably arrange your recipe in a Python package rather than
  as a top-level module and a top-level testing module.

- You might use a test runner like nose or pytest.  There are `recipes
  that can help set this up
  <https://pypi.org/search/?q=test+runner+buildout+recipe>`_.
  We just used the test runner built into ``unittest``.

``zc.buildout.testing`` reference
----------------------------------
The zc.buildout.testing module provides an API that can be used when
writing recipe tests.  This API is documented below.

Many of the functions documented below take a path argument as
multiple arguments.  These are joined using ``os.path.join``.  This is
more convenient than having to call os.path.join before calling the
functions.

``Buildout()``
    A class you can use to create buildout and sections objects in your tests

    This is a subclass of the main object used to run buildout.  Its
    constructor takes no arguments.  You can add data to it by setting
    section names to dictionaries::

       buildout['config'] = dict(contents=self.config)

    To get an options object to pass to your recipe, just ask for it back::

       buildout['config']

    See the :ref:`recipe example <recipe-example>` above.

``cat(*path)``
    Display the contents of a file.  The file path is provided as one or
    more strings, to be joined with os.path.join.

    On Windows, if the file doesn't exist, the function will try
    adding a '-script.py' suffix.  This helps to work around a
    difference in script generation on windows.

``clear_here()``
    Remove all files and directories in the current working directory.

    *New in buildout 2.9*

``eqs(got, *expected)``
    Compare a collection with a collection given as multiple
    arguments.

    Both collections are converted to and compared as sets.  If the
    sets are the same, then no output is returned, otherwise a tuple
    of extras is returned, so, for example::

      >>> eqs([1, 2, 3], 3, 1, 2)
      >>> eqs([1, 2, 3], 1, 2, 4) == ({3}, {4})
      True

    *New in buildout 2.9*

``ls(*path)``
    List the contents of a directory.  The directory path is provided as one or
    more strings, to be joined with os.path.join.

``mkdir(*path)``
    Create a directory. The directory path is provided as one or
    more strings, to be joined with os.path.join.

``system(command, input='')``
    Execute a system command with the given input passed to the
    command's standard input.  The output (error and regular output
    combined into a single string) from the command is returned.

``read(*path)``
    Read text from a file at the given path.  The file path is
    provided as one or more strings, to be joined with os.path.join.

    If no path is given, the ``'out'`` is used.

    *New in buildout 2.9*

``remove(*path)``
    Remove a directory or file. The path is provided as one or
    more strings, to be joined with os.path.join.

``rmdir(*path)``
    Remove a directory. The directory path is provided as one or
    more strings, to be joined with os.path.join.

``run_buildout_in_process(command='buildout')``
    Run Buildout in a `multiprocessing.Process
    <https://docs.python.org/3/library/multiprocessing.html#process-and-exceptions>`_.
    The command is must be a buildout command string, starting with 'buildout'.
    You can provide additional arguments, as in ``'buildout -v'``.

    Some extra options are added to the command to prevent network
    access when running the command.  Any distribution the buildout
    needs must already be available for import.  So, for example, if
    you want to use some recipe, include it in your rest dependencies.

    All output from the buildout run is captured in the file named ``out``.

    This is useful for integration tests or tests of recipes that
    interact intimately with buildout or other recipes.

    *New in buildout 2.9*

``write(*path_and_contents)``
    Create a file.  The file path is provided as one or more strings,
    to be joined with os.path.join. The last argument is the file contents.

Documenting your recipe
=======================

Please, don't use your doctests to document your recipe. (We did that
a lot and it didn't turn out well.) Just write straightforward
documentation that explains to users how to use your recipe.

If you have examples, however, considering testing them using `manuel
<https://pythonhosted.org/manuel/>`_.  You can see examples of how to
do that by looking at the `source of this topic
<https://raw.githubusercontent.com/buildout/buildout/master/doc/topics/writing-recipes.rst>`_.
Otherwise, it's very easy to end up with mistakes in your examples.


.. [#installed] Configuration data from previous runs are saved in a
   buildout's installed database, :ref:`typically saved in
   <installed-option>` a generated ``.installed.cfg`` file.

.. [#templaterecipes] There are a variety of template recipes that
   provide different features, like using template files and
   supporting various template engines. Don't re-use the example here.

.. [#boilerplate] Unfortunately, returning the result of calling
   ``created()`` is boilerplate. Future versions of buildout `won't
   require this return <https://github.com/buildout/buildout/issues/357>`_.

.. [#even-though-develop] Even though we aren't distributing the
   recipe in this example, we still need to create a :ref:`develop
   distribution <python-development-projects>` so that Buildout can
   find the recipe and its meta data.

.. [#helper-class-refined-in-2.9] We're relying on some refinements
   made to the helper class in zc.buildout 2.9.
