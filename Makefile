HERE = $(shell pwd)
PYTHON_PATH = $(HERE)/python
PYTHON_VER ?= 2.7
PYTHON_MINOR ?= 2.7.3

ifeq ($(PYTHON_VER),2.6)
	PYTHON_MINOR = 2.6.8
endif
ifeq ($(PYTHON_VER),3.2)
	PYTHON_MINOR = 3.2.3
endif

PYTHON_DOWNLOAD ?= http://www.python.org/ftp/python/$(PYTHON_MINOR)/Python-$(PYTHON_MINOR).tgz

.PHONY: all build test
BUILD_DIRS = $(PYTHON_PATH) bin build develop-eggs eggs parts

all: build

$(PYTHON_PATH):
	@echo "Installing Python"
	mkdir -p $(PYTHON_PATH)
	cd $(PYTHON_PATH) && \
	curl --progress-bar $(PYTHON_DOWNLOAD) | tar -zx
	cd $(PYTHON_PATH)/Python-$(PYTHON_MINOR) && \
	./configure --prefix $(PYTHON_PATH) >/dev/null 2>&1 && \
	make >/dev/null 2>&1 && \
	make install >/dev/null 2>&1
	@echo "Finished installing Python"

build: $(PYTHON_PATH)
	$(PYTHON_PATH)/bin/python dev.py

clean:
	rm -rf $(BUILD_DIRS)

test:
	$(HERE)/bin/test -v -1 -t \!isolation.txt
