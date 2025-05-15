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
case "$OSTYPE" in
  msys*)
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
PIP_ARGS="$PIP_ARGS packaging build"
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
echo "Building source dist, so we get an egg-info directory."
"$VENV_PYTHON" -m build --sdist .

echo
echo "Now calling 'python dev.py' to create 'bin/buildout' script in main directory."
"$VENV_PYTHON" dev.py
