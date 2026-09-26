#!/bin/sh
# Explicit-Any burndown gate, driven by `make typecheck-any`.
#
# mypy --disallow-any-explicit is the only checker flag that catches
# nested Any (dict[str, Any]); ruff ANN401 sees bare Any only, and ty
# has no Any rule. The gate fails when the run reports a site that
# etc/any-burndown-baseline.txt does not know, so no new Any enters the
# tree while the burndown burns down. Deleting baselined lines is the
# progress mechanism; burndown commits drop the lines they fix, and a
# stale-line warning names baselined sites the run no longer reports.
# With an empty baseline the gate is plain disallow-any-explicit.
#
# `--write-baseline` replaces the baseline with the current report. It
# exists for line-drift refreshes; every baseline diff is reviewed in
# the commit that carries it.
set -eu
cd "$(dirname "$0")/.."
baseline=etc/any-burndown-baseline.txt

if ! command -v mypy >/dev/null 2>&1; then
    echo "typecheck-any: mypy not on PATH; enter the devenv shell (devenv-provided)" >&2
    exit 2
fi

current=$(mktemp)
trap 'rm -f "$current"' EXIT
mypy --config-file pyproject.toml src/zc/buildout 2>&1 \
    | sed -n 's/^\(.*:[0-9][0-9]*\): error: Explicit "Any" is not allowed.*/\1/p' \
    | LC_ALL=C sort > "$current"

if [ "${1:-}" = "--write-baseline" ]; then
    cp "$current" "$baseline"
    echo "typecheck-any: baseline rewritten from current report"
    exit 0
fi

count() { printf '%s' "$1" | grep -c . || true; }
sorted_baseline=$(mktemp)
trap 'rm -f "$current" "$sorted_baseline"' EXIT
LC_ALL=C sort "$baseline" > "$sorted_baseline"
new=$(LC_ALL=C comm -23 "$current" "$sorted_baseline")
stale=$(LC_ALL=C comm -13 "$current" "$sorted_baseline")
echo "typecheck-any: $(count "$(LC_ALL=C comm -12 "$current" "$sorted_baseline")") baselined explicit-any sites, $(count "$new") new (mypy $(mypy --version | awk '{print $2}'))"

if [ -n "$new" ]; then
    echo "typecheck-any: FAIL, new explicit Any sites:" >&2
    printf '%s\n' "$new" >&2
    exit 1
fi
if [ -n "$stale" ]; then
    echo "typecheck-any: baselined sites no longer reported, delete them from $baseline:"
    printf '%s\n' "$stale"
fi
