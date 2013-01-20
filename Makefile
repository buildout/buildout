HERE = $(shell pwd)
PYTHON_VER ?= 2.7
PYTHON_MINOR ?= 2.7.3
PYTHON_PATH = $(HERE)/python$(PYTHON_VER)

ifeq ($(PYTHON_VER),2.6)
	PYTHON_MINOR = 2.6.8
endif
ifeq ($(PYTHON_VER),3.2)
	PYTHON_MINOR = 3.2.3
endif

ifeq ($(PYTHON_VER),3.3)
	PYTHON_MINOR = 3.3.0
	PYTHON_ARCHIVE = Python-3.3.0
endif

PYTHON_ARCHIVE ?= Python-$(PYTHON_MINOR)
PYTHON_DOWNLOAD = http://www.python.org/ftp/python/$(PYTHON_MINOR)/$(PYTHON_ARCHIVE).tgz
PYTHON_EXE = python$(PYTHON_VER)

.PHONY: all build test
BUILD_DIRS = $(PYTHON_PATH) bin build develop-eggs eggs parts

all: build

$(PYTHON_PATH):
	@echo "Installing Python"
	mkdir -p $(PYTHON_PATH)
	cd $(PYTHON_PATH) && \
	curl --progress-bar $(PYTHON_DOWNLOAD) | tar -zx
ifeq ($(PYTHON_VER),2.6)
	cd $(PYTHON_PATH) && \
	curl --progress-bar https://raw.github.com/collective/buildout.python/master/src/issue12012-sslv2-py26.txt > ssl.txt
	cd $(PYTHON_PATH)/$(PYTHON_ARCHIVE) && \
	patch -p0 < ../ssl.txt
endif
	cd $(PYTHON_PATH)/$(PYTHON_ARCHIVE) && \
	./configure --prefix $(PYTHON_PATH) >/dev/null 2>&1 && \
	make >/dev/null 2>&1 && \
	make install >/dev/null 2>&1
	@echo "Finished installing Python"

build: $(PYTHON_PATH)
	$(PYTHON_PATH)/bin/$(PYTHON_EXE) dev.py

clean:
	rm -rf $(BUILD_DIRS)

test:
	$(HERE)/bin/test -1
