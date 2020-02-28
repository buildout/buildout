SHELL := /bin/bash
HERE = $(shell pwd)
PYTHON_VER ?= 2.7
PYTHON_PATH = $(HERE)/pythons/$(PYTHON_VER)
PYTHON_BUILD_DIR = $(HERE)/python_builds

ifeq ($(PYTHON_VER),2.7)
	PYTHON_MINOR ?= 2.7.17
endif
ifeq ($(PYTHON_VER),3.5)
	PYTHON_MINOR ?= 3.5.9
	PYTHON_CONFIGURE_ARGS ?= --without-ensurepip
endif
ifeq ($(PYTHON_VER),3.6)
	PYTHON_MINOR ?= 3.6.10
	PYTHON_CONFIGURE_ARGS ?= --without-ensurepip
endif
ifeq ($(PYTHON_VER),3.7)
	PYTHON_MINOR ?= 3.7.6
	PYTHON_CONFIGURE_ARGS ?= --without-ensurepip
endif
ifeq ($(PYTHON_VER),3.8)
	PYTHON_MINOR ?= 3.8.2
	PYTHON_CONFIGURE_ARGS ?= --without-ensurepip
endif

ifndef PYTHON_MINOR
    $(error Please specify desired PYTHON_MINOR for Python $(PYTHON_VER))
endif

PYTHON_ARCHIVE ?= Python-$(PYTHON_MINOR)
PYTHON_DOWNLOAD = https://www.python.org/ftp/python/$(PYTHON_MINOR)/$(PYTHON_ARCHIVE).tgz
PYTHON_EXE = python$(PYTHON_VER)
CURRENT_PYTHON = $(shell cat $(PYTHON_PATH)/python_version.txt)

.PHONY: all build test python
BUILD_DIRS = $(PYTHON_PATH) bin build develop-eggs eggs parts

all: build

$(PYTHON_PATH)/bin/$(PYTHON_EXE):
	@echo "Installing Python"
	mkdir -p $(PYTHON_PATH)
	mkdir -p $(PYTHON_BUILD_DIR)
	cd $(PYTHON_BUILD_DIR) && \
	curl --progress-bar --location $(PYTHON_DOWNLOAD) | tar -zx
	cd $(PYTHON_BUILD_DIR)/$(PYTHON_ARCHIVE) && \
	./configure --prefix $(PYTHON_PATH) $(PYTHON_CONFIGURE_ARGS) >/dev/null 2>&1 && \
	make >/dev/null 2>&1 && \
	make install >/dev/null 2>&1
	@echo "Finished installing Python"

check_version:
	if [[ "$(CURRENT_PYTHON)" != "Python $(PYTHON_MINOR)" ]]; then rm $(PYTHON_PATH)/bin/$(PYTHON_EXE); fi 

python: check_version $(PYTHON_PATH)/bin/$(PYTHON_EXE)
	$(PYTHON_PATH)/bin/$(PYTHON_EXE) --version 2> $(PYTHON_PATH)/python_version.txt


build: $(PYTHON_PATH)/bin/$(PYTHON_EXE)
	$(PYTHON_PATH)/bin/$(PYTHON_EXE) dev.py

clean:
	rm -rf $(BUILD_DIRS) $(PYTHON_BUILD_DIR)

test:
	$(HERE)/bin/test -1 -vvv -c
