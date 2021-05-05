#!/bin/bash

set -x
set -e

cd ../..
docker build -f .github/workflows/Dockerfile-debian --tag debian_buildout:python${PYTHON_VER} --build-arg PYTHON_VER=${PYTHON_VER} .
docker run debian_buildout:python${PYTHON_VER} /bin/bash -c 'RUN_COVERAGE= COVERAGE_REPORT= /home/buildout/sandbox/bin/test -c -vvv'
