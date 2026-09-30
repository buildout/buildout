# Repo test suites

Buildout's own behavior specification is executable and comes in two
suites: the legacy doctest/testrunner suite (`make test`) and the
ported pytest suite (`make pytest`). For a behavior-affecting change,
these are the deep proof layer beneath the CLI drives.

## Which suite proves what

- **The legacy suite (`make test`) is the official truth.** The
  pytest suite is a port and still too young to stand alone — a
  change is NOT verified until `make test` passes. Fast loops defer,
  never replace: every verification ends with the legacy suite.
- **The pytest suite is the development loop.** It is much quicker
  (~1 min vs ~8+ min for a full run), so iterate with it while
  developing — scoped single files, then full `make pytest` — then
  prove the change with `make test`.
- **Divergence rule:** if the legacy suite fails while the pytest
  suite passes, the pytest port is wrong — fix the pytest suite to
  match the legacy behavior, not the other way around.
- **Changing tested behavior:** when a change impacts existing tests,
  update BOTH suites in the same change.
- **Port confidence:** after mirroring or splitting a region, prove the
  two suites agree with a kill-matrix — see "Proving a port" below.

## Proving a port: kill-matrix

Both suites passing proves the CODE passes both — it does not prove both
suites would catch the same regressions. After porting or splitting a
test region (legacy `.txt` ↔ pytest mirror), mutate the freshly-mirrored
SOURCE code and check both suites kill the same mutants.

- **The pattern** (reusable harness: `mutation-testing/harness.sh`):
  pick a handful of semantic mutations on the ported region (flip a
  condition, drop a branch, weaken a validation); apply each as an
  exact-string replace; run the scoped legacy file
  (`bin/test -pvc -t <name>`) and the scoped pytest mirror file; rc≠0 =
  kill; `git restore` between mutants.
- **Read the matrix:** every mutant should die in BOTH suites. A
  one-suite kill means the port diverges — fix the pytest side (see the
  divergence rule). A double survivor means either an unexercised path
  (add a test to BOTH suites) or an equivalent mutant.
- **Expected survivor classes** (measured 2026-09-10 on the
  query/annotate region, `mutation-testing/NOTES.md`): guards on paths
  no test config exercises; and process-isolation mutants (e.g.
  deepcopy→shallow) are unkillable by CLI-level suites — every
  `bin/buildout` call is a fresh process. Do not chase those.
- **Companion gates:** a scoped coverage diff per region (both suites
  should cover the ported region fully) and revert-as-mutation (revert
  a historical bugfix, confirm BOTH suites go red).
- **Full mutmut runs are a nightly-CI tool, never per-commit:** mutants
  × suite runtime against an 8-minute legacy suite is not loop-friendly.

## Sub-features

- `suite-doctest` — `make test` runs the zope.testrunner doctest suite
  (`bin/test -pvc`). Several minutes. The official truth.
- `suite-pytest` — `make pytest` runs `src/zc/buildout/tests/pytests/`
  under xdist (`-n auto`). Much faster — the development loop.
- `suite-scoped` — both suites support scoped runs for fast iteration:
  `make test-small` (or `bin/test -pvc -t buildout.txt`) and
  single-file pytest invocations.
- `suite-killmatrix` — mutation kill-matrix proves legacy/pytest
  agreement on a freshly ported region (harness:
  `mutation-testing/harness.sh`); see "Proving a port" above.

## How to get to it (user POV)

- Repo root: `make test`, `make pytest`, `make test-small`.
- Hand-rolled scoped: `bin/test -pvc -t <test-name>`;
  `bin/py -m pytest src/zc/buildout/tests/pytests/test_<x>.py -q`.

## Driving it with shell

Preconditions:

- Doctor all-OK (both `bin/test` and `bin/py` present, `eggs/v5/`
  populated); run from the repo root — this is the ONE feature that
  drives in the repo root, because the suites are built to.
- Full runs go to `$ART`: `make test 2>&1 | tee "$ART/make-test.log"`.

- **Doctest suite.** `make test 2>&1 | tee "$ART/make-test.log"`.
  Exit 0; final lines report the testrunner totals
  (`Total: N tests, 0 failures, 0 errors ...`). Capture that line.
- **Pytest suite.** `make pytest 2>&1 | tee "$ART/make-pytest.log"`.
  Exit 0; final line `N passed ...`. Capture it.
- **Scoped smoke (fast proof).** `make test-small` and
  `PYTHONWARNINGS=ignore PYTHONPATH="$(ls -d $PWD/eggs/v5/*.egg | tr '\n' ':')" \
    bin/py -m pytest src/zc/buildout/tests/pytests/test_pytest_rmtree.py -q`.
  Both exit 0. Use these when the full suites are too slow for the
  question at hand, and say so in the report — a scoped smoke is
  iteration fuel, never the final proof (see "Which suite proves
  what").

## Gotchas

- The suites need no network package index: their setups
  (`buildoutSetUp`, both doc-suite setups) run every test-spawned pip
  with `PIP_NO_INDEX=1` and `PIP_FIND_LINKS=downloads/test-seed/`,
  where `prepare.sh` seeds the exact setuptools/wheel wheels it
  installed (build isolation on sdist and editable installs,
  `python -m build`). The uv resolve seam instead reads
  `downloads/test-seam-seed/` — the same seed minus the setuptools
  build-environment floor, which compiles must never upgrade to. A
  suite run with the ambient index pointed at a
  dead port is a valid hermeticity probe. Missing seed dir (suites run
  without `make bin/buildout`) silently restores the ambient-index
  behavior — when hermeticity matters, check the seed exists first.
  The seed download happens BEFORE the leg's pinned pip lands: pip
  < 24 misreads current PyPI metadata (observed: a pip 23.3.2 leg
  could not see a current platformdirs at all), so prepare.sh brings
  pip current right after venv creation, downloads the seeds under
  it, and only then installs `$PIP_VERSION`. Preserve that ordering
  when touching the bootstrap.
- Hand-invoking pytest WITHOUT the `PYTHONPATH=eggs/v5/*.egg` line
  breaks xdist workers (they are bare interpreters and do not inherit
  `bin/py`'s baked sys.path) — the Makefile comment says exactly this.
  Use `make pytest`, or replicate the PYTHONPATH. This applies to ANY
  `-n` invocation, including a scoped `-n 2` on one file (only
  `-n`-free hand runs are exempt): the workers fail collection with
  `ModuleNotFoundError` for the eggs and the file reports 0 passed —
  do not mistake that for a red suite.
- `make test` rebuilds `bin/test` via `bin/buildout` if the config
  changed — a suite run can rewrite repo-root state. That is normal;
  the doctor's dirty-tree NOTE records it.
- Both suites spawn subprocesses heavily; run them sequentially, never
  concurrently (`-n auto` plus the testrunner starves CPU and causes
  flaky timeouts).
- If `bin/` or `venvs/` is missing, rebuild first with the known-good
  pin: `PYTHON_VERSION=3.12 SETUPTOOLS_VERSION=75.8.2 make bin/buildout`.
- Failure triage: a red suite on an UNMODIFIED checkout means the
  environment drifted (new setuptools/pip), not necessarily the code —
  record `bin/py -m pip --version` and the venv's `pip freeze` into
  `$ART` before concluding anything.
- Suite disagreement is a pytest-port bug: legacy red + pytest green
  means the pytest suite must be fixed to match legacy. Behavior
  changes that impact existing tests update BOTH suites in the same
  change.
- Multi-Python verification: use the devenv CLI override, then
  rebuild and run the suites inside that shell:
  `devenv shell --option languages.python.version:string 3.10`, then
  `rm -rf bin && make bin/buildout && bin/buildout && make pytest &&
  make test`. venvs are keyed per Python version, so no `make clean`
  between versions — but `make bin/buildout` alone is mtime-keyed and
  no-ops after a version switch, leaving `bin/` scripts on the OLD
  interpreter; `rm -rf bin` forces dev.py to regenerate them. Prove
  the interpreter before trusting a run:
  `bin/py -c 'import sys; print(sys.version)'`.
