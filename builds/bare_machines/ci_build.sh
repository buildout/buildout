#!/bin/bash

set -x
set -e

cd ../..

# Some machines come with preinstalled six
# which breaks test suite
pip${PYTHON_VER} uninstall -y six || true
python${PYTHON_VER} dev.py
make -f Makefile.builds test_without_coverage
