Change History
**************

.. You should *NOT* be adding new change log entries to this file.
   You should create a file in the news directory instead.
   For helpful instructions, please see:
   https://github.com/buildout/buildout/blob/master/doc/ADD-A-NEWS-ITEM.rst

.. towncrier release notes start

5.3.0a2 (1980-01-01)
--------------------

Bug fixes:


- A failing ``pip``/``uv`` install subprocess is now reported as a clean
  user error whose message ends with the command's own output, so the
  actual diagnostic (for example a missing system header while building an
  sdist) is the last thing on screen.  Previously the captured output went
  to a detached ``print`` that could surface after the report or not at
  all, and the failure was mislabeled "An internal error occurred due to a
  bug in either zc.buildout or in a recipe being used", followed by a
  traceback.  [gotcha]
- Fixed egg reconstruction after a batched ``uv`` install of distributions
  sharing a namespace package (``zope.*``, ``zc.*``, ...).  The whole shared
  top-level directory was moved into the first reconstructed egg, leaving the
  sibling distributions' eggs with metadata only; their code was importable
  solely from the wrong egg, and broke at runtime as soon as the winning egg
  was not on ``sys.path`` (``ModuleNotFoundError: No module named
  'zc.lockfile'``).  Each egg is now reconstructed file-precise from its own
  RECORD entries.  [gotcha]
- Made the offline-mode error for a configuration file that cannot be
  downloaded actionable: it now advises setting ``extends-cache`` to a cache
  directory in the root configuration and running buildout once in online
  mode, after which the download is reused from the cache.  A configured
  ``extends-cache`` directory is now created on first use, as the
  documentation always promised; previously even the first *online* run
  failed with "to be used as a download cache doesn't exist" unless the
  directory was created by hand.  [gotcha]
- Windows: ``make`` no longer reruns ``prepare.sh`` on every invocation.  ``dev.py`` generates only ``bin\\buildout.exe`` there, so the extensionless Makefile target never materialized; the rerun re-resolved the venv with ``pip -U``, and any release published between two runs flipped the ``py`` part signature.  The resulting uninstall tried to delete the running ``bin\\buildout.exe`` and died with ``WinError 32``.  The Makefile now tracks the prepare run with a stamp file instead of the script name. [gotcha]


Development:


- CI now enforces the explicit-Any burndown: mypy is devenv-provided, a typecheck-any job runs make typecheck-any in the workflow, and a matching mypy cell joins the dagger static family, so no new explicit Any annotation can enter src/zc/buildout on a green CI. [Fizz]
- Document the Windows iteration loop in ``doc/running-tests.rst`` and in
  the ``develop-buildout`` skill: pushing a tree to the ``windows-iter``
  scratch branch runs only the static trio and the Windows leg, while the
  full matrix stays off that branch. The scratch ref is disposable; any
  push recreates it. [gotcha]
- Documented the pre-push static gate (``make lint``, ``make typecheck``, ``make complexity``) and the filesystem-ordering trap in the repo skills: directory-listing order differs between macOS and Linux CI, so pattern-select instead of positional indexing, and verify such changes on the dagger CI axis before pushing. [gotcha]
- Extracted the ``_read_record_or_raise`` and ``_ensure_download_cache`` helpers to keep ``make_egg_after_pip_install`` and ``_open`` within their pinned complexity budgets, and refreshed the line-pinned complexity baseline after the line drift from the recent easy_install changes. [gotcha]
- Point the ``develop-buildout`` skill's annotation section at the
  ``annotate-from-traces`` skill, so annotating existing modules reaches
  the MonkeyType traced-suite pipeline instead of improvising. [gotcha]
- Record in the verify-buildout lint feature that ``ruff --fix
  --unsafe-fixes`` breaks the ``While:`` reporting code, a finding from
  the 2026-09-12 ruff-fix probes whose branch is being retired. [gotcha]
- Recorded the coverage-based survivor classification in ``mutation-testing/NOTES.md``: the two suites are complementary (99% combined on cli/configfiles), no dead code found, shared blind spot reduced to two ``__repr__`` debug helpers.
- Recorded the scoped-round harness lessons in ``mutation-testing/NOTES.md``: mutants as data in Python instead of generated bash, a vacuous-suite guard (testrunner exits 0 on a misspelled selector), ANSI stripping, and the gap/equivalent/dead classification of survivors.
- Split the ``develop-buildout`` skill's dagger and ty sections into
  on-demand supporting files (``dagger.md``, ``ty-tier.md``), shrinking
  the always-loaded skill body from 499 to 308 lines. Content moved
  verbatim; pointer sections keep discovery. [gotcha]
- The ``develop-buildout`` and ``verify-buildout`` skills absorb the
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
- ``annotate-from-traces`` skill documents the MonkeyType traced-suite
  pipeline for annotating existing modules: subprocess tracing via
  ``make test-traced``, purging test-double traces before the libcst
  apply, the human pass over tracer blind spots, repo typing precedents
  (``TextIO`` over ``TextIOWrapper``, ``Mapping`` versus invariant
  ``Dict``, documented escape hatches), the modern-syntax dialect behind
  ``from __future__ import annotations``, and the before/after ``ty``
  log evidence discipline.
  [gotcha]
- ``develop-buildout`` documents dagger as the local pre-push CI gate:
  replay cells on the committed tree (static gates included), the
  measured boundary of what container cells catch versus what still
  needs the runner, and how the engine's caches make the gate cheap on
  a warm engine; plus the running-dagger-locally mechanics and two
  module rules (exec-error output, ``ReturnType.ANY`` caching).
  [gotcha]


Tests:


- Extend the pytest mirror with verbose ``annotate`` coverage: the
  ``-=`` directive's history sub-block and history print order are now
  asserted. The 2026-09-30 mutation round confirmed the corresponding
  mutants (dropped REMOVE history entry, reversed history) are not
  reachable through the annotate CLI rendering in either suite; they are
  recorded as an equivalent-mutant class. [gotcha]
- Fixed test_annotate_verbose_shows_removal_history on Windows: the test asserted multi-line annotate output with LF while text-mode stdout emits CRLF there; it now normalizes line endings before asserting. [gotcha]
- Fixed the ``update_env`` fixture's fake-release builder picking the wrong entry on filesystems with a different directory-listing order than macOS, which failed ``test_update`` and its contract test on Linux CI. [gotcha]
- Fixed the extends-cache unit tests building a malformed ``file://`` URL on Windows (``file://C:/...`` parses to an empty path); they now use ``Path.as_uri()``. [gotcha]
- Fixed the test-suite flake behind the intermittent
  ``test_dependencylinks_option`` failure under pytest-xdist: the
  ``update_env`` fixture built fake zc.buildout releases with
  ``python -m build --sdist`` directly on the shared checkout, and
  setuptools rewrote ``src/zc.buildout.egg-info`` in place.  Sample
  buildouts develop zc.buildout from that checkout, so part signatures
  hash ``src/``; a concurrent worker hashing the tree during the rewrite
  window computed a different signature and parts flipped from
  "Updating" to "Uninstalling/Installing".  The fake releases are now
  built from a private copy of the tree.  [gotcha]


5.3.0a1 (2026-09-27)
--------------------

Breaking changes:


- The ``installer = uv`` mode tightens several legacy behaviors.
  ``find-links`` entries pointing at a Mercurial repository (``hg:`` or
  ``hg+``) or carrying ``#egg=``/``#md5=`` URL fragments now raise a clear
  ``UserError`` naming the entry, instead of surfacing uv's own parse error.
  Offline mode (``buildout -o``) now forwards ``--offline`` to uv, so resolves
  are served by uv's local cache alone and builds that relied on network
  access during offline runs must warm the cache first.
  The ``download-cache`` option is deprecated: uv keeps downloads in its own
  cache and the download cache is not populated; setting the option logs a
  deprecation warning, and the directory is still consulted as a find-links
  location.  [gotcha]


New features:


- New ``--interpolated`` option on the ``query`` and ``annotate`` commands:
  print values with ``${...}`` substitutions applied, the way recipes see
  them.  Raw values remain the default output.  [gotcha]
- New ``installer`` option in the ``[buildout]`` section: set it to ``uv``
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
- Repeated buildout runs are faster: sources listed in the ``develop``
  option are no longer reinstalled (``pip install -e``) on every run.
  An editable install is only redone when its ``setup.py``, ``setup.cfg``
  or ``pyproject.toml`` is newer than its egg-link, when its egg-info is
  missing, or when the develop-eggs directory changed; verbose output tells
  the cases apart with ``Making editable install`` versus
  ``Keeping editable install of ...: its packaging metadata ... is
  unchanged``.  [gotcha]
- The ``installer = uv`` mode adapts buildout semantics to uv with clear
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


Bug fixes:


- Fixed spurious uninstall/reinstall cycles of parts whose recipe resolves
  to a develop egg: a packaging run on the develop source tree regenerates
  setuptools' ``SOURCES.txt``, which moved the directory hash, so
  ``_dir_hash`` now excludes it.
  Offline mode (``buildout -o``) now reuses distributions that were
  installed from wheels, whose dist-info layout was invisible to the offline
  environment scan.
  Fixed a ``TypeError`` that made zc.buildout unimportable on Python 3.9.
  ``query`` rejects malformed arguments (for example ``:port`` or
  ``a:b:c``) with a clear message stating the expected ``section:option``
  format.
  With ``installer = uv``, old-style wheels whose ``.dist-info`` directory
  keeps the unescaped project name install correctly, and the uv floor is
  0.12.11 because earlier 0.12.x served their own cache on ``--offline``
  resolves.  [gotcha]
- Windows fixes: a local package index spelled as a drive path
  (``C:\index``) no longer reaches pip misread as a URL — drive paths are
  converted to ``file://`` URIs like any other local index — and with
  ``installer = uv`` a ``file://`` index spelled as a native Windows path no
  longer crashes resolution, while the fallback lookup for the uv executable
  next to the Python interpreter now finds the ``uv.exe`` console script.
  [gotcha]


Development:


- Adopted ruff with a ``make lint`` gate and completed the tree-wide lint
  burndown: the classic pyflakes/pycodestyle rules, import sorting,
  pyupgrade within the Python 3.9 floor, comprehension construction,
  blind-except and the bugbear/simplify/misc judgment sets are all selected
  with an empty global ignore list, and deliberate exceptions carry scoped
  noqa reasons.  The code tree modernized along the way: PEP 604 unions,
  PEP 585 builtin generics, f-strings and the mechanical pyupgrade fixes,
  with load-bearing import orders preserved.  [gotcha]
- All implementation modules now carry full type annotations.
  ``make typecheck`` gates on Astral's ``ty`` with zero diagnostics over the
  checkout, and ``make typecheck-any`` (mypy, ``disallow_any_explicit``)
  blocks new explicit ``Any`` annotations against a burndown baseline; the
  uv lock, ``pkg_resources``, config-data and recipe-seam boundaries are
  typed precisely.  The test-support modules ``testing.py`` and
  ``testrecipes.py`` remain unannotated by design.  [gotcha]
- CI and the development environment were rebuilt around devenv and Dagger.
  GitHub jobs bootstrap only Nix and take every tool — Python, uv, ruff, ty —
  from the repository-owned ``devenv.nix`` (optionally shared across jobs via
  a cachix cache), so CI and local shells use the same toolchain.
  A repository-owned dagger module runs the whole CI job table locally or in
  containers (``dagger call ci``, per-family matrices, per-Python pip/uv
  cache volumes, transient-fetch retries that still fail fast on genuine
  failures, and failure-debug tooling), replacing the flaked devpi proxy.
  The Windows leg lives in its own reusable workflow with a dispatch-only
  iteration loop, both suites gained coverage jobs that upload HTML reports,
  and ``etc/bump_ci_versions.py`` keeps the CI version matrices current.
  The test suites run hermetically: ``prepare.sh`` seeds
  ``downloads/test-seed/`` so spawned pip/uv builds resolve offline.
  Agent skills and in-tree planning documents — including the phased plan to
  remove ``pkg_resources`` and ``setuptools`` from the uv path — are
  maintained alongside the code.  [gotcha]
- Structural refactoring under a new complexity gate: ``make complexity``
  (radon) fails when a function grows beyond the checked-in baseline or when
  new code exceeds grade B.  The high-complexity cores of ``Buildout``
  (initialization, install, develop, query, upgrade, ``main``) and of
  ``easy_install.Installer`` were decomposed into module-level helpers
  pinned by unit tests, several functions dropping from cyclomatic
  complexity 20–60 to grade A or B without behavior change.
  The monolithic modules split into focused ones — ``cli``, ``configfiles``,
  ``configsetup``, ``parts``, ``annotations``, ``scripts``, ``develop``,
  ``install_backend`` and ``errors`` — with the original modules
  re-exporting for compatibility, and the frame-local ``__doing__``
  error-context mechanism was replaced by a portable context manager, with
  unchanged ``While:`` error output.  [gotcha]


Tests:


- CI gains a parallel uv test set: the legacy suite reruns through the uv
  install pipeline (``make test-uv``) across the platform matrix including
  Windows, against a uv version matrix spanning the earliest supported
  0.12.x and the latest releases.  Most of the legacy doctest corpus runs
  green under ``installer = uv`` — recipe and extension fixtures build
  wheels instead of eggs and egg-only doctests are marked ``uv-deprecated``
  — and picked-versions reporting parity between the uv and pip installers
  is pinned by unit tests.  [gotcha]
- Test maintenance: test with pip 26.1.2, updated GitHub workflow action
  versions, fixed script tests and Windows detection in ``prepare.sh``,
  restored the propagate flags of ``zc.buildout*`` loggers after each pytest
  so later ``caplog`` captures are not starved, and made the test harness's
  index URLs, file server and output normalizers Windows- and uv-proof.
  [maurits, gotcha]
- The test suite was ported from legacy doctests to pytest: the ported suite
  runs in parallel via pytest-xdist (``make pytest``) and is wired into CI
  across the full Python and platform matrix, and the dagger CI module
  gained its own test harness that pins the job table against the GitHub
  workflows.  [gotcha]


5.2.0 (2026-04-29)
------------------

New features:


- Restrict ``setuptools`` to less than 82 if it is not pinned.
  When ``zc.buildout`` checks if it should upgrade itself or ``setuptools``, under some circumstances this could lead to a too new ``setuptools`` version getting installed.
  [maurits]


Tests:


- Test with ``pip`` 26.1.  [maurits]


5.1.3 (2026-03-06)
------------------

Bug fixes:


- Replace 4 bare except clauses with except Exception.
  [haosenwang1018]


5.1.2 (2026-02-10)
------------------

Bug fixes:


- Accept ``setuptools`` 81.
  Require ``setuptools<82``.
  [maurits]


5.1.1 (2025-11-25)
------------------

Bug fixes:


- Store buildout index url in the installer, so pip can use it.  [maurits] (#731)
- When installing packages in development, treat the name as a file uri.
  Otherwise ``pip install -e package_name`` will look on PyPI, instead of a local ``package_name`` directory.
  [maurits] (#734)


5.1.0 (2025-11-20)
------------------

New features:


- Support Python 3.14.  No changes were needed.
  [maurits] (#314)
- Warn when old-style namespaces are used in packages under development.
  [maurits] (#729)


Bug fixes:


- Require ``setuptools<81``.
  We need the ``pkg_resources`` module which is scheduled for removal in 81.
  [maurits] (#81)


5.0.0 (2025-11-12)
------------------

Tests:


- Test with ``pip`` 25.3. (#727)


5.0.0a3 (2025-09-24)
--------------------

Bug fixes:


- Fix logic in detecting namespace init files for deletion.  [maurits] (#720)


5.0.0a2 (2025-09-11)
--------------------

Bug fixes:


- Fix reading metadata files from dist-info in Windows.  [maurits] (#722)


5.0.0a1 (2025-09-11)
--------------------

Breaking changes:


- Install development eggs (editable installs) using pip.
  Theoretically this means that you could develop a package that uses for example ``hatchling`` as build system.
  In practice this does not work yet, but the foundation is there.
  [maurits] (#676)
- Install all namespace packages as native namespaces.  [maurits] (#676)
- Store eggs in a sub directory: ``eggs/v5``.
  Or with abi tags for example: ``eggs/v5/cp313``.
  [maurits] (#676)
- Install most packages with pip, with only rare exceptions.  [maurits] (#676)
- The ``zc.buildout`` package itself uses native namespaces now.  [maurits] (#676)
- Require at least ``setuptools`` version 61.0.0.
  This is needed due to the changes in the test setup.
  [maurits]


Tests:


- The tests have mostly been changed to use wheels instead of eggs, so they more closely resemble real life.  [maurits] (#676)
- Removed inactive tests for no longer existing ``bootstrap.py``.
  [maurits]
- Split the ``buildout.txt`` test file into multiple files.
  [maurits]


4.1.12 (2025-06-11)
-------------------

Bug fixes:


- Fix error ``get_win_launcher`` not found on Windows on setuptools 80.3+.
  [maurits] (#713)


4.1.11 (2025-06-11)
-------------------

Bug fixes:


- Fix development installs to still work when using setuptools 80.0.0.
  From then on, setuptools internally calls ``pip install --editable``.
  Note that "distutils scripts" can no longer be detected with setuptools 80.
  This seems an ancient technology, and probably hardly used.
  [maurits] (#708)
- Use a copy of ``package_index.py`` from ``setuptools`` 80.2.0.
  This fixes compatibility with ``setuptools`` 80.3.0 where this module was removed.
  Merged some of our patches into this copy.
  [maurits] (#710)


4.1.10 (2025-05-21)
-------------------

Bug fixes:


- Override `pkg_resources.Environment.can_add` to have better results on Mac.
  Without this, a freshly created Mac-specific egg may not be considered compatible.
  This can happen when the Python you use was built on a different Mac OSX version.
  [maurits] (#609)


4.1.9 (2025-04-09)
------------------

Bug fixes:


- Fix accidental changes to ``PYTHONPATH`` in ``os.environ`` when calling ``pip install``.
  [xavth] (#639)


Tests


- Use ``wheel`` 0.45.1 when testing with ``setuptools`` older than 70.1.0.
  Otherwise, when combining an older ``setuptools`` with a newer ``wheel`` version, the ``bdist_wheel`` command exists in neither of these packages.
  [maurits] (#705)


4.1.8 (2025-04-09)
------------------

Bug fixes:


- Use the canonical name of a package when checking for a version constraint.
  [maurits] (#689)
- Get actual project name from dist.
  Use this for naming the egg that gets created after installing a wheel or after doing a pip install of a source dist.
  [maurits] (#695)
- Log all http errors when processing package url.
  [maurits] (#1013)


4.1.7 (2025-04-08)
------------------

Bug fixes:


- Prevent getting package pages twice.
  Since version 4.1.5 we first request normalized package url on PyPI servers, but a subsequent check needed a fix.
  [maurits] (#634)
- No longer recompile py files if we moved the dist.
  This code was never updated for Python 3, where the `.pyc` files are in a `__pycache__` directory, so it had no effect.
  [maurits] (#699)
- Require at least `packaging` version 23.2.
  Needed because we use the `utils.is_normalized_name` function.
  [maurits] (#700)


4.1.6 (2025-04-03)
------------------

Tests


- While creating sample packages for testing, mostly create wheels instead of eggs.
  For the sample source distributions, create ``tar.gz`` instead of ``zip`` files.
  Then our package index for testing is more like the actual PyPI.
  [maurits] (#675)


4.1.5 (2025-03-31)
------------------

Bug fixes:


- Implement PEP 503: request normalized package url on PyPI servers.
  [andreclimaco] (#634)
- Install ``wheel`` before ``setuptools`` when checking if an upgrade and restart are needed.
  [maurits] (#691)


4.1.4 (2025-03-07)
------------------

Bug fixes:


- If needed, copy and rename wheels before making an egg out of them.
  This helps for wheels of namespace packages created with ``setuptools`` 75.8.1 or higher.
  For namespace package we need a dot instead of an underscore in the resulting egg name.
  [maurits] (#686)


4.1.3 (2025-03-05)
------------------

Bug fixes:


- Patch the ``find`` method from ``pkg_resources.WorkingSet``.
  Let this use the code from ``setuptools`` 75.8.2, if the currently used version is older.
  This is better at finding installed distributions.
  But don't patch ``setuptools`` versions older than 61: the new version of the method would give an error there.
  [maurits] (#682)


4.1.2 (2025-03-05)
------------------

Bug fixes:


- Fix error finding the ``zc.buildout`` distribution when checking if we need to upgrade/restart.
  This depends on your ``setuptools`` version.
  [maurits] (#681)


4.1.1 (2025-03-04)
------------------

Bug fixes:


- Fix error adding minimum ``zc.buildout`` version as requirement.
  [maurits] (#679)


4.1 (2025-03-04)
----------------

New features:


- In the ``ls`` testing method, add keyword argument ``lowercase_and_sort_output``.
  The default is False, so no change.
  When true, as the name says, it sorts the output by lowercase, and prints it lowercase.
  We need this in one test because with ``setuptools`` 75.8.1 we no longer have a filename ``MIXEDCASE-0.5-pyN.N.egg``, but ``mixedcase-0.5-pyN.N.egg``.
  [maurits] (#7581)


Bug fixes:


- When trying to find a distribution for ``package.name``, first try the normalized name (``package_name``).
  This fixes an error finding entry points for namespace packages.
  The error is: ``TypeError: ('Expected str, Requirement, or Distribution', None)``.
  [maurits] (#7581)


Development:


- Test with latest ``setuptools`` 75.8.2 and with ``pip`` 25.0.1.
  Note that ``setuptools`` 75.8.1 can be troublesome and should be avoided.
  [maurits] (#7581)


4.0 (2025-01-30)
----------------

Breaking changes:


- Drop Python 3.8 support.  Require 3.9 as minimum. (#38)


Development:


- Test against `setuptools == 75.6.0`. (#671)


4.0.0a1 (2024-10-22)
--------------------

Breaking changes:


- Add dependency on ``packaging``.  This gets rid of ugly compatibility code.
  [maurits] (#38)
- Require ``setuptools >= 49.0.0``.
  This is the first version that supports PEP 496 environment markers, for example ``demo ==0.1; python_version < '3.9'``.
  An earlier change had ``setuptools >= 42.0.2``, otherwise we got ImportErrors.
  Also, since this is higher than 38.2.3, we are sure to have support for wheels.
  Remove support for ``distribute``, which was probably already broken.
  [maurits] (#38)
- Drop support for Python 2.  Require Python 3.8 as minimum.
  [maurits] (#38)


New features:


- Support Python 3.12 and 3.13.
  This only needed a few test fixes.
  [maurits] (#38)
