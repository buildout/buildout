# Development environment for zc.buildout, driven by devenv.sh.
#
# Enter with:  devenv shell
#
# Python version: defaults to 3.12 (known-good for the 5.x bootstrap).
# Override per shell from the command line — no file edits needed:
#
#   devenv shell --option languages.python.version:string 3.10
#
# The chosen version is exported as PYTHON_VERSION, so the repo's own
# bootstrap (`make bin/buildout`, i.e. ./prepare.sh) picks exactly the
# Python this environment provides. prepare.sh keys its venvs by Python
# version (venvs/python3.x), so switching versions does not require
# `make clean` — just re-run `make bin/buildout && bin/buildout`.
{ pkgs, lib, config, ... }:

{
  languages.python = {
    enable = true;
    version = "3.12";
    # Deliberately no languages.python.venv here: the repo bootstraps
    # its own venvs/ via prepare.sh; a devenv-managed venv would
    # shadow it on PATH and confuse the test-suite runners.
  };

  # Tools for development and for the verify-buildout skill:
  # - git: version control
  # - gnumake: the Makefile entry points (make test / make pytest / ...)
  # - uv: fast path of prepare.sh (USE_UV), also fetches pythons
  # - coreutils: provides `timeout` etc. on macOS, where it is missing
  # - ty: Astral's type checker; the static tier of verify-buildout
  # - towncrier: news entries in news/ are required by the
  #   develop-buildout skill (config: [tool.towncrier] in pyproject.toml)
  # - ruff: linting; driven by `make lint` (config: [tool.ruff] in
  #   pyproject.toml)
  # - radon: cyclomatic-complexity measurements behind the budget gate
  #   (`make complexity`; baseline etc/complexity-baseline.json)
  # - mypy: explicit-Any burndown gate (`make typecheck-any`; config
  #   [tool.mypy] in pyproject.toml, baseline etc/any-burndown-baseline.txt)
  packages = with pkgs; [
    git
    gnumake
    uv
    coreutils
    ty
    # No top-level towncrier attr in nixpkgs; the python3Packages
    # application ships the standalone `towncrier` CLI.
    python3Packages.towncrier
    ruff
    python3Packages.radon
    mypy
  ];

  # MonkeyType and autotyping are not in nixpkgs, and they must share
  # the interpreter of the repo venv they trace or rewrite (the
  # MonkeyType tracer runs in-process with the test suite). Install
  # them into venvs/python$PYTHON_VERSION on demand:
  #
  #   typing-bootstrap
  scripts.typing-bootstrap.exec = ''
    VENV="venvs/python$PYTHON_VERSION"
    if [ ! -x "$VENV/bin/python" ]; then
      echo "no $VENV yet — run: make bin/buildout" >&2
      exit 1
    fi
    "$VENV/bin/python" -m pip install --quiet MonkeyType autotyping
    echo "MonkeyType + autotyping installed into $VENV"
  '';

  # Dagger engine on a Podman machine, from the devenv-dagger module
  # (inputs declared in devenv.yaml). Enabling services.dagger
  # auto-enables services.podman-machine. `devenv up` starts the
  # machine and the engine container; the dagger CLI in this shell
  # reaches the engine via _EXPERIMENTAL_DAGGER_RUNNER_HOST, which the
  # module exports.
  # Local developer shells only. On CI runners (the CI env var is
  # always set there) the module stays disabled: its
  # podman-machine:init task otherwise runs before every shell entry
  # (measured 85-120s per CI leg) and qemu/podman/dagger bloat the
  # closure, none of which a CI leg uses. The dagger workflow job
  # brings its own CLI and engine (dagger/dagger-for-github on the
  # runner's docker). mkDefault keeps the gate overridable from
  # devenv.local.nix.
  services.dagger.enable = lib.mkDefault (builtins.getEnv "CI" == "");

  # Machine resources are coded, not hand-set: the podman default of
  # 2048 MiB OOM-killed the CI cache workload under full-run load. The
  # values apply when the machine is created; `podman machine set`
  # changes an existing machine.
  services.podman-machine.memoryMiB = 8192;
  services.podman-machine.cpus = 6;

  # Feed the repo bootstrap the Python version selected above.
  env.PYTHON_VERSION = config.languages.python.version;
  # nixpkgs Pythons ship with ensurepip disabled, so `python -m venv`
  # cannot bootstrap pip. Route prepare.sh through uv (--seed installs
  # pip), using the uv provided by this environment.
  env.USE_UV = "1";
  # prepare.sh runs `uv venv` unconditionally; let it replace an
  # existing venvs/pythonX.Y instead of erroring out, so that
  # re-running `make bin/buildout` (e.g. after a version switch) just
  # works.
  env.UV_VENV_CLEAR = "1";
  # Known-good bootstrap pin: latest setuptools (>= 81) removed
  # pkg_resources, which the 5.x bootstrap (dev.py) still imports.
  # Override per command when probing newer setuptools:
  #   SETUPTOOLS_VERSION=84.0.0 make bin/buildout
  env.SETUPTOOLS_VERSION = "75.8.2";

  enterShell = ''
    echo "zc.buildout devenv — python $(python --version 2>&1 | awk '{print $2}') (PYTHON_VERSION=$PYTHON_VERSION)"
    echo "Override python: devenv shell --option languages.python.version:string <3.9-3.14>"
  '';
}
