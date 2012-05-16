#!/bin/sh

if [ "$(basename $0)" != "roundup" ]; then
    exec $(dirname $0)/roundup $0
fi

describe "buildout"

it_has_a_help_option() {
    [[ "$(bin/buildout --help)" == "Usage: buildout"* ]]
}

it_has_an_annotate_command() {
    [[ "$(bin/buildout annotate)" == *"Annotated sections"* ]]
}

it_creates_files() {
    bin/buildout
    test -x bin/py
    test -x bin/test
    test -x bin/oltest
}

it_creates_a_working_bin_test() {
    [[ "$(bin/test --help)" == "Usage: test [options] [MODULE] [TEST]"* ]]
}

it_creates_a_working_bin_oltest() {
    [[ "$(bin/oltest --help)" == "Usage: oltest [options] [MODULE] [TEST]"* ]]
}

it_creates_a_working_bin_py() {
    [[ "$(bin/py -c 'import sys; print(sys.path)')" == *eggs/zc.buildout-*.egg* ]]
}
