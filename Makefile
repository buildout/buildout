HERE = $(shell pwd)
PYTHON_VER ?= 2.7
PYTHON_MINOR ?= 2.7.3
PYTHON_PATH = $(HERE)/python$(PYTHON_VER)
# see http://lipyrary.blogspot.com/2011/05/how-to-compile-python-on-ubuntu-1104.html
ARCH = $(shell dpkg-architecture -qDEB_HOST_MULTIARCH)

ifeq ($(PYTHON_VER),2.6)
	PYTHON_MINOR = 2.6.8
endif

ifeq ($(PYTHON_VER),2.5)
	PYTHON_MINOR = 2.5.6
endif

ifeq ($(PYTHON_VER),2.4)
	PYTHON_MINOR = 2.4.6
endif

PYTHON_ARCHIVE ?= Python-$(PYTHON_MINOR)
PYTHON_DOWNLOAD = http://www.python.org/ftp/python/$(PYTHON_MINOR)/$(PYTHON_ARCHIVE).tgz
PYTHON_EXE = python$(PYTHON_VER)

.PHONY: all build test
BUILD_DIRS = $(PYTHON_PATH) bin build develop-eggs eggs parts

all: build

$(PYTHON_PATH):
	@echo "Installing Python"
	# see http://mail.python.org/pipermail/python-bugs-list/2007-April/038211.html
	sudo mv /usr/include/sqlite3.h /tmp/
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
	./configure LDFLAGS="-L/usr/lib/$(ARCH) -L/lib/$(ARCH)" --prefix $(PYTHON_PATH) --with-zlib=/usr/include && \
	make  && \
	make install >/dev/null 2>&1
	@echo "Finished installing Python"

build: $(PYTHON_PATH)
	$(PYTHON_PATH)/bin/$(PYTHON_EXE) dev.py

clean:
	rm -rf $(BUILD_DIRS)

test:
	$(HERE)/bin/test -v
