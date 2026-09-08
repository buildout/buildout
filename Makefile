.PHONY: all test help lint grammar-test sync-grammar
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

sync-grammar:
	# Ship the generated parser inside the zc.buildout package; the
	# linter compiles this copy with the system C compiler at runtime.
	mkdir -p src/zc/buildout/grammar/tree_sitter
	cp tree-sitter-buildout/src/parser.c src/zc/buildout/grammar/parser.c
	cp tree-sitter-buildout/src/tree_sitter/*.h src/zc/buildout/grammar/tree_sitter/

grammar-test:
	# Requires the tree-sitter CLI (brew install tree-sitter-cli or
	# npm install -g tree-sitter-cli) and node.
	cd tree-sitter-buildout && tree-sitter generate --abi=14 && tree-sitter test

lint:
	$(MAKE) sync-grammar
	if [ ! -x venvs/linter/bin/buildout-lint ]; then \
		python3 -m venv venvs/linter && \
		venvs/linter/bin/pip install -q --upgrade pip && \
		venvs/linter/bin/pip install -q -e '.[linter]'; \
	fi
	PYTHONWARNINGS=ignore venvs/linter/bin/buildout-lint \
		buildout.cfg .github/workflows/scripts*.cfg
	PYTHONWARNINGS=ignore venvs/linter/bin/python -m unittest \
		discover -s tree-sitter-buildout/linter -p 'test_*.py'

help:
	./prepare.sh --help

clean:
	rm -rf venvs .Python .installed.cfg bin build dist lib include parts pip-selfcheck.json develop-eggs src/*.egg-info zc.recipe.egg_/src/*.egg-info
