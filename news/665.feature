Add config option: ``optional-extends``.
This is the same as the ``extends`` option, but then for optional files.
The names must be file paths, not URLs.  If the path does not exist,  it is silently ignored.
This is useful for optionally loading a ``local.cfg`` or ``custom.cfg`` with options specific for the developer or the server.
[maurits]
