#!/bin/sh

if [ "$(basename $0)" != "roundup" ]; then
    exec $(dirname $0)/roundup $0
fi

describe "bootstrap"

it_creates_a_directory_structure() {
    python ../bootstrap/bootstrap.py
    test -d bin
    test -x bin/buildout
    test -d parts
    test -d eggs
    test -d develop-eggs
}
