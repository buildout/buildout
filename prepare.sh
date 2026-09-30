#!/bin/sh
# Note: if you are testing changes, you may want to temporarily change the line
# above to use /bin/dash instead of bash.  Otherwise you may get incompatibilities.
# Exit on error:
set -e
HERE="$PWD"
# TODO check PYTHON_VER as well?  Probably just rename current code.
PYTHON_VERSION="${PYTHON_VERSION:-3}"
PIP_VERSION="${PIP_VERSION}"
SETUPTOOLS_VERSION="${SETUPTOOLS_VERSION}"
PIP_ARGS="${PIP_ARGS:--U}"
USE_UV="${USE_UV}"
if test "$USE_UV"; then
    UV_LINE="YES (override by unsetting USE_UV environment variable or making it empty)"
else
    UV_LINE="NO (override by giving USE_UV environment variable a non-empty value)"
fi
cat << MARKER
Prepare a virtual environment for testing zc.buildout.

Using:
* Python: $PYTHON_VERSION (override with PYTHON_VERSION environment variable)
* pip: $PIP_VERSION (override with PIP_VERSION environment variable)
* setuptools: $SETUPTOOLS_VERSION (override with SETUPTOOLS_VERSION environment variable)
* use uv: $UV_LINE

An empty version means: use whatever is already available, or install latest.
Extra arguments for pip install: $PIP_ARGS (override with PIP_ARGS environment variable)
MARKER

case "$*" in
  help*)
    exit 0
    ;;
  --help*)
    exit 0
    ;;
esac

# Let's ignore all Python warnings for now.
# There would especially be too many setuptools warnings.
PYTHONWARNINGS="ignore"
VENVS="$HERE/venvs"
# The GitHub actions runners (and most other systems) have an OSTYPE env var.
# We use this to check if we are on Windows, as this influences some paths.
case "$OSTYPE" in
  msys*|cygwin*)
    # Windows
    PYTHON="python3.exe"
    VENV="$VENVS/python"
    VENV_PYTHON="$VENV/Scripts/$PYTHON"
    ;;
  *)
    PYTHON="python$PYTHON_VERSION"
    VENV="$VENVS/$PYTHON"
    VENV_PYTHON="$VENV/bin/$PYTHON"
    ;;
esac
echo
echo "Python version:"
$PYTHON --version

echo
echo "Creating virtual environment in $VENV"
mkdir -p "$VENVS"
if test "$USE_UV"; then
  echo "using uv"
  uv venv -p $PYTHON_VERSION --seed "$VENV"
else
  $PYTHON -m venv "$VENV"
fi

PIP_ARGS="$PIP_ARGS pip"
if test $PIP_VERSION; then
	# PIP_ARGS="$PIP_ARGS pip==$PIP_VERSION"
    # We already have something like '-U pip'.
    # Make this '-U pip==version'.
	PIP_ARGS="$PIP_ARGS==$PIP_VERSION"
fi
WHEEL_VERSION=""
PIP_ARGS="$PIP_ARGS setuptools"
if test $SETUPTOOLS_VERSION; then
	PIP_ARGS="$PIP_ARGS==$SETUPTOOLS_VERSION"
  # wheel is a dependency of zc.buildout, but we may need a specific version.
  # If we use setuptools older than 70.1.0, we must use at most wheel 0.45.1,
  # otherwise the bdist_wheel command is not present.
  # Take the major and minor version and remove the dot: 69.5.1 -> 695
  SV=$(echo $SETUPTOOLS_VERSION | cut -d "." -f-2 | sed "s/\.//")
  # Do the same transformation on the target version: 70.1.0 -> 701.
  # Check if the SETUPTOOLS_VERSION is lighter than the target.
  if test $SV -lt 701; then
    WHEEL_VERSION="0.45.1"
    echo "Pinning wheel to $WHEEL_VERSION for compat with older setuptools."
  fi
fi
# Always include wheel:
PIP_ARGS="$PIP_ARGS wheel"
if test $WHEEL_VERSION; then
  # Use a specific version:
	PIP_ARGS="$PIP_ARGS==$WHEEL_VERSION"
fi
# packaging is already a dependency of zc.buildout, but we explicitly add it.
# We add 'build' so we can build a source dist of zc.buildout,
# which has a side effect we need: generate 'src/zc.buildout.egg-info'
# This is needed so in Python we can do:
# >>> pkg_resources.working_set.add_entry('src')
# Floor build at 1: if a package index momentarily hides pyproject_hooks,
# an unfloored build requirement silently backtracks to build 0.9.0, which
# lacks build.env.DefaultIsolatedEnv and fails the test suite much later.
# uv is a dependency of zc.buildout; add it like packaging.
PIP_ARGS="$PIP_ARGS packaging build>=1 uv"
echo
echo "Using arguments for pip install: $PIP_ARGS"
# "$VENV_PYTHON" -m pip install -e .[test] -e zc.recipe.egg_[test] $PIP_ARGS
"$VENV_PYTHON" -m pip install $PIP_ARGS
echo
echo "pip freeze output:"
"$VENV_PYTHON" -m pip freeze --all
echo
echo "pip list output:"
"$VENV_PYTHON" -m pip list --verbose

echo
echo "Seeding downloads/test-seed with the setuptools and wheel wheels just installed."
echo "The test suites resolve their spawned installers' build requirements from there"
echo "(see buildoutSetUp in src/zc/buildout/testing.py), so suite runs need no index."
echo "A uv wheel is seeded as well: zc.buildout declares uv as a dependency, so"
echo "sample buildouts resolving that requirement must find it without an index."
echo "packaging and pip are seeded for the same reason: they are zc.buildout"
echo "runtime requirements, so a compile carrying the zc.buildout develop"
echo "project as an override must find them in the seeded sources."
echo "tomli joins the seed on Python < 3.11, where zc.buildout requires it."
SEED="$HERE/downloads/test-seed"
mkdir -p "$SEED"
rm -f "$SEED"/*.whl
SEED_SETUPTOOLS=$("$VENV_PYTHON" -c 'import importlib.metadata as m; print(m.version("setuptools"))')
SEED_WHEEL=$("$VENV_PYTHON" -c 'import importlib.metadata as m; print(m.version("wheel"))')
SEED_UV=$("$VENV_PYTHON" -c 'import importlib.metadata as m; print(m.version("uv"))')
SEED_PACKAGING=$("$VENV_PYTHON" -c 'import importlib.metadata as m; print(m.version("packaging"))')
SEED_PIP=$("$VENV_PYTHON" -c 'import importlib.metadata as m; print(m.version("pip"))')
# tomli is a zc.buildout runtime requirement on Python < 3.11 only, so
# the venv has it exactly on those interpreters.  The seed must carry
# it there too: a compile carrying the zc.buildout develop override
# resolves the marker dependency and fails hermetically without a
# candidate (GH run 35833561014).
SEED_TOMLI=$("$VENV_PYTHON" -c 'import importlib.metadata as m; print(m.version("tomli"))' 2>/dev/null || true)
SEED_TOMLI_SPEC=
if test "$SEED_TOMLI"; then
  SEED_TOMLI_SPEC="tomli==$SEED_TOMLI"
fi
"$VENV_PYTHON" -m pip download --quiet --no-deps --dest "$SEED" \
    "setuptools==$SEED_SETUPTOOLS" "wheel==$SEED_WHEEL" "uv==$SEED_UV" \
    "packaging==$SEED_PACKAGING" "pip==$SEED_PIP" $SEED_TOMLI_SPEC
ls -l "$SEED"

# The uv resolve seam gets its own copy of the seed, snapshotted before
# the setuptools floor lands below: the floor serves spawned build
# environments only, and a compile that resolves setuptools against it
# "upgrades" the toolchain past the cell's pin (GH run 36030422312).
# hermetic_pip_env points buildout_testing_seam_find_links here.
SEAM_SEED="$HERE/downloads/test-seam-seed"
rm -rf "$SEAM_SEED"
mkdir -p "$SEAM_SEED"
cp "$SEED"/*.whl "$SEAM_SEED"
ls -l "$SEAM_SEED"

# The spawned builds' expectations match modern setuptools: PEP 660's
# build_editable hook (added in setuptools 64) and normalized wheel
# filenames (fixed in 75.8.x). A cell pinning an older setuptools keeps
# it at runtime, but the seed must also carry a floor version: build
# environments resolve the highest version find-links offers. Without
# the floor, old-setuptools cells fail where the pre-hermetic proxy
# setup did not (GH run 34977253833).
SEED_FLOOR_SETUPTOOLS="75.8.2"
SV=$(echo "$SEED_SETUPTOOLS" | cut -d "." -f-2 | sed "s/\.//")
SF=$(echo "$SEED_FLOOR_SETUPTOOLS" | cut -d "." -f-2 | sed "s/\.//")
if test "$SV" -lt "$SF"; then
  echo
  echo "Adding setuptools floor $SEED_FLOOR_SETUPTOOLS to the seed for spawned builds."
  "$VENV_PYTHON" -m pip download --quiet --no-deps --dest "$SEED" \
      "setuptools==$SEED_FLOOR_SETUPTOOLS"
  ls -l "$SEED"
fi

echo
echo "Building source dist, so we get an egg-info directory."
"$VENV_PYTHON" -m build --sdist .

echo
echo "Now calling 'python dev.py' to create 'bin/buildout' script in main directory."
"$VENV_PYTHON" dev.py
