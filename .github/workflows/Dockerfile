FROM centos as centos-python
RUN yum install -y make gcc openssl-devel libffi-devel sqlite-devel glibc-langpack-en
ARG PYTHON_VER
ENV LC_ALL C.UTF-8
RUN mkdir buildout
WORKDIR /buildout
COPY Makefile Makefile.configure /buildout/
RUN make PYTHON_VER=${PYTHON_VER} download_python
RUN make PYTHON_VER=${PYTHON_VER} python
FROM centos-python
ARG PYTHON_VER
COPY doc /buildout/doc
COPY src /buildout/src
COPY zc.recipe.egg_ /buildout/zc.recipe.egg_
COPY setup.* dev.py *.rst *.txt buildout.cfg .coveragerc /buildout/
RUN make PYTHON_VER=${PYTHON_VER} build
