---
name: verify-buildout
description: Verify zc.buildout behavior by driving the real CLI the way a user does — running bin/buildout from this checkout against throwaway projects, exploring the composed configuration files with query/annotate, and running the repo's two test suites (make test / make pytest). Use when a change to this repo needs behavioral proof beyond unit tests.
---

# Verify buildout

zc.buildout is a CLI: a user writes a `buildout.cfg`, runs `buildout`,
and expects parts installed, scripts generated, and the composed
configuration explorable.
This skill drives exactly that loop with the `bin/buildout` built from
this checkout, plus the repo's two test suites as the deep proof layer.
The process side of a change — towncrier news entries and rebase-based
linear integration — lives in the sibling `develop-buildout` skill.

This skill is location-independent: it lives at
`.goose/skills/verify-buildout/` inside the checkout. Set `REPO` to the
checkout root on the current machine (the helper scripts derive it
from their own location, e.g.
`REPO=$(cd "$(dirname "$0")/../../../.." && pwd)` in `helpers/`).
No machine-specific path or branch name appears anywhere in this skill.
All commands assume
`export PYTHONWARNINGS=ignore` — the checkout still imports
`pkg_resources` on startup and the deprecation warning otherwise
pollutes every transcript.

## Launch

Buildout is a short-lived CLI — there is no server. "Launch" means:
build the runner once, then start each drive in its own throwaway
project directory.

Toolchain: enter `devenv shell` first (devenv.nix at the repo root).
It provides Python (default 3.12), git, gnumake, uv, coreutils,
towncrier (news fragments, see the develop-buildout skill) and ruff
(`make lint`), and exports `PYTHON_VERSION` + `USE_UV` +
`UV_VENV_CLEAR` + `SETUPTOOLS_VERSION=75.8.2` so the bootstrap below
just works.
Pick another supported Python (3.9–3.14) from the command line, no
file edit:

```sh
devenv shell --option languages.python.version:string 3.10
```

Switching versions needs no `make clean`: prepare.sh keys its venvs by
Python version (`venvs/python3.x`). But `make bin/buildout` is
mtime-keyed and no-ops when `bin/buildout` is up to date — it does NOT
notice the version change, and the stale script keeps the old
interpreter. Force regeneration and prove the interpreter before
trusting results:

```sh
rm -rf bin && make bin/buildout && bin/buildout
bin/py -c 'import sys; print(sys.version)'   # must show the override version
```

Without devenv, set the pins by hand:
`PYTHON_VERSION=3.12 SETUPTOOLS_VERSION=75.8.2` (unpinned setuptools
breaks the 5.x bootstrap).

One-time build (already done in a fresh checkout only if `bin/` is
missing):

```sh
cd $REPO
make bin/buildout        # = ./prepare.sh: venv in venvs/, pip deps, sdist, dev.py
```

Per-drive launch:

```sh
D=$(mktemp -d /tmp/verify-buildout.XXXXXX) && cd "$D"
printf '[buildout]\nparts =\n' > buildout.cfg
```

Ready check: `bin/buildout --version` prints `buildout version 5.2.x`
without a traceback.

Teardown: `rm -rf "$D"` — but only AFTER evidence is copied out (see
Evidence). Never run drives in the repo root: `bin/buildout` there
rewrites `.installed.cfg`, `parts/`, `eggs/` — shared state the test
suites depend on.

## Doctor

One read-only check answering "is this checkout worth driving?". Run
the helper (ships with this skill, executable):

```sh
$REPO/.goose/skills/verify-buildout/helpers/doctor.sh
```

It checks, printing OK/FAIL per line and exiting non-zero on any FAIL:

- `bin/buildout --version` runs and reports 5.2.x (runner built, importable)
- `bin/test` and `bin/py` exist (suite runners ready)
- `venvs/` has a python (bootstrap venv present)
- `git -C <repo> rev-parse HEAD` and `status --short` — record the exact
  revision driven, and whether the tree was dirty
- `eggs/v5/` exists (pytest suite needs its eggs on PYTHONPATH)
- `ty --version` on PATH (Astral checker for the static tier; the
  devenv provides it)

Run the doctor first whenever anything looks off; a FAIL there
invalidates everything downstream. If `bin/buildout` is missing,
rebuild with `make bin/buildout` (pins above).

## Drive

Harness: plain shell. The app under test is
`$REPO/bin/buildout` — a dev install of
this checkout, so every drive exercises the current source tree. Every
drive runs in its own `mktemp -d` project dir with its own
`buildout.cfg`. That is complete isolation: two drives can run side by
side as long as each has its own `$D`. The only shared, mutable state
is the pip download cache (`~/.cache/pip`) — reads/writes there are
safe but mean "offline" behavior is not truly hermetic unless pip is
starved; see Gotchas in the feature files. (The suites, by contrast,
ARE index-hermetic: their spawned pips run with `PIP_NO_INDEX` against
seeded wheels — see [`features/repo-test-suites.md`](./features/repo-test-suites.md).)

Feature recipes live in [`features/`](./features/README.md) — read the
index, then follow the feature file. The tiers:

1. **Hermetic** (no network): empty-parts install, rerun modes,
   `query`/`annotate`, command-line assignments, `-U`.
2. **Networked**: real part install (`zc.recipe.egg` via local
   `develop`, published egg from PyPI), `init`/`bootstrap`. Requires
   network or a warm pip cache.
3. **Suites** (the deep proof): the repo has TWO suites, run from the
   repo root. Hierarchy: `make test` is the official truth — no change
   is verified until it passes; `make pytest` is the fast development
   loop, still too young to stand alone. If legacy fails while pytest
   passes, the pytest port is wrong — fix pytest to match. A change
   that impacts existing tests updates BOTH suites.

Alongside the tiers, `make lint` (ruff, from the devenv) is a
seconds-fast static hygiene gate — see
[`features/lint.md`](./features/lint.md). Next to it sits the
complexity budget gate `make complexity` (radon, from the devenv;
baseline `etc/complexity-baseline.json`, line-pinned — any
line-shifting source edit can fail it, so it rides in every
verification) — see
[`features/complexity.md`](./features/complexity.md). Both complement
the suites and never substitute for them.
   - `make test` — legacy doctest/testrunner suite (`bin/test -pvc`).
     The official truth. Several minutes — long enough for the
     turn-budget rules in develop-buildout: announce the run and
     checkpoint state before starting it. Always capture the output
     (`make test 2>&1 | tee /tmp/buildout-test-<label>.log`): a
     several-minute rerun is too slow to be the way you re-read a
     failure, and the log survives the turn. The logs are scratch
     artifacts — never commit them, and delete them once the suite
     passes. Scoped smoke:
     `make test-small` (single `buildout.txt` file) or
     `bin/test -pvc -t <name>`.
   - `make pytest` — ported pytest suite in
     `src/zc/buildout/tests/pytests/`, run with xdist
     (`bin/py -m pytest ... -n auto`). The development loop — iterate
     here, prove with `make test`. The Makefile passes
     `PYTHONPATH=eggs/v5/*.egg` because xdist workers are bare
     interpreters that do not inherit `bin/py`'s baked sys.path — if
     you invoke pytest by hand, you MUST set that PYTHONPATH yourself.
     The requirement rides with `-n`, not with the full suite: a
     scoped run with `-n 2` breaks just the same; only `-n`-free
     hand runs are exempt. The symptom of forgetting it: every
     worker errors at collection with `ModuleNotFoundError` for the
     eggs, so the file reports 0 passed.
     Scoped smoke: one file, e.g. `... test_pytest_rmtree.py -q`.
   - `make coverage` / `make coverage-pytest` — coverage variants of
     both suites: every spawned interpreter is traced via
     `etc/coverage/sitecustomize.py` on PYTHONPATH, then
     `bin/coverage combine/report/html`. See
     [`features/coverage.md`](./features/coverage.md).
4. **Static** (type gate): `make typecheck` — Astral's ty over the
   checkout, with the repo venv as its Python environment and
   `_vendor/` excluded via `[tool.ty]` in pyproject.toml. Treat the
   diagnostic count like suite totals: record it, compare across
   runs. Zero is the target only after the per-module ratchet lands
   (easy_install.py and buildout.py stay lenient longest); until
   then the gate is the trend.

## Daggerized CI axis (use it first)

Filesystem-semantics changes are the case this axis exists for.
macOS and Linux disagree on directory-listing order and case
sensitivity, so a green local suite proves nothing about code that
reads directories positionally (`os.listdir(...)[0]`), globs, or
reasons about path case. Such a change is not verified until the
matching `dagger call job --name <cell>` passes in the Linux
container, whatever the local suite said.

The same blindness covers interpreter and platform facts. The local
cell is one Python on one OS; a fixture that hard-codes what the
interpreter could tell it — py3.12 egg tags, an unconditional
macOS-only platform egg — passes every local gate and fails on every
other matrix cell (observed: six IndexError failures across CI's
non-3.12 legs, invisible to the local py3.12 gates). Derive
interpreter facts from the running interpreter
(`sys.implementation.cache_tag`, sysconfig's platform), condition
platform-specific expectations, and let the dagger matrix — not the
local run — be the proof for any test module that embeds such facts.


The repo's CI matrix is mirrored by a Dagger module in `dagger/`:
`dagger call jobs` lists the cells, `dagger call job --name <cell>`
runs one, `dagger call ci [--family <name>]` runs a family or all,
`dagger call smoke` runs the fast self-check set (the static tier, the
module harness, one scripts cell; ~2 min warm). Reach for this axis
FIRST whenever the answer must match CI: environment-shaped questions
(does this pin set install? does the suite pass on 3.14?), workflow or
module changes, and the pre-push parity check. It adds no moving parts
beyond the engine: cells fetch from PyPI directly, with per-Python
pip/uv cache volumes for the bootstrap fetches. It never touches your
checkout's `venvs/`/`eggs/`.

Cache expectations (measured 2026-09-15, engine 0.21.9): an unchanged
repo reruns a finished cell in seconds (exec-layer cache); a static
cell costs ~10 min fully cold, seconds warm. A re-executed suite cell
saves only its bootstrap fetches (~10% of the cell) — budget a suite
cell at roughly its suite's wall time. Edits to project files (`src/`,
`Makefile`, `pyproject.toml`, …) invalidate the cells; module
(`dagger/src/`) and `news/` edits do not.

Order the smoke set by what the change breaks first: a bootstrap-path
change (`prepare.sh`, `Makefile`, `devenv.nix`) can void every suite
run, so run `dagger call smoke` BEFORE the suites; for suite-internal
changes run the suites first (they are the faster decisive probe) and
smoke last, on the exact tree you will push. The suites above stay the
official truth for behavior; the local `make` loop stays the
iteration tool for debugging a red test.

For changes to the dagger module itself, the proof ladder is its own
harness: `uvx --with pytest --with pyyaml python -m pytest
dagger/tests -q` for the fast loop, `dagger call ci --family module`
for the dogfooded run, then a real cell (`dagger call job --name
<cell>`) — the harness cannot see container behavior. Details and the
failure-reading recipe live in
[`features/ci.md`](./features/ci.md) ("The daggerized mirror").

Engine care: the engine runs in the devenv's podman machine. If dagger
calls hang at "connecting to engine" or die with a terminated
`podman exec`, check the container
(`podman --connection devenv ps -a --filter name=devenv-dagger`) and
start it (`podman --connection devenv start devenv-dagger`) — a podman
machine restart does not always bring it back. Keep long dagger calls
in the foreground of their shell: backgrounded with stdin closed, the
CLI's `podman exec -i` bridge gets EOF and the call dies mid-run.

## Evidence

Capture per drive, into a named artifacts dir that survives cleanup —
use `ART=/tmp/verify-buildout-artifacts-$(date +%Y%m%d-%H%M%S)` and
`mkdir -p "$ART"`; cleanup removes project dirs, never `$ART`.

Proof standards:

- Record per drive: the exact `buildout.cfg` used, the command, exit
  code, full stdout/stderr transcript (`| tee "$ART/<name>.log"`), and
  `git rev-parse HEAD` of the checkout.
- Static tier: `make typecheck 2>&1 | tee "$ART/typing.log"`; the
  "Found N diagnostics" line is evidence the same way suite totals
  are.
- Capture the action AND the resulting state: after an install, list
  the tree (`ls -la`, `ls bin/`) and verify the run's side effects on
  disk (next bullet).
- `query`/`annotate` are a separate, read-only axis: they explore the
  configuration FILES as composed — the `extends` chain above all,
  plus command-line assignments and defaults — printing each value
  with its origin (DEFAULT_VALUE / config / COMMAND_LINE_VALUE). They
  do NOT inspect the result of a run: installed parts and generated
  scripts are proven on disk, never through `query`/`annotate`.
- Verify side effects on disk, not just output: `.installed.cfg`
  contents, generated scripts in `bin/`, egg links in `develop-eggs/`.
  Note: with `parts =` empty, NO `.installed.cfg` is written — that is
  expected, assert it, don't "fix" it.
- For the suites: keep the final summary line (testrunner totals or
  pytest `passed/failed` line) plus the scoped or full run duration.
- Mocks: none. The only sanctioned offline substitution is the
  hermetic tier itself; never stub PyPI.

## Cleanup

- `rm -rf` each drive's project dir `$D` — only after evidence is in
  `$ART`. Nothing else: buildout is short-lived, no processes survive
  a drive.
- Never kill by process name. If a suite run must be aborted, kill the
  exact PID you started; xdist children exit with their parent.
- Do NOT run `make clean` as cleanup: it deletes `bin/`, `venvs/`,
  `eggs/` — the built environment the next run needs. `make clean` is
  a bootstrap reset, not drive cleanup.
- Proof artifacts in `$ART` are never removed by cleanup.

## Helpers

- [`helpers/doctor.sh`](./helpers/doctor.sh) — the Doctor check
  described above. Usage: `doctor.sh` (no args; absolute paths baked
  in). Prints `OK <check>` / `FAIL <check>`, exit 0 iff all OK.

## Feature map

See [`features/README.md`](./features/README.md). Current coverage:
install-and-inspect (hermetic core), configure-and-substitute,
rerun-modes, project scaffolding (init/bootstrap, networked), the two
repo test suites, their coverage variants (`make coverage` /
`make coverage-pytest`), static lint (`make lint`, ruff), and the
complexity budget gate (`make complexity`, radon).
