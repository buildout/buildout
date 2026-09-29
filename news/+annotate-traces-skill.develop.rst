``annotate-from-traces`` skill documents the MonkeyType traced-suite
pipeline for annotating existing modules: subprocess tracing via
``make test-traced``, purging test-double traces before the libcst
apply, the human pass over tracer blind spots, repo typing precedents
(``TextIO`` over ``TextIOWrapper``, ``Mapping`` versus invariant
``Dict``, documented escape hatches), the modern-syntax dialect behind
``from __future__ import annotations``, and the before/after ``ty``
log evidence discipline.
[gotcha]
