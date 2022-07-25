================================================================
Buildout, an automation tool written in and extended with Python
================================================================

Buildout is a tool for automating software assembly.

- Run build tools to build software.

- Apply software and templates to generate configuration files and scripts.

- Applicable to all software phases, from development to production deployment.

- Based on **core principles**:

  - Repeatability

  - Componentization

  - Automation

Repeatability
=============

It's important that given a project configuration, two checkouts of the
configuration in the same environment (operating system, Python
version) should produce the same result, regardless of their history.

For example, if someone has been working on a project for a long time,
and has committed their changes to a version control system, they
should be able tell a colleague to check out their project and run
buildout and the resulting build should have the same result as the
build in the original working area.

Componentization
================

We believe that software should be self-contained, or at least, that
it should be possible.  The tools for satisfying the software
responsibilities should largely reside within the software project
itself.

Some examples:

- Software services should include tools for monitoring them.
  Operations, including monitoring is a software responsibility,
  because the creators of the software are the ones who know best how
  to assess whether it is operating correctly.

  It should be possible, when deploying production software, for the
  software to configure the monitoring system to monitor the software.

- Software should provide facilities to automate its configuration.
  It shouldn't be necessary for people to create separate
  configuration whether it be in development or deployment (or stages
  in between).

Automation
==========

Software deployment should be highly automated.  It should be possible
to checkout a project with a single simple command (or two) and get a
working system.  This is necessary to achieve the goals of
repeatability and componentization and generally not to waste people's
time.

Learning more
=============

Learn more:

- :doc:`Getting started <getting-started>`

- :doc:`Topics <topics/index>`

- :doc:`Reference <reference>`


Additional resources
====================

Issue tracker
  https://github.com/buildout/buildout/issues

Github repository
  https://github.com/buildout/buildout

Contributing
  Join the buildout-development google group,
  https://groups.google.com/forum/#!forum/buildout-development to
  discuss ideas and submit pull requests against the `buildout
  repository <https://github.com/buildout/buildout>`_.
