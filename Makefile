HERE = $(shell pwd)
PYTHON_VER ?= 3.7
PYTHON_PATH = $(HERE)/pythons/$(PYTHON_VER)
PYTHON_BUILD_DIR = $(HERE)/python_builds
PLATFORM = $(shell uname)
VENV = $(HERE)/venvs/$(PYTHON_VER)
BUILD_VARIABLES =

ifeq ($(PYTHON_VER),2.7)
	PYTHON_MINOR ?= 2.7.17
endif
ifeq ($(PYTHON_VER),3.5)
	PYTHON_MINOR ?= 3.5.9
endif
ifeq ($(PYTHON_VER),3.6)
	PYTHON_MINOR ?= 3.6.10
endif
ifeq ($(PYTHON_VER),3.7)
	PYTHON_MINOR ?= 3.7.7
endif
ifeq ($(PYTHON_VER),3.8)
	PYTHON_MINOR ?= 3.8.2
endif
ifeq ($(PYTHON_VER),3.9)
	PYTHON_MINOR ?= 3.9.0
	PYTHON_ARCHIVE ?= Python-3.9.0a6
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

all: test
.PHONY: all download_python python build test docker clean

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

docker:
	docker build -f .github/workflows/Dockerfile --tag centos_buildout:python${PYTHON_VER} --build-arg PYTHON_VER=${PYTHON_VER} .
	docker run centos_buildout:python${PYTHON_VER} /buildout/bin/test -c -vvv -t abi

clean:
	rm -rf $(BUILD_DIRS) $(PYTHON_BUILD_DIR)

test:
	$(HERE)/bin/test -1 -vvv -c
