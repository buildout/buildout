Document the Windows iteration loop in ``doc/running-tests.rst`` and in
the ``develop-buildout`` skill: pushing a tree to the ``windows-iter``
scratch branch runs only the static trio and the Windows leg, while the
full matrix stays off that branch. The scratch ref is disposable; any
push recreates it. [gotcha]
