===========================
Implicit part selection
===========================

Buildout parts are requested by the ``parts`` option of the
``buildout`` section, but a buildout may install additional parts that
are referenced by the named parts.  For example, in
[#common-dev-buildout-pattern]_:

.. code-block:: ini

   [buildout]
   develop = .
   parts = py

   [test]
   recipe = zc.recipe.testrunner
   eggs = myproject

   [py]
   recipe = zc.recipe.egg
   eggs = ${test:eggs}
   interpreter = py

.. -> src

   >>> write(src, 'buildout.cfg')
   >>> write("from setuptools import setup; setup(name='myproject')",
   ... 'setup.py')
   >>> run_buildout()
   >>> eqs(ls('bin'), 'test', 'py')

The named part, ``py`` will be installed, but so will the ``test``
part, because the configuration of the ``py`` part refers to the
configuration of the ``test`` part.

This is a minor convenience in this example, but in much larger
buildouts, it can lead to significant simplification.

Implicit part selection also serves separation of concerns.  The
buildout ``parts`` option reflects the requirements of a buildout as a
whole.  If a named part depends on another part, that's the concern of
the named part, not of the buildout itself.

.. [#common-dev-buildout-pattern] This configuration follows a common
   pattern for new development projects, with a part to define a test
   runner and a part to define an interpreter.
