#!/bin/bash

set -x
set -e

cd ../..
docker build -f .github/workflows/Dockerfile-debian-system --tag debian_system_buildout .
docker run debian_system_buildout make -f Makefile.builds test_without_coverage
