HERE = $(shell pwd)
PYTHON_VER ?= 2.7
PYTHON_MINOR ?= 2.7.3
PYTHON_PATH = $(HERE)/python$(PYTHON_VER)

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
ifeq ($(PYTHON_VER),2.4)
	sed -i 's@#zlib zlibmodule.c -I$(prefix)/include -L$(exec_prefix)@zlib zlibmodule.c -I$(prefix)/include -L$(exec_prefix)@' "$(PYTHON_PATH)/$(PYTHON_ARCHIVE)/Modules/Setup.dist"
	sed -i '200i_socket socketmodule.c' "$(PYTHON_PATH)/$(PYTHON_ARCHIVE)/Modules/Setup.dist"
	sed -i '202iSSL=/usr/lib/ssl _ssl _ssl.c -DUSE_SSL -I/usr/include/openssl -L/usr/lib/ssl -lssl -lcrypto' "$(PYTHON_PATH)/$(PYTHON_ARCHIVE)/Modules/Setup.dist"
endif
ifeq ($(PYTHON_VER),2.5)
	sed -i '1ifrom __future__ import with_statement' "$(PYTHON_PATH)/$(PYTHON_ARCHIVE)/setup.py"
	sed -i '200i_socket socketmodule.c' "$(PYTHON_PATH)/$(PYTHON_ARCHIVE)/Modules/Setup.dist"
	sed -i '202iSSL=/usr/lib/ssl _ssl _ssl.c -DUSE_SSL -I/usr/include/openssl -L/usr/lib/ssl -lssl -lcrypto' "$(PYTHON_PATH)/$(PYTHON_ARCHIVE)/Modules/Setup.dist"
endif
ifeq ($(PYTHON_VER),2.6)
	cd $(PYTHON_PATH) && \
	curl --progress-bar https://raw.github.com/collective/buildout.python/master/src/issue12012-sslv2-py26.txt > ssl.txt
	cd $(PYTHON_PATH)/$(PYTHON_ARCHIVE) && \
	patch -p0 < ../ssl.txt
endif
	cd $(PYTHON_PATH)/$(PYTHON_ARCHIVE) && \
	./configure --prefix $(PYTHON_PATH) --with-zlib=/usr/include --without-sqlite >/dev/null 2>&1 && \
	make  && \
	make install >/dev/null 2>&1
	@echo "Finished installing Python"

build: $(PYTHON_PATH)
	$(PYTHON_PATH)/bin/$(PYTHON_EXE) dev.py

clean:
	rm -rf $(BUILD_DIRS)

test:
	$(HERE)/bin/test -v
