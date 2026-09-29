## Static tier (ty)

`make typecheck` gates on Astral's `ty` (provided by the devenv) at zero
diagnostics over the checkout, with the test eggs on its search path.
Run it before committing typing-adjacent work and keep the gate at zero.

Clearing diagnostics, in order of preference:

- Narrow truthfully. Optional producers (`working_set.find`, Popen
  pipes, `options.get`) get real guards in library code and
  `assert x is not None` in tests. `self.assertIsNotNone` does not
  narrow for ty — add the bare `assert` where the value is consumed.
- Fix the call when the call is wrong. A shifted positional call in a
  test patch once survived only because a cache fallback swallowed the
  TypeError; the diagnostic exposed a latent bug, not a typing gap.
- Scoped `# ty: ignore[rule]` with the reason inline is the convention
  for corners that cannot be typed truthfully: version-compat branches
  behind runtime guards (old-pip signatures), platform-only attributes
  (`sys.pypy_version_info`), deliberate instance shadows. Name the
  guard or the version in the comment.

Generated pytest ports (`test_pytest_*.py`) come from `gen_pytest.py`
over doctest sources (`.txt` files, `test_all.py` docstrings):

- Edit doctest source and generated port in lockstep, so a regen
  reproduces the port.
- Trailing comments in doctest code do not survive generation, so a
  line-level suppression cannot come from the source. Prefer truthful
  fixes in ported code; a suppression hand-added to a port is lost on
  the next regen.
- Every regeneration pairs with an `inject_prose.py` re-run, and
  `inject_prose.py --check` anchored and unplaced counts must hold or
  improve against the pre-edit baseline. The prose comments in the
  ports preserve the doctest narrative for readers; a dropped or
  displaced prose block is a regeneration defect, not cosmetic loss.
  If an edit moves an anchor (an example's first emitted statement),
  fix the anchor, never delete the prose.

### Regenerating (or lockstep-editing) a port, in practice

There is no regen driver: `gen_pytest.py` has no CLI despite its
docstring, and its emitters (`emit_fn_from_txt`,
`emit_fn_from_docstring`) produce single-line `{expected!r}` literals
while the committed ports are hand-polished (triple-quoted expected
blocks, prose comments, `capture_print(ls, x)` call shapes). So today
a byte-exact regen of a committed port does NOT reproduce it. The
workflow that keeps the invariant, smallest first:

- **Small expected-output change** (the common case, e.g. a listing
  gains a line): edit the doctest source AND the same block in the
  port, by hand, in the same commit. Then run the affected ported
  tests plus the legacy file, and finish with `inject_prose.py
  --check` (run from `src/zc/buildout/tests/pytests/` with `bin/py`)
  against baseline counts captured before the edit.
- **Structural change** (examples added/removed/moved): regenerate
  the single function with the emitter and diff it against the port
  function with its prose comment lines stripped; every drift line is
  either a lockstep miss or known formatting drift. Apply the
  semantic part to the port, keep the hand polish.
- Some legacy examples have no live port counterpart: an
  unexpressible assertion (e.g. the tuple-assigned `ls()` pair in
  init.txt) lives on as a `# TODO assert:` comment in the port.
  Editing such a source spot changes no port code; say so in the
  commit message.
- One legacy source can map to several port functions
  (`split-long-pytests` split the big ones), so grep the port for the
  expected text to find the right function; do not trust the
  `test_<stem>` naming the emitter would use.
- The port-to-source mapping for `inject_prose.py` lives in its
  `SPECS` table. New ported files join that table in the same commit.

