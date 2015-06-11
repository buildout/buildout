#############################################################################
#
# Copyright (c) 2004-2009 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Various test-support utility functions
"""

try:
    # Python 3
    from http.server    import HTTPServer, BaseHTTPRequestHandler
    from urllib.request import urlopen
except ImportError:
    # Python 2
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from urllib2        import urlopen

import errno
import logging
import os
import pkg_resources
import random
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

import zc.buildout.buildout
import zc.buildout.easy_install
from zc.buildout.rmtree import rmtree

print_ = zc.buildout.buildout.print_

fsync = getattr(os, 'fsync', lambda fileno: None)
is_win32 = sys.platform == 'win32'

setuptools_location = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')).location

def cat(dir, *names):
    path = os.path.join(dir, *names)
    if (not os.path.exists(path)
        and is_win32
        and os.path.exists(path+'-script.py')
        ):
        path = path+'-script.py'
    with open(path) as f:
        print_(f.read(), end='')

def ls(dir, *subs):
    if subs:
        dir = os.path.join(dir, *subs)
    names = sorted(os.listdir(dir))
    for name in names:
        if os.path.isdir(os.path.join(dir, name)):
            print_('d ', end=' ')
        elif os.path.islink(os.path.join(dir, name)):
            print_('l ', end=' ')
        else:
            print_('- ', end=' ')
        print_(name)

def mkdir(*path):
    os.mkdir(os.path.join(*path))

def remove(*path):
    path = os.path.join(*path)
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)

def rmdir(*path):
    shutil.rmtree(os.path.join(*path))

def write(dir, *args):
    path = os.path.join(dir, *(args[:-1]))
    f = open(path, 'w')
    f.write(args[-1])
    f.flush()
    fsync(f.fileno())
    f.close()

def clean_up_pyc(*path):
    base, filename = os.path.join(*path[:-1]), path[-1]
    if filename.endswith('.py'):
        filename += 'c' # .py -> .pyc
    for path in (
        os.path.join(base, filename),
        os.path.join(base, '__pycache__'),
        ):
        if os.path.isdir(path):
            rmdir(path)
        elif os.path.exists(path):
            remove(path)

## FIXME - check for other platforms
MUST_CLOSE_FDS = not sys.platform.startswith('win')

def system(command, input='', with_exit_code=False):
    p = subprocess.Popen(command,
                         shell=True,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=MUST_CLOSE_FDS)
    i, o, e = (p.stdin, p.stdout, p.stderr)
    if input:
        i.write(input.encode())
    i.close()
    result = o.read() + e.read()
    o.close()
    e.close()
    output = result.decode()
    if with_exit_code:
        # Use the with_exit_code=True parameter when you want to test the exit
        # code of the command you're running.
        output += 'EXIT CODE: %s' % p.wait()
    return output

def get(url):
    return str(urlopen(url).read().decode())

def _runsetup(setup, *args):
    if os.path.isdir(setup):
        setup = os.path.join(setup, 'setup.py')
    args = list(args)
    args.insert(0, '-q')
    here = os.getcwd()
    try:
        os.chdir(os.path.dirname(setup))
        zc.buildout.easy_install.call_subprocess(
            [sys.executable, setup] + args,
            env=dict(os.environ, PYTHONPATH=setuptools_location))
        if os.path.exists('build'):
            rmtree('build')
    finally:
        os.chdir(here)

def sdist(setup, dest):
    _runsetup(setup, 'sdist', '-d', dest, '--formats=zip')

def bdist_egg(setup, executable, dest=None):
    # Backward compat:
    if dest is None:
        dest = executable
    else:
        assert executable == sys.executable, (executable, sys.executable)
    _runsetup(setup, 'bdist_egg', '-d', dest)

def wait_until(label, func, *args, **kw):
    if 'timeout' in kw:
        kw = dict(kw)
        timeout = kw.pop('timeout')
    else:
        timeout = 30
    deadline = time.time()+timeout
    while time.time() < deadline:
        if func(*args, **kw):
            return
        time.sleep(0.01)
    raise ValueError('Timed out waiting for: '+label)

class TestOptions(zc.buildout.buildout.Options):

    def initialize(self):
        pass

class Buildout(zc.buildout.buildout.Buildout):

    def __init__(self):
        zc.buildout.buildout.Buildout.__init__(
            self, '', [('buildout', 'directory', os.getcwd())])

    Options = TestOptions

def buildoutSetUp(test):

    test.globs['__tear_downs'] = __tear_downs = []
    test.globs['register_teardown'] = register_teardown = __tear_downs.append

    prefer_final = zc.buildout.easy_install.prefer_final()
    register_teardown(
        lambda: zc.buildout.easy_install.prefer_final(prefer_final)
        )

    here = os.getcwd()
    register_teardown(lambda: os.chdir(here))

    handlers_before_set_up = logging.getLogger().handlers[:]
    def restore_root_logger_handlers():
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        for handler in handlers_before_set_up:
            root_logger.addHandler(handler)
    register_teardown(restore_root_logger_handlers)

    base = tempfile.mkdtemp('buildoutSetUp')
    base = os.path.realpath(base)
    register_teardown(lambda base=base: rmtree(base))

    old_home = os.environ.get('HOME')
    os.environ['HOME'] = os.path.join(base, 'bbbBadHome')
    def restore_home():
        if old_home is None:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = old_home
    register_teardown(restore_home)

    base = os.path.join(base, '_TEST_')
    os.mkdir(base)

    tmp = tempfile.mkdtemp('buildouttests')
    register_teardown(lambda: rmtree(tmp))

    zc.buildout.easy_install.default_index_url = 'file://'+tmp
    os.environ['buildout-testing-index-url'] = (
        zc.buildout.easy_install.default_index_url)

    def tmpdir(name):
        path = os.path.join(base, name)
        mkdir(path)
        return path

    sample = tmpdir('sample-buildout')

    os.chdir(sample)

    # Create a basic buildout.cfg to avoid a warning from buildout:
    with open('buildout.cfg', 'w') as f:
        f.write("[buildout]\nparts =\n")

    # Use the buildout bootstrap command to create a buildout
    zc.buildout.buildout.Buildout(
        'buildout.cfg',
        [('buildout', 'log-level', 'WARNING'),
         # trick bootstrap into putting the buildout develop egg
         # in the eggs dir.
         ('buildout', 'develop-eggs-directory', 'eggs'),
         ]
        ).bootstrap([])



    # Create the develop-eggs dir, which didn't get created the usual
    # way due to the trick above:
    os.mkdir('develop-eggs')

    def start_server(path):
        port, thread = _start_server(path, name=path)
        url = 'http://localhost:%s/' % port
        register_teardown(lambda: stop_server(url, thread))
        return url

    cdpaths = []
    def cd(*path):
        path = os.path.join(*path)
        cdpaths.append(os.path.abspath(os.getcwd()))
        os.chdir(path)

    def uncd():
        os.chdir(cdpaths.pop())

    test.globs.update(dict(
        sample_buildout = sample,
        ls = ls,
        cat = cat,
        mkdir = mkdir,
        rmdir = rmdir,
        remove = remove,
        tmpdir = tmpdir,
        write = write,
        system = system,
        get = get,
        cd = cd, uncd = uncd,
        join = os.path.join,
        sdist = sdist,
        bdist_egg = bdist_egg,
        start_server = start_server,
        buildout = os.path.join(sample, 'bin', 'buildout'),
        wait_until = wait_until,
        print_ = print_,
        clean_up_pyc = clean_up_pyc,
        ))

    zc.buildout.easy_install.prefer_final(prefer_final)

def buildoutTearDown(test):
    for f in test.globs['__tear_downs']:
        f()

class Server(HTTPServer):

    def __init__(self, tree, *args):
        HTTPServer.__init__(self, *args)
        self.tree = os.path.abspath(tree)

    __run = True
    def serve_forever(self):
        while self.__run:
            self.handle_request()

    def handle_error(self, *_):
        self.__run = False

class Handler(BaseHTTPRequestHandler):

    Server.__log = False

    def __init__(self, request, address, server):
        self.__server = server
        self.tree = server.tree
        BaseHTTPRequestHandler.__init__(self, request, address, server)

    def do_GET(self):
        if '__stop__' in self.path:
            raise SystemExit

        def k():
            self.send_response(200)
            out = '<html><body>k</body></html>\n'.encode()
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(out)

        if self.path == '/enable_server_logging':
            self.__server.__log = True
            return k()

        if self.path == '/disable_server_logging':
            self.__server.__log = False
            return k()

        path = os.path.abspath(os.path.join(self.tree, *self.path.split('/')))
        if not (
            ((path == self.tree) or path.startswith(self.tree+os.path.sep))
            and
            os.path.exists(path)
            ):
            self.send_response(404, 'Not Found')
            #self.send_response(200)
            out = '<html><body>Not Found</body></html>'.encode()
            #out = '\n'.join(self.tree, self.path, path)
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(out)
            return

        self.send_response(200)
        if os.path.isdir(path):
            out = ['<html><body>\n']
            names = sorted(os.listdir(path))
            for name in names:
                if os.path.isdir(os.path.join(path, name)):
                    name += '/'
                out.append('<a href="%s">%s</a><br>\n' % (name, name))
            out.append('</body></html>\n')
            out = ''.join(out).encode()
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
        else:
            with open(path, 'rb') as f:
                out = f.read()
            self.send_header('Content-Length', len(out))
            if path.endswith('.egg'):
                self.send_header('Content-Type', 'application/zip')
            elif path.endswith('.gz'):
                self.send_header('Content-Type', 'application/x-gzip')
            elif path.endswith('.zip'):
                self.send_header('Content-Type', 'application/x-gzip')
            else:
                self.send_header('Content-Type', 'text/html')

        self.end_headers()

        self.wfile.write(out)

    def log_request(self, code):
        if self.__server.__log:
            print_('%s %s %s' % (self.command, code, self.path))

def _run(tree, port):
    server_address = ('localhost', port)
    httpd = Server(tree, server_address, Handler)
    httpd.serve_forever()

def get_port():
    for i in range(10):
        port = random.randrange(20000, 30000)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            try:
                s.connect(('localhost', port))
            except socket.error:
                return port
        finally:
            s.close()
    raise RuntimeError("Can't find port")

def _start_server(tree, name=''):
    port = get_port()
    thread = threading.Thread(target=_run, args=(tree, port), name=name)
    thread.setDaemon(True)
    thread.start()
    wait(port, up=True)
    return port, thread

def start_server(tree):
    return _start_server(tree)[0]

def stop_server(url, thread=None):
    try:
        urlopen(url+'__stop__')
    except Exception:
        pass
    if thread is not None:
        thread.join() # wait for thread to stop

def wait(port, up):
    addr = 'localhost', port
    for i in range(120):
        time.sleep(0.25)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(addr)
            s.close()
            if up:
                break
        except socket.error:
            e = sys.exc_info()[1]
            if e[0] not in (errno.ECONNREFUSED, errno.ECONNRESET):
                raise
            s.close()
            if not up:
                break
    else:
        if up:
            raise
        else:
            raise SystemError("Couldn't stop server")

def install(project, destination):
    if not isinstance(destination, str):
        destination = os.path.join(destination.globs['sample_buildout'],
                                   'eggs')

    dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse(project))
    if dist.location.endswith('.egg'):
        destination = os.path.join(destination,
                                   os.path.basename(dist.location),
                                   )
        if os.path.isdir(dist.location):
            shutil.copytree(dist.location, destination)
        else:
            shutil.copyfile(dist.location, destination)
    else:
        # copy link
        with open(os.path.join(destination, project+'.egg-link'), 'w') as f:
            f.write(dist.location)

def install_develop(project, destination):
    if not isinstance(destination, str):
        destination = os.path.join(destination.globs['sample_buildout'],
                                   'develop-eggs')

    dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse(project))
    with open(os.path.join(destination, project+'.egg-link'), 'w') as f:
        f.write(dist.location)

def _normalize_path(match):
    path = match.group(1)
    if os.path.sep == '\\':
        path = path.replace('\\\\', '/')
        if path.startswith('\\'):
            path = path[1:]
    return '/' + path.replace(os.path.sep, '/')

normalize_path = (
    re.compile(
        r'''[^'" \t\n\r]+\%(sep)s_[Tt][Ee][Ss][Tt]_\%(sep)s([^"' \t\n\r]+)'''
        % dict(sep=os.path.sep)),
    _normalize_path,
    )

normalize_endings = re.compile('\r\n'), '\n'

normalize_script = (
    re.compile('(\n?)-  ([a-zA-Z_.-]+)-script.py\n-  \\2.exe\n'),
    '\\1-  \\2\n')

if sys.version_info > (2, ):
    normalize___pycache__ = (
        re.compile('(\n?)d  __pycache__\n'), '\\1')
else:
    normalize___pycache__ = (
        re.compile('(\n?)-  \S+\.pyc\n'), '\\1')

normalize_egg_py = (
    re.compile('-py\d[.]\d(-\S+)?.egg'),
    '-pyN.N.egg',
    )

normalize_exception_type_for_python_2_and_3 = (
    re.compile(r'^(\w+\.)*([A-Z][A-Za-z0-9]+Error: )'),
    '\2')

not_found = (re.compile(r'Not found: [^\n]+/(\w|\.)+/\r?\n'), '')

# Setuptools now pulls in dependencies when installed.
adding_find_link = (re.compile(r"Adding find link '[^']+'"
                               r" from setuptools .*\r?\n"), '')

ignore_not_upgrading = (
    re.compile(
    'Not upgrading because not running a local buildout command.\n'
    ), '')
