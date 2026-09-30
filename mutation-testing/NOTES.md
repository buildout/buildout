# Mutation testing exploration — legacy vs ported pytest suite

Date: 2026-09-10. Question (Gotcha): are there mutations that break one
suite but not the other? Scope: the query/annotate region of
`src/zc/buildout/buildout.py` (lines 1392–1450), freshly mirrored in both
suites (legacy `configuration.txt` "Query values" ↔ pytest
`test_pytest_buildout_txt.py`).

## Kill matrix (semantic mutations, both suites scoped)

rc=0 → suite green → mutant SURVIVED; rc≠0 → KILLED.

| Mutation | legacy | pytest |
|---|---|---|
| M0 baseline (unmutated) | pass | pass |
| M1 `--interpolated` returns raw (drop cooked branch) | KILL | KILL |
| M2 empty section/option accepted (`:port`, `values:`) | KILL | KILL |
| M3 `a:b:c` not rejected cleanly (len check off) | KILL | KILL |
| M4 missing key prints None instead of error | KILL | KILL |
| M5 `annotate --interpolated` returns raw | KILL | KILL |
| M6 `if value is not None` guard removed | survive → KILL | survive → KILL |
| M7 deepcopy → shallow copy in `_interpolated_annotated` | survive | survive |

Kill patterns agreed 7/7. No mutation broke one suite but not the other.

The two double-survivors are the instructive part:

- **M7 is an equivalent mutant for CLI-level suites**: every
  `bin/buildout` invocation is a fresh process, so corrupting shared
  in-memory state across calls is invisible to BOTH suites. Expect a
  class of unkillable mutants for any process-isolated CLI.
- **M6 survived because the path was never exercised**: the guard only
  matters when `_annotated` holds a key the Options layer lacks. That
  happens with section extension (`<=`): `_do_extend_raw` pops `<` from
  the Options view, so `options.get('<')` is None while `_annotated`
  still carries the `<` SectionKey. FIXED 2026-09-10: both suites now
  test `annotate --interpolated` on an extending section (legacy
  `configuration.txt` "Query values" ↔ pytest
  `test_configuration_query_values`); without the guard the mutant
  dies with AttributeError (None.splitlines) in BOTH suites.

## Coverage cross-check (scoped, `bin/coverage3`)

- Legacy `bin/test -t configuration.txt` alone: region 1392–1450 fully
  covered (no uncovered lines).
- Pytest mirror file alone: same region fully covered.

## Tooling

- `mutmut` 3.7.0 installs cleanly inside devenv (`uv tool install
  mutmut`). mutmut drives pytest natively; for the legacy
  zope.testrunner suite, wrap `bin/test -t <name>` as a custom runner or
  apply mutants via git (see `mutation-testing/harness.sh`).
- Cost model: mutants × suite runtime. Full-module mutmut against an
  8-minute legacy suite is not loop-friendly; scope per module, or use
  semantic hand-mutations on freshly ported seams (the 80/20 used here).

## Suggested standing practices

1. Kill-matrix on any newly mirrored/split region as part of the porting
   checklist.
2. Coverage-diff per region (cheap, shown above) as a sanity gate.
3. Revert-as-mutation: revert a historical bugfix, confirm BOTH suites
   go red.
4. If systematized: mutmut scoped via `paths_to_mutate` per module,
   nightly CI, never per-commit.

## Harness lessons (2026-09-30 scoped rounds)

- Write the harness in Python with mutants as data (a list of
  (name, old, new) pairs), not as generated bash. Nested shell quoting
  (`${...}` in patterns, macOS `sed -i ''` argument order) silently ate
  four rounds of mutants in one day. Bash glues the runs; it must never
  carry the mutant payloads.
- Guard against vacuous runs: assert the legacy selector matched >0
  tests before trusting a "survive". zope.testrunner prints
  "Total: 0 tests" for a misspelled `-t` name and exits 0. Strip ANSI
  color codes before grepping the summary, and note the wording differs:
  real runs say "Ran N tests", empty runs say "Total: 0 tests".
- Classify every survivor before writing tests: gap (assert it),
  equivalent (record it), or dead/defensive (delete or justify it).
  The 2026-09-30 configfiles.py round survived 6/6 mutants against 78
  real extends tests; the working hypothesis is unreachable
  bugfix-era branches, to be settled by a full-suite coverage run.
