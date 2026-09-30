Extend the pytest mirror with verbose ``annotate`` coverage: the
``-=`` directive's history sub-block and history print order are now
asserted. The 2026-09-30 mutation round confirmed the corresponding
mutants (dropped REMOVE history entry, reversed history) are not
reachable through the annotate CLI rendering in either suite; they are
recorded as an equivalent-mutant class. [gotcha]
