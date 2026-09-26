.PHONY: all test pytest coverage coverage-pytest coverage-unittests typecheck test-traced lint complexity complexity-baseline help
PYTHON_VERSION ?= 3.12
all: test

# The devenv shell leaks its profile's site-packages onto every spawned
# interpreter's sys.path via NIX_PYTHONPATH (nixpkgs sitecustomize).
# Ambient distributions there (e.g. six, pulled in by radon's mando
# dependency) hijack dependency resolution in the suites' spawned
# buildout children: pkg_resources picks the ambient dist over the
# pinned eggs/v5 copy on a location-string tie-break, and the install
# then fails trying to pip-install the profile's site-packages
# directory. Keep the suites hermetic by clearing NIX_PYTHONPATH.
HERMETIC_ENV = NIX_PYTHONPATH=

bin/buildout: setup.py prepare.sh dev.py
	./prepare.sh

bin/test: bin/buildout buildout.cfg
	bin/buildout || bin/buildout.exe

test: bin/test
	$(HERMETIC_ENV) PYTHONWARNINGS=ignore bin/test -pvc

test-recipe: bin/test
	$(HERMETIC_ENV) PYTHONWARNINGS=ignore bin/test-recipe

test-small: bin/test
	$(HERMETIC_ENV) PYTHONWARNINGS=ignore bin/test -pvc -t buildout.txt

# Second legacy-suite run with the uv pipeline: buildout_testing_installer
# is read by easy_install as the default for the [buildout] installer
# option and propagates into every spawned bin/buildout child, so the
# untouched corpus exercises uv instead of pip.
#
# UV_VERSION pins the uv under test (the uv matrix in test-uv.yml): the
# pin target installs that release into a repo-local tool dir with the
# ambient uv, and the recipe puts its bin dir first on PATH for the
# suite. easy_install._uv_executable resolves `uv` on PATH first, so
# every spawned child runs the pin. The bootstrap (bin/test) keeps the
# ambient uv: the pin targets the code under test, not the toolchain
# building the checkout. UV_TOOL_DIR moves with UV_TOOL_BIN_DIR because
# `uv tool install` keys tool environments by package name: two pinned
# versions in the default dir would clobber each other.
UV_PIN_DIR = $(CURDIR)/.uv-pin

$(UV_PIN_DIR)/uv-%/bin/uv:
	UV_TOOL_DIR="$(UV_PIN_DIR)/uv-$*/tools" \
		UV_TOOL_BIN_DIR="$(UV_PIN_DIR)/uv-$*/bin" \
		uv tool install --reinstall "uv==$*"

test-uv: bin/test $(if $(UV_VERSION),$(UV_PIN_DIR)/uv-$(UV_VERSION)/bin/uv,)
	$(HERMETIC_ENV) PYTHONWARNINGS=ignore buildout_testing_installer=uv \
		$(if $(UV_VERSION),PATH="$(UV_PIN_DIR)/uv-$(UV_VERSION)/bin:$$PATH",) \
		bin/test -pvc

# Coverage variants of both suites. etc/coverage/sitecustomize.py on
# PYTHONPATH starts coverage in the suite process itself and in every
# spawned Python subprocess (bin/buildout drives, pip installs, xdist
# workers) — each interpreter writes its own data file (.coveragerc has
# parallel = true). COVERAGE_PROCESS_START arms the sitecustomize hook.
# An absolute COVERAGE_FILE keeps all data files in the repo root: bin/test
# exits with parts/test as cwd and test-spawned processes chdir around.
# combine/report/html go through bin/coverage: the bare venv python has no
# coverage installed.
COVERAGE_ENV = COVERAGE_PROCESS_START=$(CURDIR)/.coveragerc \
	COVERAGE_FILE=$(CURDIR)/.coverage \
	PYTHONWARNINGS=ignore \
	PYTHONPATH="$(CURDIR)/etc/coverage$$(bin/py -c 'import glob, os; print(os.pathsep + os.pathsep.join(glob.glob(os.path.join(os.getcwd(), "eggs", "v5", "*.egg"))))')"

coverage: bin/test
	rm -f .coverage .coverage.*
	rm -rf htmlcov
	$(COVERAGE_ENV) $(HERMETIC_ENV) bin/test -pvc
	bin/coverage combine
	bin/coverage report
	bin/coverage html

coverage-pytest: bin/test
	rm -f .coverage .coverage.*
	rm -rf htmlcov
	$(COVERAGE_ENV) $(HERMETIC_ENV) bin/py -m pytest src/zc/buildout/tests/pytests/ -v -n auto
	bin/coverage combine
	bin/coverage report
	bin/coverage html

# Unittests-only variant: --unittests-only (pytests conftest) deselects
# every test that takes an integration fixture from conftest.py as an
# argument, leaving the tests that call the library directly. Same
# coverage machinery as coverage-pytest, over that subset.
coverage-unittests: bin/test
	rm -f .coverage .coverage.*
	rm -rf htmlcov
	$(COVERAGE_ENV) $(HERMETIC_ENV) bin/py -m pytest src/zc/buildout/tests/pytests/ -v -n auto --unittests-only
	bin/coverage combine
	bin/coverage report
	bin/coverage html

typecheck: bin/test
	# Static tier of verify-buildout: Astral's ty over the checkout with
	# the repo venv as its Python environment. The _vendor exclude lives
	# in pyproject.toml [tool.ty]. ty comes from the devenv.
	# Depends on bin/test (not bare bin/buildout): the buildout run is what
	# materializes eggs/, and the eggs go on ty's search path below so
	# imports that resolve at test time also resolve statically.
	ty check --project . --python venvs/python$(PYTHON_VERSION)/bin/python --output-format concise $(foreach e,$(wildcard eggs/v5/*.egg),--extra-search-path $e)

pytest: bin/test
	# xdist workers are bare-interpreter subprocesses: they do not inherit
	# bin/py's baked sys.path, so pass the eggs via PYTHONPATH. Let Python
	# itself assemble the value: the PWD variable is empty when make is
	# invoked from PowerShell (Windows CI), and the PYTHONPATH separator
	# is ';' on Windows but ':' elsewhere.
	$(HERMETIC_ENV) PYTHONWARNINGS=ignore PYTHONPATH="$$(bin/py -c 'import glob, os; print(os.pathsep.join(glob.glob(os.path.join(os.getcwd(), "eggs", "v5", "*.egg"))))')" \
		bin/py -m pytest src/zc/buildout/tests/pytests/ -v -n auto

lint:
	# ruff comes from the devenv (devenv.nix); run inside `devenv shell`.
	# Rule selection lives in [tool.ruff] in pyproject.toml — a pragmatic
	# baseline for this legacy tree; tighten it there as code gets cleaned.
	ruff check .

typecheck-any:
	# Explicit-Any burndown gate: no new `Any` annotation enters
	# src/zc/buildout. mypy (devenv-provided)
	# runs with disallow_any_explicit from [tool.mypy] in pyproject.toml.
	# The gate script compares reported sites against
	# etc/any-burndown-baseline.txt and fails only on sites the baseline
	# does not know, so the gate is green while the burndown burns down:
	# burndown commits delete baselined lines, and deliberate sites carry
	# per-line ignores with reasons. With an empty baseline the gate is
	# plain disallow-any-explicit.
	sh etc/check_any_burndown.sh

complexity:
	# Cyclomatic-complexity budget gate, a static tier of
	# verify-buildout: no function or method may exceed its entry in
	# etc/complexity-baseline.json, and code without an entry must be
	# radon grade B or better. radon comes from the devenv (the
	# daggerized CI pins the same version in its radon cell); the gate
	# script (etc/complexity_gate.py) is stdlib-only. After landing an
	# accepted simplification, refresh and commit the baseline:
	# make complexity-baseline
	python3 etc/complexity_gate.py

complexity-baseline:
	python3 etc/complexity_gate.py --write-baseline

help:
	./prepare.sh --help

clean:
	rm -rf venvs .Python .installed.cfg bin build dist lib include parts pip-selfcheck.json develop-eggs src/*.egg-info zc.recipe.egg_/src/*.egg-info

# Temporary slow tier: run the suite with MonkeyType tracing in every
# process, including spawned bin/buildout subprocesses (via
# etc/tracing/sitecustomize.py on PYTHONPATH). Traces land in
# .monkeytype-trace/monkeytype.sqlite3 for monkeytype stub/apply.
test-traced: bin/test
	rm -rf .monkeytype-trace && mkdir -p .monkeytype-trace
	$(HERMETIC_ENV) PYTHONPATH=$(CURDIR)/etc/tracing \
	MT_DB_PATH=$(CURDIR)/.monkeytype-trace/monkeytype.sqlite3 \
	MONKEYTYPE_TRACE_MODULES=zc,buildout \
	PYTHONWARNINGS=ignore \
	bin/test -pvc
