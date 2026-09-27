The test suite was ported from legacy doctests to pytest: the ported suite
runs in parallel via pytest-xdist (``make pytest``) and is wired into CI
across the full Python and platform matrix, and the dagger CI module
gained its own test harness that pins the job table against the GitHub
workflows.  [gotcha]
