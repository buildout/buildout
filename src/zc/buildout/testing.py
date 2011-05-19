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
    import http.server as BaseHTTPServer
except ImportError:
    import BaseHTTPServer
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
import textwrap
import threading
import time
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

import zc.buildout.buildout
import zc.buildout.easy_install
from zc.buildout.easy_install import setuptools_key
from zc.buildout.rmtree import rmtree
from zc.buildout.compat23 import call_external_python

fsync = getattr(os, 'fsync', lambda fileno: None)
is_win32 = sys.platform == 'win32'

# Only some unixes allow scripts in shebang lines:
script_in_shebang = is_win32
if sys.platform == 'linux2':
    f = subprocess.Popen('uname -r', shell=True, stdout=subprocess.PIPE).stdout
    r = f.read().decode('ascii').strip()
    f.close()
    r = tuple(map(int, re.match(r'\d+(\.\d+)*', r).group(0).split('.')))
    if r >= (2, 6, 27, 9):
        # http://www.in-ulm.de/~mascheck/various/shebang/
        script_in_shebang = True


setuptools_location = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')).location

def cat(dir, *names):
    path = os.path.join(dir, *names)
    if (not os.path.exists(path)
        and is_win32
        and os.path.exists(path+'-script.py')
        ):
        path = path+'-script.py'
    sys.stdout.write(open(path).read())

def ls(dir, *subs):
    if subs:
        dir = os.path.join(dir, *subs)
    names = []
    for name in os.listdir(dir):
        if name == '__pycache__':
            continue
        name = name.replace('.cpython-32m.so', '.so')
        names.append(name)

    for name in sorted(names):
        if os.path.isdir(os.path.join(dir, name)):
            code = 'd '
        elif os.path.islink(os.path.join(dir, name)):
            code = 'l '
        else:
            code = '- '
        print('%s %s' % (code, name))

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

## FIXME - check for other platforms
MUST_CLOSE_FDS = not sys.platform.startswith('win')

def system(command, input=''):
    env = dict(os.environ)
    env['COLUMNS'] = '80'
    p = subprocess.Popen(command,
                         shell=True,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=MUST_CLOSE_FDS,
                         env=env,
                         )
    i, o, e = (p.stdin, p.stdout, p.stderr)
    if input:
        i.write(input.encode())
    i.close()
    result = o.read() + e.read()
    o.close()
    e.close()
    p.wait()
    return result.decode()

def print_(*args):
    sys.stdout.write(' '.join(map(str, args)))

def run(command, input=''):
    sys.stdout.write(system(command, input))

def call_py(interpreter, cmd, flags=None):
    if sys.platform == 'win32':
        args = ['"%s"' % arg for arg in (interpreter, flags, cmd) if arg]
        args.insert(-1, '"-c"')
        return system('"%s"' % ' '.join(args))
    else:
        cmd = repr(cmd)
        return system(
            ' '.join(arg for arg in (interpreter, flags, '-c', cmd) if arg))

def get(url):
    return urlopen(url).read().decode()

def _runsetup(setup, executable, *args):
    if os.path.isdir(setup):
        setup = os.path.join(setup, 'setup.py')
    d = os.path.dirname(setup)

    args = [zc.buildout.easy_install._safe_arg(arg)
            for arg in args]
    args.insert(0, '-q')
    env = dict(os.environ)
    env['PYTHONPATH'] = setuptools_location
    args.append(env)

    here = os.getcwd()
    try:
        os.chdir(d)
        os.spawnle(os.P_WAIT, executable,
                   zc.buildout.easy_install._safe_arg(executable),
                   setup, *args)
        if os.path.exists('build'):
            rmtree('build')
    finally:
        os.chdir(here)

def sdist(setup, dest):
    _runsetup(setup, sys.executable, 'sdist', '-d', dest, '--formats=zip')

def bdist_egg(setup, executable, dest):
    _runsetup(setup, executable, 'bdist_egg', '-d', dest)

def sys_install(setup, dest):
    _runsetup(setup, sys.executable, 'install', '--install-purelib', dest,
              '--record', os.path.join(dest, '__added_files__'),
              '--single-version-externally-managed')

def find_python(version):
    """Return the path to a Python executable for a given version of Python.

    The version is given as a 2-component string: '2.4', '3.2', ...

    """
    env_friendly_version = ''.join(version.split('.'))

    candidates = []
    candidates.append(os.environ.get('PYTHON%s' % env_friendly_version))

    if is_win32:
        candidates.append('\Python%s\python.exe' % env_friendly_version)
    else:
        GET_EXECUTABLE_PATH = 'import sys; result = sys.executable'
        # Try Python executable with version encoded in filename
        r = call_external_python(
            'python%s' % version, GET_EXECUTABLE_PATH)
        candidates.append(r.out)

        # Try Python executable without version encoded in filename
        r = call_external_python(
            'python', 'import sys; result = "%s.%s\" % sys.version_info[:2]')

        if r.out == version:
            r = call_external_python('python', GET_EXECUTABLE_PATH)
            candidates.append(r.out)

    for candidate in candidates:
        if not candidate:
            continue
        if os.path.exists(candidate):
            return candidate

    raise ValueError(
        "Couldn't figure out the executable for Python %(version)s.\n"
        "Set the environment variable PYTHON%(envversion)s to the location\n"
        "of the Python %(version)s executable before running the tests."
        % {'version': version,
           'envversion': env_friendly_version})

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

def raises(exc_type, callable, *args, **kw):
    if isinstance(exc_type, str):
        E = Exception
    else:
        E = exc_type

    try:
        callable(*args, **kw)
    except E:
        v = sys.exc_info()[1]
        if E is exc_type:
            return v

        if exc_type == v.__class__.__name__:
            return v
        else:
            raise

    raise AssertionError("Expected %r" % exc_type)

def get_installer_values():
    """Get the current values for the easy_install module.

    This is necessary because instantiating a Buildout will force the
    Buildout's values on the installer.

    Returns a dict of names-values suitable for set_installer_values."""
    names = ('default_versions', 'download_cache', 'install_from_cache',
             'prefer_final', 'include_site_packages',
             'allowed_eggs_from_site_packages', 'use_dependency_links',
             'allow_picked_versions', 'always_unzip'
            )
    values = {}
    for name in names:
        values[name] = getattr(zc.buildout.easy_install, name)()
    return values

def set_installer_values(values):
    """Set the given values on the installer."""
    for name, value in list(values.items()):
        getattr(zc.buildout.easy_install, name)(value)

def make_buildout(executable=None):
    """Make a buildout that uses this version of zc.buildout."""
    # Create a basic buildout.cfg to avoid a warning from buildout.
    open('buildout.cfg', 'w').write(
        "[buildout]\nparts =\n"
        )
    # Get state of installer defaults so we can reinstate them (instantiating
    # a Buildout will force the Buildout's defaults on the installer).
    installer_values = get_installer_values()
    # Use the buildout bootstrap command to create a buildout
    config = [
        ('buildout', 'log-level', 'WARNING'),
        # trick bootstrap into putting the buildout develop egg
        # in the eggs dir.
        ('buildout', 'develop-eggs-directory', 'eggs'),
        ]
    if executable is not None:
        config.append(('buildout', 'executable', executable))
    zc.buildout.buildout.Buildout(
        'buildout.cfg', config,
        user_defaults=False,
        ).bootstrap([])
    # Create the develop-eggs dir, which didn't get created the usual
    # way due to the trick above:
    os.mkdir('develop-eggs')
    # Reinstate the default values of the installer.
    set_installer_values(installer_values)

def buildoutSetUp(test):

    test.globs['__tear_downs'] = __tear_downs = []
    test.globs['register_teardown'] = register_teardown = __tear_downs.append

    installer_values = get_installer_values()
    register_teardown(
        lambda: set_installer_values(installer_values)
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
    os.environ.pop('PYTHONPATH', None)

    def tmpdir(name):
        path = os.path.join(base, name)
        mkdir(path)
        return path

    sample = tmpdir('sample-buildout')

    os.chdir(sample)
    make_buildout()

    def start_server(path):
        port, thread = _start_server(path, name=path)
        url = 'http://localhost:%s/' % port
        register_teardown(lambda: stop_server(url, thread))
        return url

    def make_py(initialization=''):
        """Returns paths to new executable and to its site-packages.
        """
        buildout = tmpdir('executable_buildout')
        site_packages_dir = os.path.join(buildout, 'site-packages')
        mkdir(site_packages_dir)
        old_wd = os.getcwd()
        os.chdir(buildout)
        make_buildout()
        # Normally we don't process .pth files in extra-paths.  We want to
        # in this case so that we can test with setuptools system installs
        # (--single-version-externally-managed), which use .pth files.
        initialization = (
            ('import sys\n'
             'import site\n'
             'known_paths = set(sys.path)\n'
             'site_packages_dir = %r\n'
             'site.addsitedir(site_packages_dir, known_paths)\n'
            ) % (site_packages_dir,)) + initialization
        initialization = '\n'.join(
            '  ' + line for line in initialization.split('\n'))
        install_develop(
            'zc.recipe.egg', os.path.join(buildout, 'develop-eggs'))
        install_develop(
            'z3c.recipe.scripts', os.path.join(buildout, 'develop-eggs'))
        write('buildout.cfg', textwrap.dedent('''
            [buildout]
            parts = py
            include-site-packages = false
            exec-sitecustomize = false

            [py]
            recipe = z3c.recipe.scripts
            interpreter = py
            initialization =
            %(initialization)s
            extra-paths = %(site_packages)s
            eggs = %(setuptools_key)s
            ''') % dict(
                  initialization = initialization,
                  site_packages = site_packages_dir,
                  setuptools_key = setuptools_key,
                  ),
              )
        system(os.path.join(buildout, 'bin', 'buildout'))
        os.chdir(old_wd)
        return (
            os.path.join(buildout, 'bin', 'py'), site_packages_dir)

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
        run = run,
        raises = raises,
        print_ = print_,
        call_py = call_py,
        get = get,
        cd = (lambda *path: os.chdir(os.path.join(*path))),
        join = os.path.join,
        sdist = sdist,
        bdist_egg = bdist_egg,
        start_server = start_server,
        buildout = os.path.join(sample, 'bin', 'buildout'),
        wait_until = wait_until,
        make_py = make_py
        ))

def buildoutTearDown(test):
    for f in test.globs['__tear_downs']:
        f()

class Server(BaseHTTPServer.HTTPServer):

    def __init__(self, tree, *args):
        BaseHTTPServer.HTTPServer.__init__(self, *args)
        self.tree = os.path.abspath(tree)

    __run = True
    def serve_forever(self):
        while self.__run:
            self.handle_request()

    def handle_error(self, *_):
        self.__run = False

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

    Server.__log = False

    def __init__(self, request, address, server):
        self.__server = server
        self.tree = server.tree
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(
            self, request, address, server)

    def do_GET(self):
        if '__stop__' in self.path:
            raise SystemExit

        if self.path == '/enable_server_logging':
            self.__server.__log = True
            self.send_response(200)
            return

        if self.path == '/disable_server_logging':
            self.__server.__log = False
            self.send_response(200)
            return

        path = os.path.abspath(os.path.join(self.tree, *self.path.split('/')))
        if not (
            ((path == self.tree) or path.startswith(self.tree+os.path.sep))
            and
            os.path.exists(path)
            ):
            self.send_response(404, 'Not Found')
            out = '<html><body>Not Found</body></html>'.encode()
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(out)
            return

        self.send_response(200)
        if os.path.isdir(path):
            out = ['<html><body>\n']
            names = os.listdir(path)
            names.sort()
            for name in names:
                if os.path.isdir(os.path.join(path, name)):
                    name += '/'
                out.append('<a href="%s">%s</a><br>\n' % (name, name))
            out.append('</body></html>\n')
            out = ''.join(out).encode()
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
        else:
            out = open(path, 'rb').read()
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
            print('%s %s %s' % (self.command, code, self.path))

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
            raise SystemError("Couln't stop server")

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
        open(os.path.join(destination, project+'.egg-link'), 'w'
             ).write(dist.location)

def install_develop(project, destination):
    if not isinstance(destination, str):
        destination = os.path.join(destination.globs['sample_buildout'],
                                   'develop-eggs')

    dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse(project))
    open(os.path.join(destination, project+'.egg-link'), 'w'
         ).write(dist.location)

def _normalize_path(match):
    path = match.group(1)
    if os.path.sep == '\\':
        path = path.replace('\\\\', '/')
        if path.startswith('\\'):
            path = path[1:]
    return '/' + path.replace(os.path.sep, '/')

if sys.platform == 'win32':
    sep = r'[\\/]' # Windows uses both sometimes.
else:
    sep = re.escape(os.path.sep)
normalize_path = (
    re.compile(
        r'''[^'" \t\n\r!]+%(sep)s_[Tt][Ee][Ss][Tt]_%(sep)s([^"' \t\n\r]+)'''
        % dict(sep=sep)),
    _normalize_path,
    )

normalize_endings = re.compile('\r\n'), '\n'

normalize_script = (
    re.compile('(\n?)-  ([a-zA-Z_.-]+)-script.py\n-  \\2.exe\n'),
    '\\1-  \\2\n')

normalize_egg_py = (
    re.compile('-py\d[.]\d(-\S+)?.egg'),
    '-pyN.N.egg',
    )
