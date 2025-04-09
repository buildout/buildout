#!/bin/sh
# Exit on error:
set -e
HERE="$PWD"
# TODO check PYTHON_VER as well?  Probably just rename current code.
PYTHON_VERSION="${PYTHON_VERSION:-3}"
PIP_VERSION="${PIP_VERSION}"
SETUPTOOLS_VERSION="${SETUPTOOLS_VERSION}"
PIP_ARGS="${PIP_ARGS:--U}"
cat << MARKER
Prepare a virtual environment for testing zc.buildout.

Using:
* Python: $PYTHON_VERSION (override with PYTHON_VERSION environment variable)
* pip: $PIP_VERSION (override with PIP_VERSION environment variable)
* setuptools: $SETUPTOOLS_VERSION (override with SETUPTOOLS_VERSION environment variable)

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
$PYTHON -m venv "$VENV"

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
# wheel and packaging are already dependencies of zc.buildout.
# We add 'build' so we can build a source dist of zc.buildout,
# which has a side effect we need: generate 'src/zc.buildout.egg-info'
# This is needed so in Python we can do:
# >>> pkg_resources.working_set.add_entry('src')
PIP_ARGS="$PIP_ARGS wheel packaging build"
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
