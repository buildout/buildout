All implementation modules now carry full type annotations.
``make typecheck`` gates on Astral's ``ty`` with zero diagnostics over the
checkout, and ``make typecheck-any`` (mypy, ``disallow_any_explicit``)
blocks new explicit ``Any`` annotations against a burndown baseline; the
uv lock, ``pkg_resources``, config-data and recipe-seam boundaries are
typed precisely.  The test-support modules ``testing.py`` and
``testrecipes.py`` remain unannotated by design.  [gotcha]
