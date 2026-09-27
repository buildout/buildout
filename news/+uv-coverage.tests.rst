CI gains a parallel uv test set: the legacy suite reruns through the uv
install pipeline (``make test-uv``) across the platform matrix including
Windows, against a uv version matrix spanning the earliest supported
0.12.x and the latest releases.  Most of the legacy doctest corpus runs
green under ``installer = uv`` — recipe and extension fixtures build
wheels instead of eggs and egg-only doctests are marked ``uv-deprecated``
— and picked-versions reporting parity between the uv and pip installers
is pinned by unit tests.  [gotcha]
