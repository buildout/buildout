Port the test suite from legacy doctests to pytest. The ported suite runs in parallel via pytest-xdist (``make pytest``) and is wired into CI across the full Python and platform matrix.
