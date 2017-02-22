=========
Reference
=========

The Buildout command line
=========================

A Buildout execution is of the form:

.. code-block:: console

  buildout [buildout-options] [settings] [subcommand [subcommand-arguments]]

Buildout options
----------------

Buildout subcommands
--------------------

.. _bootstrap-subcommand:

bootstrap
_________

Install a local ``bootstrap`` script.  The ``bootstrap`` subcommand
doesn't take any arguments.

See :doc:`Bootstrapping <topics/bootstrapping>` for information on why
you might want to do this.

.. _init-subcommand:

init [requirements]
____________________

Generate a Buildout configuration file and bootstrap the resulting buildout.

If requirements are given, the generated configuration will have a
``py`` part that uses the ``zc.recipe.egg`` recipe to install the
requirements and generate an interpreter script that can import them.
It then runs the resulting buildout.

See :ref:`Bootstrapping <init-generates-buildout.cfg>` for examples.

