#!/bin/bash

set -x
set -e

cd ../..

# Travis Python comes with preinstalled six
# which breaks test suite
pip${PYTHON_VER} uninstall -y six || true
python${PYTHON_VER} dev.py
bin/test -c -vvv
