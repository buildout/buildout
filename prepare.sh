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
    VENV_BIN_DIR="$VENV/Scripts"
    # Depending on the Python version you may get python3.exe or python.exe.
    # Since 3.13 it is python.exe, though this may be a bug and could change.
    # VENV_PYTHON="$VENV_BIN_DIR/$PYTHON"
    VENV_PYTHON="$VENV_BIN_DIR/python.exe"
    ;;
  *)
    PYTHON="python$PYTHON_VERSION"
    VENV="$VENVS/$PYTHON"
    VENV_BIN_DIR="$VENV/bin"
    VENV_PYTHON="$VENV_BIN_DIR/python"
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
PIP_ARGS="$PIP_ARGS setuptools"
if test $SETUPTOOLS_VERSION; then
	PIP_ARGS="$PIP_ARGS==$SETUPTOOLS_VERSION"
fi
# wheel is a dependency of zc.buildout, so always include it:
PIP_ARGS="$PIP_ARGS wheel"
# packaging and platformdirs are dependencies of zc.buildout, but we
# explicitly add them because zc.buildout itself is not pip-installed here.
# We add 'build' so we can build a source dist of zc.buildout,
# which has a side effect we need: generate 'src/zc.buildout.egg-info'
# This is needed so dev.py can find the zc.buildout distribution after
# putting 'src' on sys.path.
PIP_ARGS="$PIP_ARGS packaging platformdirs build"
echo
echo "Using arguments for pip install: $PIP_ARGS"
echo "Using $VENV_PYTHON"
# Showing contents of bin dir, so we have a clue in case
# the python script cannot be found.
# Use ls, not dir: dir is GNU coreutils only, it is missing on macOS.
echo ls "$VENV_BIN_DIR"
ls "$VENV_BIN_DIR"
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
