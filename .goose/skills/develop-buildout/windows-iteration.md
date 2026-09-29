# Windows iteration loop

The Windows leg is the one CI surface no local checkout can reproduce
(Nix does not run on Windows runners, so `windows.yml` keeps
`actions/setup-python`). Iterating on a Windows-only failure through
`run-tests.yml` pays the full matrix on every push. The iteration
loop exists to avoid that.

## What it is

`.github/workflows/windows-iter.yml`, on the default branch:

- One Linux job runs the static trio with a single devenv setup:
  `make lint` (ruff), `make complexity` (radon), `make typecheck`
  (ty). Same commands as the corresponding legs in `run-tests.yml`,
  so the loop and the push gate agree.
- Then the Windows leg runs, and nothing else. The explicit-Any
  burndown and the test matrixes stay push-gate territory.
- `run-tests.yml` carries `branches-ignore: [windows-iter]`, so a
  scratch push never triggers the full matrix.

## Usage

Push the tree under test to the scratch branch:

```sh
git push gotcha HEAD:windows-iter
```

The workflow file lives on the default branch, so manual dispatch
also works against any ref:

```sh
gh workflow run windows-iter.yml --ref <branch>
```

## The ref is disposable

The branch name is CI configuration. It lives in the workflow files
on the default branch, not in any local or remote ref. The
`windows-iter` ref itself is just the last tree someone iterated on.
Delete it, recreate it, point it at a throwaway tree. The push above
recreates it whenever it is gone. Never let a stale `windows-iter`
ref block cleanup, and never treat its tip as work to preserve.

## When to reach for it

A Windows-only failure diagnosed by the watchdog flow (see
SKILL.md, "Windows CI watchdog"): apply the smallest truthful fix,
verify locally what is verifiable, push to `windows-iter` for the
Windows verdict, and only then push the real branch.
