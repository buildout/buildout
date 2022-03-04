#!/bin/bash

set -x
set -e

cd ../..
docker build -f .github/workflows/Dockerfile --tag centos_buildout:python${PYTHON_VER} --build-arg PYTHON_VER=${PYTHON_VER} .
docker run "centos_buildout:python${PYTHON_VER}" make -f Makefile.builds test_with_coverage
