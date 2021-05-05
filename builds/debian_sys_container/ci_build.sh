#!/bin/bash

set -x
set -e

cd ../..
docker build -f .github/workflows/Dockerfile-debian-system --tag debian_system_buildout .
docker run debian_system_buildout /bin/bash -c 'RUN_COVERAGE= COVERAGE_REPORT= /home/buildout/sandbox/bin/test -c -vvv'
