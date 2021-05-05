FROM centos as centos-python
RUN yum install -y make gcc openssl-devel libffi-devel sqlite-devel glibc-langpack-en
RUN useradd -ms /bin/bash buildout
USER buildout
ARG PYTHON_VER
ENV LC_ALL C.UTF-8
RUN mkdir /home/buildout/sandbox
WORKDIR /home/buildout/sandbox
COPY Makefile Makefile.configure /home/buildout/sandbox/
RUN make PYTHON_VER=${PYTHON_VER} download_python
RUN make PYTHON_VER=${PYTHON_VER} python
FROM centos-python
ARG PYTHON_VER
COPY doc /home/buildout/sandbox/doc
COPY src /home/buildout/sandbox/src
COPY zc.recipe.egg_ /home/buildout/sandbox/zc.recipe.egg_
COPY setup.* dev.py *.rst *.txt buildout.cfg .coveragerc /home/buildout/sandbox/
USER root
RUN chown -R buildout:buildout *
USER buildout
RUN make PYTHON_VER=${PYTHON_VER} build
