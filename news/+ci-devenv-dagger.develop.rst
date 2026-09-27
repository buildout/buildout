CI and the development environment were rebuilt around devenv and Dagger.
GitHub jobs bootstrap only Nix and take every tool — Python, uv, ruff, ty —
from the repository-owned ``devenv.nix`` (optionally shared across jobs via
a cachix cache), so CI and local shells use the same toolchain.
A repository-owned dagger module runs the whole CI job table locally or in
containers (``dagger call ci``, per-family matrices, per-Python pip/uv
cache volumes, transient-fetch retries that still fail fast on genuine
failures, and failure-debug tooling), replacing the flaked devpi proxy.
The Windows leg lives in its own reusable workflow with a dispatch-only
iteration loop, both suites gained coverage jobs that upload HTML reports,
and ``etc/bump_ci_versions.py`` keeps the CI version matrices current.
The test suites run hermetically: ``prepare.sh`` seeds
``downloads/test-seed/`` so spawned pip/uv builds resolve offline.
Agent skills and in-tree planning documents — including the phased plan to
remove ``pkg_resources`` and ``setuptools`` from the uv path — are
maintained alongside the code.  [gotcha]
