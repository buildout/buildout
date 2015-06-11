HERE = $(shell pwd)
PYTHON_VER ?= 2.7
PYTHON_PATH = $(HERE)/pythons/$(PYTHON_VER)
PYTHON_BUILD_DIR = $(HERE)/python_builds

ifeq ($(PYTHON_VER),2.6)
	PYTHON_MINOR ?= 2.6.8
endif
ifeq ($(PYTHON_VER),2.7)
	PYTHON_MINOR ?= 2.7.3
endif
ifeq ($(PYTHON_VER),3.2)
	PYTHON_MINOR ?= 3.2.3
endif
ifeq ($(PYTHON_VER),3.3)
	PYTHON_MINOR ?= 3.3.0
endif
ifeq ($(PYTHON_VER),3.4)
	PYTHON_MINOR ?= 3.4.2
	PYTHON_CONFIGURE_ARGS ?= --without-ensurepip
endif

ifndef PYTHON_MINOR
    $(error Please specify desired PYTHON_MINOR for Python $(PYTHON_VER))
endif

PYTHON_ARCHIVE ?= Python-$(PYTHON_MINOR)
PYTHON_DOWNLOAD = https://www.python.org/ftp/python/$(PYTHON_MINOR)/$(PYTHON_ARCHIVE).tgz
PYTHON_EXE = python$(PYTHON_VER)

.PHONY: all build test
BUILD_DIRS = $(PYTHON_PATH) bin build develop-eggs eggs parts

all: build

$(PYTHON_PATH)/bin/$(PYTHON_EXE):
	@echo "Installing Python"
	mkdir -p $(PYTHON_PATH)
	mkdir -p $(PYTHON_BUILD_DIR)
	cd $(PYTHON_BUILD_DIR) && \
	curl --progress-bar --location $(PYTHON_DOWNLOAD) | tar -zx
ifeq ($(PYTHON_VER),2.6)
	cd $(PYTHON_BUILD_DIR) && \
	curl --progress-bar -L https://raw.github.com/collective/buildout.python/ad45adb78bfa37542d62a394392d5146fce5af34/src/issue12012-sslv2-py26.patch > ssl.patch
	cd $(PYTHON_BUILD_DIR)/$(PYTHON_ARCHIVE) && \
	patch -p0 < ../ssl.patch
endif
	cd $(PYTHON_BUILD_DIR)/$(PYTHON_ARCHIVE) && \
	./configure --prefix $(PYTHON_PATH) $(PYTHON_CONFIGURE_ARGS) >/dev/null 2>&1 && \
	make >/dev/null 2>&1 && \
	make install >/dev/null 2>&1
	@echo "Finished installing Python"

build: $(PYTHON_PATH)/bin/$(PYTHON_EXE)
	$(PYTHON_PATH)/bin/$(PYTHON_EXE) dev.py

clean:
	rm -rf $(BUILD_DIRS) $(PYTHON_BUILD_DIR)

test:
	$(HERE)/bin/test -1 -v
