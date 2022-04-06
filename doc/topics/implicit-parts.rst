=================================================
Automatic installation of part dependencies
=================================================

Buildout parts are requested by the ``parts`` option of the
``buildout`` section, but a buildout may install additional parts that
are dependencies of the named parts.  For example, in

.. code-block:: ini

   [buildout]
   develop = .
   parts = server

   [server]
   => app
   recipe = zc.zdaemonrecipe
   program = ${buildout:bin-directory}/app ${config:location}

   [app]
   recipe = zc.recipe.egg
   eggs = myapp

   [config]
   recipe = zc.recipe.deployment:configuration
   text = port 8080

.. -> src

    >>> write(src, 'buildout.cfg')
    >>> write("from setuptools import setup; setup(name='myapp', py_modules=['myapp'])", 'setup.py')
    >>> write("pass", 'myapp.py')
    >>> run_buildout('buildout annotate')
    >>> run_buildout()
    >>> print(read()) # doctest: +ELLIPSIS
    Creating ...
    Installing config.
    Installing app.
    Installing server.
    ...

the ``server`` part depends on the ``app`` part to
install the server software and on the ``config`` part to provide the
server configuration.

The ``config`` part will be installed before the ``server`` part
because it's referenced in a value substitution.  The value
substitution makes the ``config`` part a dependency of the ``server``
part.

The ``server`` part has the line:

.. code-block:: ini

   => app

This line [#implication-syntax]_, uses a feature that's **new in zc.buildout
2.9**.  It declares that the ``app`` part is a dependency of the
``server`` part.  The server part doesn't use any information from the
``app`` part, so it has to declare the dependency explicitly.  It
could have declared both dependencies explicitly:

.. code-block:: ini

  => app config

Dependency part selection serves separation of concerns.  The
buildout ``parts`` option reflects the requirements of a buildout as a
whole.  If a named part depends on another part, that's the concern of
the named part, not of the buildout itself.

.. [#implication-syntax] The ``=>`` syntax is a convenience.  It's
   based on the mathematical symbol for implication.  It's a short
   hand for:

   .. code-block:: ini

      <part-dependencies> = app

   Multiple parts may be listed and spread over multiple lines, as
   long as continuation lines are indented.
