.PHONY: all test help
all: test

bin/buildout: setup.py prepare.sh dev.py
	./prepare.sh

bin/test: bin/buildout buildout.cfg
	bin/buildout || bin/buildout.exe

test: bin/test
	PYTHONWARNINGS=ignore bin/test -pvc

test-recipe: bin/test
	PYTHONWARNINGS=ignore bin/test-recipe

test-small: bin/test
	PYTHONWARNINGS=ignore bin/test -pvc -t buildout.txt

help:
	./prepare.sh --help

clean:
	rm -rf venvs .Python .installed.cfg bin build dist lib include parts pip-selfcheck.json develop-eggs src/*.*-info zc.recipe.egg_/src/*.*-info
