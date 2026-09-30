The ``develop-buildout`` and ``verify-buildout`` skills absorb the
uv-dep-removal verification lessons: ``devenv up -d`` as the engine
bring-up (native devenv services; the manual podman ladder stays as
the surgical fallback), cheap family re-issue after a killed run,
call-time workspace freeze as run attribution, the four-gate bundle
re-run after any ``src/`` touch, duck-typing and Version re-parsing
rules for the two pkg_resources copies, hash-ordered SpecifierSet
iteration on old packagings, interpreter-derived fixtures versus the
blind local cell, the CI coverage job's local repro and its
parallel-file dir-hash poisoning, and the seed-before-pip-pin
bootstrap ordering.  [Fizz]
