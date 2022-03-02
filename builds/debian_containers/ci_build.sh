#!/bin/bash

set -x
set -e

cd ../..
docker build -f .github/workflows/Dockerfile-debian --tag debian_buildout:python${PYTHON_VER} --build-arg PYTHON_VER=${PYTHON_VER} .
docker run "debian_buildout:python${PYTHON_VER}" make -f Makefile.builds test_without_coverage
