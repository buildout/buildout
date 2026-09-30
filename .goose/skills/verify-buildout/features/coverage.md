# Coverage variants of the test suites

Both repo test suites have a coverage variant: `make coverage` (legacy
doctest/testrunner suite) and `make coverage-pytest` (ported pytest
suite). They answer "what of `src/zc/buildout` does this suite actually
execute" — including the code run by the many spawned `bin/buildout`
and pip subprocesses, which is where most of buildout's behavior lives.

## How it works

One mechanism covers every process, no per-suite hooks:

- `etc/coverage/sitecustomize.py` goes on `PYTHONPATH` (the Makefile
  `COVERAGE_ENV` does this, together with the `eggs/v5/*.egg` entries so
  the coverage egg is importable everywhere, including xdist workers —
  same reason as `make pytest`). Python imports `sitecustomize` at
  interpreter startup; the hook checks `COVERAGE_PROCESS_START` and
  calls `coverage.process_startup()`. Every interpreter in the run —
  the suite process, xdist workers, test-spawned `bin/buildout`
  scripts, pip — starts its own tracer before importing anything, so
  module-level lines are measured too.
- `.coveragerc` sets `parallel = true`: each process writes its own
  `.coverage.<host>.<pid>.<rand>` data file. An absolute
  `COVERAGE_FILE` (also in `COVERAGE_ENV`) keeps them all in the repo
  root — `bin/test` exits with `parts/test` as cwd and test-spawned
  processes chdir into throwaway dirs, so a relative data file would
  scatter or vanish.
- `[paths]` in `.coveragerc` folds the fake-release eggs the update
  tests build (`*/eggs/v5/zc.buildout-*.egg/zc/buildout`) back onto
  `src/zc/buildout` — they package the current source, and without the
  mapping `coverage report` aborts with "No source for code" once the
  tmpdirs are gone.
- After the suite, `bin/coverage combine` merges the data files and
  `bin/coverage report` / `bin/coverage html` render them. Use
  `bin/coverage`, never `python -m coverage`: the bare venv python has
  no coverage installed (coverage comes from the `[py]` eggs).
- `[run] disable_warnings = trace-changed` exists because the
  debugging tests drop into pdb, which replaces the trace function;
  coverage's warning would otherwise pollute that subprocess's
  expected output.

History: the pre-sitecustomize machinery (`setup_coverage()` gated on
`RUN_COVERAGE`, plus `buildoutSetUp` patching the sample `bin/buildout`
script) was removed — the patched script could not import coverage,
and the patch made a later buildout run regenerate the script, adding
output lines that broke `allowhosts`-style tests.

## What the numbers mean

- `source = zc.buildout` is matched by module name, so only code
  imported as `zc.buildout.*` is measured.
- `[run] omit = */tests/*` keeps test code out of both reports: the
  legacy harness modules, the ported pytests suite, and the
  `gen_pytest`/`inject_prose` helpers. The pattern also matches the
  copies inside the fake-release eggs the update tests install.
  Coverage measures the library, not the test code.
- `*/_package_index.py` is omitted by decision: the module vendors
  setuptools' package index client and is scheduled for removal once
  package discovery and downloads move to uv. Both reports list the
  11 remaining library modules and TOTAL describes the code that
  survives the migration.
- pytest imports the ported tests under their real
  `zc.buildout.tests.pytests.*` name because pyproject sets
  `consider_namespace_packages = true` (`src/zc/` is a namespace
  package). Without it, pytest's default import mode walks up only to
  `src/zc/buildout` and imports the tests as `buildout.tests.*`: a
  second, alias copy of the package. The alias defeated the name match
  (every `test_pytest_*` file reported 0%) and poisoned coverage's
  per-file disposition cache, so `src/zc/buildout/__init__.py`
  reported 0 lines under the pytest suite.
- Both reports now contain library modules only, so TOTAL compares
  across suites. The two suites still exercise different amounts of
  the library; expect the legacy report to be the higher,
  authoritative one.

## Sub-features

- `coverage-legacy` — `make coverage`: full legacy suite under
  coverage, then combine/report/html. Slow: the suite is ~8-10 min
  plain, and coverage 5.1 runs without its C extension here (pure
  Python tracer), so budget roughly 3x that. The official coverage
  truth.
- `coverage-pytest` — `make coverage-pytest`: pytest suite under
  coverage (~3-4 min with xdist). The fast coverage loop.
- `coverage-unittests` — `make coverage-unittests`: only the unit
  tests under coverage, the pytest tests that take no integration
  fixture from the pytests conftest (`--unittests-only`; builtin
  fixtures like tmp_path keep a test selected, the autouse
  `reset_easy_install_globals` is not an argument). Answers "what of
  the library do the unit tests alone execute", without the ported
  doctests' sandbox drives.
- `coverage-scoped` — hand runs for iteration, mirroring
  `suite-scoped`: set the same env as the Makefile (`COVERAGE_ENV`)
  and scope the suite, e.g. `bin/test -pvc -t buildout.txt` or one
  pytest file with `-n 2`.

## How to get to it (user POV)

- Repo root: `make coverage`, `make coverage-pytest`,
  `make coverage-unittests`. Reports print to the console; HTML lands
  in `htmlcov/`.
- CI: the `coverage legacy`, `coverage pytest`, and `coverage
  unittests` jobs run in parallel with the windows job and upload
  `htmlcov/` as artifacts (`coverage-legacy-html`,
  `coverage-pytest-html`, `coverage-unittests-html`).

## Driving it with shell

Preconditions: doctor all-OK; run from the repo root (suites drive in
the repo root, see repo-test-suites).

- `make coverage 2>&1 | tee "$ART/make-coverage.log"`. Exit 0; capture
  the testrunner totals line AND the report TOTAL line.
- `make coverage-pytest 2>&1 | tee "$ART/make-coverage-pytest.log"`.
  Exit 0; capture the pytest `passed` line and the report TOTAL line.
- Cleanup between runs is in the targets (`rm -f .coverage .coverage.*`).
  Never glob `.coverage*` by hand: it also matches `.coveragerc`.
- A report that aborts with `No source for code: ...` means a
  subprocess ran zc.buildout from a path that no longer exists and the
  `[paths]` mapping needs a new entry — do not paper over it with
  `coverage report -i` without understanding which path appeared.

## Gotchas

- All the `make pytest` PYTHONPATH gotchas apply (see
  repo-test-suites): if you invoke the coverage variants by hand,
  replicate the Makefile's `COVERAGE_ENV` exactly.
- Never run the two coverage suites (or any suites) concurrently —
  same CPU-starvation flakiness as the plain suites.
- `htmlcov/` and `.coverage*` are run artifacts; `.gitignore` covers
  them. The coverage targets delete both before regenerating, so a
  report always matches the run that produced it.
- The sitecustomize hook is import-tolerant on purpose: a Python
  process that has the env vars but no coverage egg importable runs
  untraced instead of crashing the suite.
- The CI `coverage pytest` job reproduces locally as-is:
  `make coverage-pytest` is the same sitecustomize instrumentation
  under the same `-n auto`. A failure that appears only on that CI
  job (observed: the order-dependent `prefer_final` doctest failure)
  is reproducible here — no runner round-trip needed.
- Parallel data files land in the repo root THROUGHOUT the run: every
  traced interpreter writes its `.coverage.<host>.<pid>.<rand>` at
  exit, including mid-narrative of another test. Code under test that
  hashes directory contents (the develop-dist `_dir_hash` signatures)
  sees them appear and flips — spurious Uninstalling/Installing where
  Updating was expected. `_dir_hash_file_ignored` carries the
  `.coverage*` prefix; any new tooling that drops files into the
  suite's working tree extends that ignore list in the same change.
- `_dir_hash` caches by path string: two tests hashing the same
  directory name inside one xdist worker share the cache entry. Give
  each test a private directory name (the regression tests mirror the
  SOURCES.txt pattern).
