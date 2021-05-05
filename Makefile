HERE = $(shell pwd)
PYTHON_VER ?= 3.7
PYTHON_PATH = $(HERE)/pythons/$(PYTHON_VER)
PYTHON_BUILD_DIR = $(HERE)/python_builds
PLATFORM = $(shell uname)
VENV = $(HERE)/venvs/$(PYTHON_VER)
BUILD_VARIABLES =

ifeq ($(PYTHON_VER),2.7)
	PYTHON_MINOR ?= 2.7.18
endif
ifeq ($(PYTHON_VER),3.5)
	PYTHON_MINOR ?= 3.5.10
endif
ifeq ($(PYTHON_VER),3.6)
	PYTHON_MINOR ?= 3.6.13
endif
ifeq ($(PYTHON_VER),3.7)
	PYTHON_MINOR ?= 3.7.10
endif
ifeq ($(PYTHON_VER),3.8)
	PYTHON_MINOR ?= 3.8.8
endif
ifeq ($(PYTHON_VER),3.9)
	PYTHON_MINOR ?= 3.9.2
endif
ifeq ($(PYTHON_VER),3.10)
	PYTHON_MINOR ?= 3.10.0
	PYTHON_ARCHIVE ?= Python-3.10.0a5
endif

ifndef PYTHON_MINOR
    $(error Please specify desired PYTHON_MINOR for Python $(PYTHON_VER))
endif

ifeq ($(PLATFORM),Darwin)
	include Makefile.configure.Darwin
else
	include Makefile.configure
endif


PYTHON_ARCHIVE ?= Python-$(PYTHON_MINOR)
PYTHON_URL = https://www.python.org/ftp/python/$(PYTHON_MINOR)/$(PYTHON_ARCHIVE).tgz
PYTHON_EXE = python$(PYTHON_VER)
PYTHON_DOWNLOAD = $(PYTHON_BUILD_DIR)/$(PYTHON_ARCHIVE).tgz

BUILD_DIRS = $(PYTHON_PATH) bin build develop-eggs eggs parts

all: all_test
.PHONY: all download_python python build test coverage docker docker_deb docker_deb_sys all_pythons all_test all_coverage

# setup python from source
$(PYTHON_DOWNLOAD):
	mkdir -p $(PYTHON_BUILD_DIR)
	curl --progress-bar --location $(PYTHON_URL) -o $(PYTHON_DOWNLOAD)

$(PYTHON_BUILD_DIR)/$(PYTHON_ARCHIVE)/configure: $(PYTHON_DOWNLOAD)
	cd $(PYTHON_BUILD_DIR) && tar -xzf $(PYTHON_DOWNLOAD)
	touch $@

$(PYTHON_PATH)/bin/$(PYTHON_EXE): $(PYTHON_BUILD_DIR)/$(PYTHON_ARCHIVE)/configure
	@echo "Installing Python"
	rm -rf $(PYTHON_PATH)
	mkdir -p $(PYTHON_PATH)
	cd $(PYTHON_BUILD_DIR)/$(PYTHON_ARCHIVE) && \
	$(BUILD_VARIABLES) ./configure --prefix $(PYTHON_PATH) $(PYTHON_CONFIGURE_ARGS) >/dev/null 2>&1 && \
	make >/dev/null 2>&1 && \
	make install >/dev/null 2>&1
	@echo "Finished installing Python"

download_python: $(PYTHON_BUILD_DIR)/$(PYTHON_ARCHIVE)/configure

python: $(PYTHON_PATH)/bin/$(PYTHON_EXE)

# used by Dockerfile
build: python
	$(PYTHON_PATH)/bin/$(PYTHON_EXE) dev.py

# copy to virtualenvs
ROOT_FILES := $(HERE)/setup.py $(HERE)/setup.cfg $(HERE)/dev.py $(HERE)/README.rst $(HERE)/CHANGES.rst $(HERE)/buildout.cfg $(HERE)/.coveragerc
SRC_FILES := $(shell find $(HERE)/src ! -path '*egg-info*' \( -name '*.py' -o -name '*.txt' -o -name '*.test' \) )
RCP_FILES := $(shell find $(HERE)/zc.recipe.egg_ ! -path '*egg-info*' \( -name '*.py' -o -name '*.txt' -o -name '*.rst' -o -name '*.cfg' -o -name '*.in' \) )
DOC_FILES := $(shell find $(HERE)/doc -name '*.rst' -o -name '*.txt')

ALL_COPY := $(subst $(HERE),$(VENV),$(SRC_FILES) $(DOC_FILES) $(RCP_FILES) $(ROOT_FILES))
# Generate rules to map sources into targets
$(foreach s,$(ALL_COPY),$(eval $s: $(VENV)/bin/$(PYTHON_EXE) $(subst $(VENV),$(HERE),$s)))

$(ALL_COPY):
	@mkdir -p $(dir $@)
	@cp $(subst $(VENV),$(HERE),$@) $@

$(VENV)/bin/$(PYTHON_EXE): $(PYTHON_PATH)/bin/$(PYTHON_EXE)
	@command -v virtualenv >/dev/null 2>&1 || { echo "virtualenv required but not installed" >&2; exit 1; }
	test -d "$(HERE)/venvs" || mkdir -p $(HERE)/venvs
	virtualenv -p $(PYTHON_PATH)/bin/$(PYTHON_EXE) $(VENV)

$(VENV)/bin/test: $(VENV)/bin/$(PYTHON_EXE) $(ALL_COPY)
	cd $(VENV) && bin/$(PYTHON_EXE) dev.py --no-clean

$(VENV)/bin/coverage: $(VENV)/bin/$(PYTHON_EXE)
	$(VENV)/bin/pip install coverage

coverage: $(VENV)/bin/coverage $(VENV)/bin/test
	COVERAGE_REPORT= RUN_COVERAGE= $(VENV)/bin/test $(testargs)

test: $(VENV)/bin/test
	$(VENV)/bin/test -c -vvv $(testargs)

all_pythons:
	$(MAKE) PYTHON_VER=2.7 python
	$(MAKE) PYTHON_VER=3.5 python
	$(MAKE) PYTHON_VER=3.6 python
	$(MAKE) PYTHON_VER=3.7 python
	$(MAKE) PYTHON_VER=3.8 python

all_coverage:
	$(MAKE) PYTHON_VER=2.7 coverage
	$(MAKE) PYTHON_VER=3.5 coverage
	$(MAKE) PYTHON_VER=3.6 coverage
	$(MAKE) PYTHON_VER=3.7 coverage
	$(MAKE) PYTHON_VER=3.8 coverage

all_test:
	$(MAKE) PYTHON_VER=2.7 test
	$(MAKE) PYTHON_VER=3.5 test
	$(MAKE) PYTHON_VER=3.6 test
	$(MAKE) PYTHON_VER=3.7 test
	$(MAKE) PYTHON_VER=3.8 test

docker:
	docker build -f .github/workflows/Dockerfile --tag centos_buildout:python${PYTHON_VER} --build-arg PYTHON_VER=${PYTHON_VER} .
	docker run centos_buildout:python${PYTHON_VER} /bin/bash -c 'RUN_COVERAGE= COVERAGE_REPORT= /home/buildout/sandbox/bin/test -c -vvv -t abi'

docker_deb:
	docker build -f .github/workflows/Dockerfile-debian --tag debian_buildout:python${PYTHON_VER} --build-arg PYTHON_VER=${PYTHON_VER} .
	docker run debian_buildout:python${PYTHON_VER} /bin/bash -c 'RUN_COVERAGE= COVERAGE_REPORT= /home/buildout/sandbox/bin/test -c -vvv -t abi'

docker_deb_sys:
	docker build -f .github/workflows/Dockerfile-debian-system --tag debian_system_buildout .
	docker run debian_system_buildout /bin/bash -c 'RUN_COVERAGE= COVERAGE_REPORT= /home/buildout/sandbox/bin/test -c -vvv -t abi'

clean:
	rm -rf $(HERE)/venvs $(PYTHON_BUILD_DIR) $(HERE)/pythons
