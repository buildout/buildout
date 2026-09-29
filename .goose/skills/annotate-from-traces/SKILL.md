---
name: annotate-from-traces
description: Add type annotations to existing zc.buildout modules from MonkeyType traced-suite runs. Trace with make test-traced, purge test-double traces before applying, human-review the tracer drafts, and prove the ty delta with before/after logs. Use when annotating code that already exists; for new code, the develop-buildout skill's annotation rules apply instead.
---

# Annotate from traces

Pipeline for annotating modules that already exist, built during the
2026-09 pass that annotated rmtree, utils.normalize_name, download,
pep425tags, configparser, _package_index, easy_install, and buildout.py
from MonkeyType traces. Every rule below is backed by a measured
incident from that pass. Sibling docs: develop-buildout covers the ty
gate, the mypy explicit-Any burndown (``make typecheck-any``), and
annotations for new code.

## The pipeline

1. Trace the suite with ``make test-traced``.
2. Purge test-double traces from the trace database.
3. Apply with MonkeyType (libcst).
4. Human pass over the drafts (blind spots and judgment calls below).
5. Capture before/after evidence logs; state the ty delta in the
   commit message.
6. Commit one module at a time, smallest first.

## Tracing: subprocess coverage or it did not happen

``make test-traced`` installs a sitecustomize hook so MonkeyType traces
across subprocesses. Without it the CLI entry paths are invisible to
the tracer: the buildout.py pass went from 54 to 96 traced qualnames
when subprocess tracing came online, and annotate/query/init/setup,
print*, addToValue, and removeFromValue only appear in traces from
that moment. Annotations drafted from main-process-only traces miss
exactly the functions users call first.

## Purge test doubles before applying

Traces recorded under the test suite carry test-only types:
``zc.buildout.testing.Buildout`` / ``TestOptions``,
``testrecipes.Debug`` doubles. Two failure modes:

- A test double sharing a production name (the testing Buildout versus
  the module's own Buildout) makes the libcst apply ambiguous and
  breaks it.
- Test doubles that do apply leak test scaffolding into production
  signatures.

Grep the trace store for testing modules before applying. Measured in
the buildout.py pass: 473 traces purged, vast majorities of real
traces retained everywhere. Three functions whose traces were 100%
test-flavored (``__setitem__``, ``parse``, ``print_options``) were
hand-annotated from their bodies instead.

## MonkeyType's mechanical blind spots

Budget a human pass over every draft; the tracer's gaps are known and
repeatable:

- Forward references come back bare. MonkeyType only quotes same-class
  self-references. Quote the rest by hand: ``Type['Buildout']``,
  ``Dict[str, 'SectionKey']``, methods referencing classes defined
  later in the module.
- Single observations overfit. A ``None``-only observed default became
  ``Optional[List[str]]`` for ``main(args)``; ``Tuple[()]`` and
  one-tuple observations were widened the same way.

## Judgment calls, with repo precedents

- ``TextIO``, not ``TextIOWrapper``, for file parameters whose callers
  pass ``open()`` results (``_print_options``, ``_save_option(s)``).
- ``Mapping`` for read-only dict parameters, so ``Dict`` call sites
  pass invariance (``_save_installed_options``).
- A ``Dict[Any, Any]`` union member can be a deliberate gradual-typing
  escape hatch, not noise. ``Dict`` is invariant; dicts mutated in
  place from raw to annotated values need the ``Any`` member.
  Collapsing them was tried in the buildout.py pass and produced 4
  spurious assignment diagnostics. Note: the explicit-Any burndown
  gate (``make typecheck-any``) counts explicit ``Any``, so an escape
  hatch like this must be argued in the commit message and may need a
  baseline entry.
- Deliberate protocol violations are a legitimate outcome when
  recorded. ``Options.get``/``keys`` stay incompatible with the
  ``Mapping`` protocol (extra ``seen`` parameter, ``List`` return);
  kept and documented as LSP findings in the commit message.

## Dialect: modern syntax behind the future import

Core modules carry ``from __future__ import annotations`` at the top.
Add it first when annotating a module that lacks it; the import is
what makes builtin generics and unions safe at runtime on the 3.9
support floor. With it in place, write ``list[str]`` and
``str | None``, not ``List``/``Optional`` from typing. Keep typing
imports for what builtins cannot express (``TextIO``, ``Protocol``,
``TypeAlias``). Match the file's existing dialect when it differs.

## Evidence discipline

Keep per-module before/after logs (``ty-baseline``, ``ty-after-*``,
``ty-final``, plus the suite logs) so the claim "new diagnostics are
true positives, none invented by annotations" is checkable by diffing
rather than asserted. State the delta in the commit message; the
buildout.py pass read "ty 204 -> 246" and enumerated the new families.

An annotation commit that raises the diagnostic count must say so and
name the families. Never raise it silently.

## New diagnostics are a findings backlog

Treat annotation-revealed diagnostics as latent code truths, not
annotation defects. The annotation commit names the families; a later
code-decision pass owns fixing or documenting each. Families found in
the 2026-09 buildout.py pass, for reference: unguarded
``.split()``/``.strip()`` on ``str | int | None`` option values,
SectionKey raw-versus-annotated dict mixing, ``cloptions`` rebound
mid-body (since fixed via ``_cloptions_dict``), ``_bool_names`` keyed
``str | bool`` indexed with ``int``, decorator attribute injection
(``command()`` sets ``.buildout_command``).

## Commit shape

One module per commit, smallest first; the 2026-09 order (rmtree,
utils.normalize_name, download, pep425tags, configparser,
_package_index, easy_install, buildout) let each commit be reviewed
against its own before/after logs. Each commit carries a towncrier
news entry per the develop-buildout rules.
