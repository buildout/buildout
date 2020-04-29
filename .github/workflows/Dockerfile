FROM centos:7
RUN yum install -y make gcc openssl-devel libffi-devel
ARG PYTHON_VER
ENV LC_CTYPE="en_US.UTF-8"
RUN mkdir buildout
WORKDIR /buildout
COPY Makefile /buildout
RUN make PYTHON_VER=${PYTHON_VER} python
COPY doc /buildout/doc
COPY src /buildout/src
COPY zc.recipe.egg_ /buildout/zc.recipe.egg_
COPY setup.* dev.py *.rst *.txt buildout.cfg /buildout/
RUN make PYTHON_VER=${PYTHON_VER} build
