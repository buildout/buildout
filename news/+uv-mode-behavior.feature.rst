The ``installer = uv`` mode adapts buildout semantics to uv with clear
errors and warnings instead of tracebacks.
Ambient ``UV_*`` environment variables no longer leak into resolves — only
the buildout configuration decides sources — while ``UV_CACHE_DIR`` is
kept so offline resolves find their store.
``install-from-cache = true`` maps onto uv's own cache via ``--offline``
resolves, and dependency links found in distribution metadata keep working
through iterative per-requirement compiles.
Invalid ``[versions]`` pins raise the pip-parity
``IncompatibleConstraintError`` (pins for other projects are skipped with
a warning), a malformed ``pylock.toml`` from uv is reported as a
resolution error with context, ``MissingDistribution`` carries uv's stderr
tail, requiring a project that find-links only offer as legacy ``.egg``
artifacts explains that uv cannot install eggs, an existing ``~/.pypirc``
warns that uv reads ``~/.netrc`` instead, and a non-default ``allow-hosts``
warns that uv has no host allow-list.  [gotcha]
