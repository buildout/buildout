#!/bin/bash

set -x
set -e

cd ../..

# Travis Python comes with preinstalled six
# which breaks test suite
pip uninstall -y six || true
python dev.py
bin/test -c -vvv
