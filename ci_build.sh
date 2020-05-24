#!/bin/bash

set -x
set -e

cd ./builds/${BUILD_TYPE} && ./ci_build.sh
