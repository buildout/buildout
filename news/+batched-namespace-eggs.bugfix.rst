Fixed egg reconstruction after a batched ``uv`` install of distributions
sharing a namespace package (``zope.*``, ``zc.*``, ...).  The whole shared
top-level directory was moved into the first reconstructed egg, leaving the
sibling distributions' eggs with metadata only; their code was importable
solely from the wrong egg, and broke at runtime as soon as the winning egg
was not on ``sys.path`` (``ModuleNotFoundError: No module named
'zc.lockfile'``).  Each egg is now reconstructed file-precise from its own
RECORD entries.  [gotcha]
