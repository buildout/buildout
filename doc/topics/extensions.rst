===================
Buildout extensions
===================

Buildout has a mechanism that can be used to extend it in low-level
and often experimental ways.  Use the ``extensions`` option in the
``buildout`` section to use an existing extension. For example, the
`buildout.wheel extension
<https://github.com/buildout/buildout.wheel>`_ provides support for
`Python wheels <http://pythonwheels.com/>`_:

.. code-block:: ini

  [buildout]
  extensions = buildout.wheel
  ...

Some other examples of extensions can be found in the `standard
package index <https://pypi.python.org/pypi?:action=browse&c=512&c=546>`_.
