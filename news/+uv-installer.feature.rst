New ``installer`` option in the ``[buildout]`` section: set it to ``uv``
to run package resolution and installation through
`uv <https://docs.astral.sh/uv/>`_ instead of pip, overridable on the
command line with the usual assignment syntax, for example
``bin/buildout buildout:installer=uv``.
Package discovery and version resolution run through ``uv pip compile``
instead of the vendored setuptools package index: everything still open
after the environment check resolves in a single compile, with the
buildout's develop projects riding as overrides, and installs in one
batched ``uv pip install`` — the per-requirement pip subprocess fan-out
is gone.
Requires uv 0.12.11 or newer; ``uv`` is now a declared dependency of
zc.buildout.  The pip mode code path is unchanged.  [gotcha]
