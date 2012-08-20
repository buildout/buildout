HERE = $(shell pwd)
PYTHON_PATH = $(HERE)/python
PYTHON_VER ?= 2.7
PYTHON_MINOR ?= 2.7.3

ifeq ($(PYTHON_VER),"2.6")
	PYTHON_MINOR ?= 2.6.8
endif
ifeq ($(PYTHON_VER),"3.2")
	PYTHON_MINOR ?= 3.2.3
endif

PYTHON_DOWNLOAD ?= http://www.python.org/ftp/python/$(PYTHON_MINOR)/Python-$(PYTHON_MINOR).tgz

.PHONY: all build test

all: build

$(PYTHON_PATH):
	@echo "Installing Python"
	mkdir -p $(PYTHON_PATH)
	cd $(PYTHON_PATH) && \
	curl --progress-bar $(PYTHON_DOWNLOAD) | tar -zx
	cd $(PYTHON_PATH)/Python-$(PYTHON_MINOR) && \
	./configure --prefix $(PYTHON_PATH) && make && make install
	@echo "Finished installing Python"

build: $(PYTHON_PATH)
	$(PYTHON_PATH)/bin/python dev.py

test:
	$(HERE)/bin/test -v
