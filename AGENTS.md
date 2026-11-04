# Notes for AI agents

## Testing with a newer setuptools release

When asked to test with the latest setuptools:

1. Look up the latest version and its `requires_python` on PyPI:
   `curl -s https://pypi.org/pypi/setuptools/json`.
   Check that `requires_python` still covers the oldest Python version in the
   test matrix. If it does not, ask before changing anything.
2. Create a branch from `master`, named after the version without dots,
   for example `setuptools-8421` for 84.2.1.
3. In `.github/workflows/run-tests.yml`, replace every occurrence of the
   current newest setuptools version with the new one. There are several
   (one per job), so replace them all, for example
   `sed -i '' 's/84\.1\.0/84.2.1/g' .github/workflows/run-tests.yml`.
   - For a new minor or patch release, replace the version in place.
   - For a new major version, the `setuptools` job's range matrix keeps the
     latest release of the previous major (like `83.0.0`) and appends the new
     version. In all other jobs, just replace the version.
4. Check the other setuptools pins in `run-tests.yml` too. A pin that the
   comments in the workflow give a specific reason for (minimum version,
   behaviour boundary) stays as is. Any other pin stands for the latest
   release of its major version (for example `80.10.2`, `83.0.0`), so update
   it if PyPI has a newer non-yanked release in that major series.
5. Add a news fragment `news/+<random hex>.tests.rst` with
   `Test with setuptools X.Y.Z.  [maurits]`.
   If an unreleased news fragment from an earlier setuptools bump is still in
   `news/` (not yet in `CHANGES.rst`), update that file instead of adding a
   new one.
6. Commit with message `Test with setuptools X.Y.Z.`. Only push and open a PR
   against `master` when asked.

Example commits: `0a6c3793` (84.0.0 → 84.1.0), `0a71552d` (84.1.0 → 84.2.1).

## Testing with a newer pip release

When asked to test with the latest pip:

1. Look up the latest version and its `requires_python` on PyPI:
   `curl -s https://pypi.org/pypi/pip/json`.
   Check that `requires_python` still covers the Python version used in the
   `pip` job. If it does not, ask before changing anything.
2. Create a branch from `master`, named after the version without dots,
   for example `pip-263` for 26.3.
3. pip is only pinned in the `pip-version` matrix of the `pip` job in
   `.github/workflows/run-tests.yml` (check with `grep -n pip-version`).
   As the comment there says, it tests only the latest release of each year
   (pip versions are `YY.N[.P]`).
   - For a new release in the current year, replace that year's version in
     place, for example `26.2.1` → `26.3`.
   - For the first release of a new year, keep the versions of earlier
     years and append the new version, for example
     `["25.3", "26.3"]` → `["25.3", "26.3", "27.0"]`.
4. Add a news fragment `news/+<random hex>.tests.rst` with
   `Test with latest pip X.Y.Z.  [maurits]`.
   If an unreleased news fragment from an earlier pip bump is still in
   `news/` (not yet in `CHANGES.rst`), update that file instead of adding a
   new one.
5. Commit with message `Test with latest pip X.Y.Z.`. Only push and open a PR
   against `master` when asked.

Example commit: `9edcf728` (26.2.1 → 26.3, with news fragment).
