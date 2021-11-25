#!/bin/bash

set -x
set -e

cd ../..

python${PYTHON_VER} dev.py
bin/test -c -vvv
