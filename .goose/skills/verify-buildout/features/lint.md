# Static lint (ruff)

`make lint` runs `ruff check .` over the whole tree — a fast static
gate (seconds, no bootstrap needed beyond git) that complements the
behavioral suites. It proves code hygiene, never behavior: a green
lint says nothing about what buildout does, and a red lint is not a
suite failure. The deep proof layers remain `make test` /
`make pytest` (see [repo-test-suites](./repo-test-suites.md)).

## Sub-features

- `lint-check` — `make lint` runs `ruff check .` from the repo root.

## How to get to it (user POV)

- Repo root, inside `devenv shell`: `make lint`.
- By hand: `ruff check .` (same thing — the target is a thin wrapper).

## Driving it with shell

Preconditions:

- Inside `devenv shell` — ruff ships with the devenv (devenv.nix), it
  is not installed into `bin/` or the venvs.
- No doctor preconditions: lint does not need `bin/`, `venvs/`, or
  `eggs/` — it reads only the source tree.

Drive:

- `make lint 2>&1 | tee "$ART/make-lint.log"`. Exit 0 prints
  `All checks passed!` — capture that line.
- On failure ruff lists each violation as `RULE description` with a
  `file:line:col` pointer and a context window; exit code is 1.

Reading a failure:

- A violation in code your change TOUCHED: fix the code, not the
  config.
- A rule fighting a deliberate legacy pattern: extend `ignore` (or
  `per-file-ignores`) in `[tool.ruff.lint]` in `pyproject.toml`, with a
  comment saying why — and say so in the change report. Widening the
  baseline to silence a real defect is a lint bypass, not a fix.

## Gotchas

- The rule set is a PINNED BASELINE, not ruff's defaults: ruff >= 0.16
  defaults to a very wide rule set that this legacy tree violates
  wholesale (600+ findings). `pyproject.toml` selects the classic set
  (`E4`, `E7`, `E9`, `F`) minus the rules the existing code trips
  (`E401/E402/E701/E702/E703/E713/E722/E731/E741`, `F401/F811/F841`),
  so `make lint` is green on a clean checkout and only bites on NEW
  violations of the enforced rules. Tighten by removing `ignore`
  entries as the code gets cleaned — that is the intended ratchet.
- High-signal rules ARE enforced and currently clean: `E9` (syntax),
  `F821` (undefined name), `F823`, `F541`. Treat any new hit there as
  a real bug until proven otherwise.
- ruff's version comes from the devenv nixpkgs pin (devenv.lock); the
  pinned `select` in pyproject.toml keeps the gate's meaning stable
  across ruff upgrades.
- Only `ruff check` is wired. `ruff format` is deliberately NOT
  enforced — this tree predates it and is not formatted.
- Do not run `ruff --fix --unsafe-fixes` on this tree: a 2026-09-12
  probe found it breaks the `While:` reporting code. Safe `--fix`
  output still needs review hunk by hunk before committing.
- `.ruff_cache/` is gitignored; stale cache is never a failure mode,
  but `ruff check --no-cache .` rules it out when triaging weirdness.
