## Dagger CI module

The workflow matrix is mirrored by a Dagger module in `dagger/`
(`dagger.json` pins the engine; code in `dagger/src/buildout_ci/`),
so CI also runs locally via `dagger call ci`. Rules for changing it:

- The Job table lives in `dagger/src/buildout_ci/jobs.py` as pure
  data (no dagger import). Every matrix edit in `run-tests.yml` must
  keep that table — and the workflow's dagger family matrix — in
  sync; `dagger/tests/test_jobs.py` fails on drift.
- A cell whose make target needs a devenv-provided tool pip-installs
  it pinned to the devenv version (`pip_install` on the Job row:
  ruff, ty, radon), so the container gate matches the local gate by
  construction.
- The module's own harness runs via `dagger call ci --family module`
  (or plain pytest over `dagger/tests/` for the fast loop). Run it
  before committing module changes; it is also a family in the
  workflow's dagger matrix, so CI runs it too.
- Module (`dagger/src/`) and `news/` edits do not invalidate the job
  cells' engine cache by design — keep it that way.
- Cells fetch from PyPI directly; there is no proxy container. The
  per-command 3-attempt retry on transient fetch signatures (both
  "No matching distribution" wordings, connection resets, timeouts) is
  PyPI-outage tolerance — keep it, and add newly observed transient
  wordings to `TRANSIENT_SIGNATURES` when CI shows one.
- Verify with the dagger axis first when the result must match CI
  (module, workflow, or bootstrap-path changes): `dagger call smoke`
  before the suites when `prepare.sh`/`Makefile`/`devenv.nix` moved,
  after the suites on the push candidate otherwise. The full reasoning
  and the cache expectations live in verify-buildout ("Daggerized CI
  axis").
- When a cell fails, an exec error's `str()` is only `exit code: N`;
  the real output lives on the exception's `stdout` / `stderr`
  attributes. The module's `_exec_output` helper extracts them — keep
  any change to failure handling going through it, or diagnosis loses
  the output.
- `ReturnType.ANY` on an exec caches its result *including a nonzero
  exit*. A retry loop must issue a fresh exec per attempt; reusing an
  ANY-typed call replays the cached failure. (This is why the
  transient-retry loop in `main.py` builds each attempt separately.)

## Running dagger locally: devenv shell, podman engine

The `dagger` CLI is not on the ambient PATH — the devenv provides it
and wires it to a local engine. Invoke it through the shell from the
checkout root: `devenv shell -- dagger version`. The moving parts:

- The engine runs as a container on the devenv's podman machine
  (machine `devenv`, engine container `devenv-dagger`, image pinned by
  `dagger.json`'s `engineVersion`). The shell exports the runner host
  (`container+podman://...`) that points the CLI at it.
- **Start sequence after a reboot or sleep:** `devenv up -d`.
  The repo declares `services.dagger` (auto-enabling
  `services.podman-machine`), so the native devenv services converge
  the machine AND the engine container in one detached command
  (measured 16.8s from fully-down). The manual podman ladder remains
  the surgical fallback when you know exactly which piece died:
  `connection refused` on the podman socket →
  `podman machine start devenv`; machine up but `dagger call` errors
  → the engine container has exited
  (`podman --connection devenv ps -a` shows it — start it with
  `podman --connection devenv start devenv-dagger`).
- **Name the connection explicitly.** The default podman connection
  can point at a *different* machine than the one hosting the engine
  (observed: default connection to a stopped `podman-machine-default`
  while the engine lives on `devenv`), so bare `podman ps` fails or
  looks at the wrong machine. Always `podman --connection devenv ...`;
  check `podman system connection list` when in doubt.

Reproducing one CI leg locally:

- `dagger call families` lists the families; the cell names are the
  Job table in `dagger/src/buildout_ci/jobs.py`. Run one cell with
  `dagger --progress=plain call job --name setuptools-65.7.0`
  (`--progress=plain` keeps the log greppable; a suite cell takes
  10-25 min and is cached until its inputs change).
- `dagger call debug --name <cell> terminal` drops you into the
  container in its failed state — poke the exact CI environment
  instead of guessing at it.
- In CI logs and `--progress=plain` output, numbered cells map to
  their pins via the `withEnvVariable SETUPTOOLS_VERSION=...` /
  `withEnvVariable PIP_VERSION=...` lines — grep those to identify
  what a failing numbered leg actually ran.
- **Never background a dagger call from an agent shell.** When the
  shell session ends, its children get SIGTERM and the engine
  connection dies mid-run (`podman exec ... dial-stdio ... signal:
  terminated`). macOS has no `setsid`, and `nohup` does not help. Run
  it foreground in one long-lived call with a generous timeout, or
  hand it to a subagent whose turn exists for that purpose — and post
  the result the moment it exists (see "Turn budget").
- **A killed run costs only its unfinished legs.** Host sleep stops
  the podman machine mid-family; a session end SIGTERMs the CLI.
  Either way the exec-layer cache holds every completed leg, so the
  recovery is: revive the engine (above), re-issue the exact same
  `dagger call ci --family <name>` — cached legs report PASS in
  seconds and only the interrupted legs re-execute.
- **A call's workspace freezes at call time.** `Directory` arguments
  upload once when the call starts: a running family sees exactly the
  tree it was launched on, even if the worktree goes dirty mid-run.
  Record `git rev-parse HEAD` at launch and the run is attributable
  to that commit; edits made during a run wait for the next call.

## Pre-test CI locally before pushing

Pushing to learn what CI thinks costs a runner round-trip per
iteration. The dagger mirror replays the same matrix in local
containers, so the cheap loop is: iterate with the native `make`
targets, commit, run the dagger cells on the committed tree, push
only what they pass. Two days of CI debugging on the uv-installer
branch (2026-09-23/24) measured the boundary:

- **What local cells catch.** Container-axis and version-matrix
  bugs. The old-style-wheel `.dist-info` discovery bug failed the
  dagger uv cells while macOS-native runs and the GHA ubuntu legs
  stayed green; the py3.10-only `tomli` seed gap was invisible from
  the py3.12 native surface, and the local python-matrix cells span
  3.9–3.14. The `static` family replays lint, typecheck, and
  complexity in-container.
- **What they cannot catch.** The GHA runner's ambient environment
  (the `RUST_LOG=debug` flood lived on the runner, in no container),
  the Windows legs (the module builds Linux containers only), the
  macOS leg's devenv evaluation, and network flakes. Green local
  cells narrow the push risk; for those axes the runner run stays
  the only proof.

Two rules make the gate trustworthy:

- **Static gates on the committed tree.** A green `make typecheck`
  on a pre-commit tree says nothing about the push candidate: a
  commit that adds a type error after the gates last ran pushes red
  (observed: `e2dd3541` failed the ty leg and the dagger static leg;
  fixed in `233658dc`). Run the static gates — or `dagger call
  smoke`, which includes the static family — against the exact
  commit you will push, never against uncommitted state.
- **Exploit the caches instead of paying cold start.** The engine
  caches at two levels (measured numbers in verify-buildout,
  "Daggerized CI axis"): an unchanged cell reruns in seconds on the
  exec-layer cache, and per-Python pip/uv cache volumes carry the
  bootstrap fetches across cells and runs. `news/` and
  `dagger/src/` edits do not invalidate job cells, so a news-only
  commit reuses the whole previous run. The payoff inverts when the
  engine is cold: after days idle the engine container is often
  stopped, and the cold start once ate five minutes of a turn
  before the first cell ran — check the engine first (see "Running
  dagger locally"), so the turn budget goes to cells, not to the
  engine waking up.

