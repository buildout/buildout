##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Various test-support utility functions

$Id$
"""


import BaseHTTPServer, ConfigParser, os, random, re, shutil, socket, sys
import tempfile, threading, time, urllib2, unittest

from zope.testing import doctest, renormalizing
import pkg_resources

import zc.buildout.buildout

def cat(dir, *names):
    path = os.path.join(dir, *names)
    if (not os.path.exists(path)
        and sys.platform == 'win32'
        and os.path.exists(path+'-script.py')
        ):
        path = path+'-script.py'
    print open(path).read(),

def ls(dir, *subs):
    if subs:
        dir = os.path.join(dir, *subs)
    names = os.listdir(dir)
    names.sort()
    for name in names:
        if os.path.isdir(os.path.join(dir, name)):
            print 'd ',
        else:
            print '- ',
        print name

def mkdir(dir, *subs):
    if subs:
        dir = os.path.join(dir, *subs)
    os.mkdir(dir)

def write(dir, *args):
    open(os.path.join(dir, *(args[:-1])), 'w').write(args[-1])

def system(command, input=''):
    i, o = os.popen4(command)
    if input:
        i.write(input)
    i.close()
    return o.read()

def get(url):
    return urllib2.urlopen(url).read()

def buildoutSetUp(test):
    # we both need to make sure that HOME isn't set and be prepared
    # to restore whatever it was after the test.
    test.globs['_oldhome'] = os.environ['HOME']
    del os.environ['HOME'] # pop doesn't truly remove it :(

    temporary_directories = []
    def mkdtemp(*args):
        d = tempfile.mkdtemp(*args)
        temporary_directories.append(d)
        return d

    os.environ['buildout-testing-index-url'] = 'file://'+mkdtemp()

    sample = mkdtemp('sample-buildout')

    # Create a basic buildout.cfg to avoid a warning from buildout:
    open(os.path.join(sample, 'buildout.cfg'), 'w').write(
        "[buildout]\nparts =\n"
        )

    # Use the buildout bootstrap command to create a buildout
    zc.buildout.buildout.Buildout(
        os.path.join(sample, 'buildout.cfg'),
        [('buildout', 'log-level', 'WARNING')]
        ).bootstrap([])

    test.globs.update(dict(
        __here = os.getcwd(),
        sample_buildout = sample,
        ls = ls,
        cat = cat,
        mkdir = mkdir,
        write = write,
        system = system,
        get = get,
        __temporary_directories__ = temporary_directories,
        __tearDown__ = [],
        mkdtemp = mkdtemp,
        ))

def buildoutTearDown(test):
    os.chdir(test.globs['__here'])
    for d in test.globs['__temporary_directories__']:
        shutil.rmtree(d)
    for f in test.globs['__tearDown__']:
        f()
    if test.globs.get('_oldhome') is not None:
        os.environ['HOME'] = test.globs['_oldhome']


script_template = '''\
#!%(python)s

import sys
sys.path[0:0] = %(path)r

from pkg_resources import load_entry_point
sys.exit(load_entry_point('zc.buildout', 'console_scripts', 'buildout')())
'''

def runsetup(d, executable, type='bdist_egg'):
    here = os.getcwd()
    try:
        os.chdir(d)
        os.spawnle(
            os.P_WAIT, executable, executable,
            'setup.py', '-q', type,
            {'PYTHONPATH': os.path.dirname(pkg_resources.__file__)},
            )
        if os.path.exists('build'):
            shutil.rmtree('build')
    finally:
        os.chdir(here)

def create_sample_eggs(test, executable=sys.executable):
    if 'sample_eggs' in test.globs:
        sample = os.path.dirname(test.globs['sample_eggs'])
    else:
        sample = test.globs['mkdtemp']('sample-eggs')
        test.globs['sample_eggs'] = os.path.join(sample, 'dist')
        write(sample, 'README.txt', '')

    for i in (0, 1):
        write(sample, 'eggrecipedemobeeded.py', 'y=%s\n' % i)
        write(
            sample, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='demoneeded', py_modules=['eggrecipedemobeeded'],"
            " zip_safe=True, version='1.%s', author='bob', url='bob', "
            "author_email='bob')\n"
            % i
            )
        runsetup(sample, executable, 'sdist')

    write(
        sample, 'setup.py',
        "from setuptools import setup\n"
        "setup(name='other', zip_safe=True, version='1.0', "
        "py_modules=['eggrecipedemobeeded'])\n"
        )
    runsetup(sample, executable)

    os.remove(os.path.join(sample, 'eggrecipedemobeeded.py'))

    for i in (1, 2, 3):
        write(
            sample, 'eggrecipedemo.py',
            'import eggrecipedemobeeded\n'
            'x=%s\n'
            'def main(): print x, eggrecipedemobeeded.y\n'
            % i)
        write(
            sample, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='demo', py_modules=['eggrecipedemo'],"
            " install_requires = 'demoneeded',"
            " entry_points={'console_scripts': ['demo = eggrecipedemo:main']},"
            " zip_safe=True, version='0.%s')\n" % i
            )
        runsetup(sample, executable)

def find_python(version):
    e = os.environ.get('PYTHON%s' % version)
    if e is not None:
        return e
    if sys.platform == 'win32':
        e = '\Python%s%s\python.exe' % tuple(version.split('.'))
        if os.path.exists(e):
            return e
    else:
        i, o = os.popen4('python%s -c "import sys; print sys.executable"'
                         % version)
        i.close()
        e = o.read().strip()
        o.close()
        if os.path.exists(e):
            return e
        i, o = os.popen4(
            'python -c "import sys; print \'%s.%s\' % sys.version_info[:2]"'
            )
        i.close()
        e = o.read().strip()
        o.close()
        if e == version:
            i, o = os.popen4('python -c "import sys; print sys.executable"')
            i.close()
            e = o.read().strip()
            o.close()
            if os.path.exists(e):
                return e
        
    raise ValueError(
        "Couldn't figure out the exectable for Python %(version)s.\n"
        "Set the environment variable PYTHON%(version)s to the location\n"
        "of the Python %(version)s executable before running the tests."
        )

def multi_python(test):
    p23 = find_python('2.3')
    p24 = find_python('2.4')
    create_sample_eggs(test, executable=p23)
    create_sample_eggs(test, executable=p24)
    test.globs['python2_3_executable'] = p23
    test.globs['python2_4_executable'] = p24



extdemo_c = """
#include <Python.h>
#include <extdemo.h>

static PyMethodDef methods[] = {{NULL}};

PyMODINIT_FUNC
initextdemo(void)
{
    PyObject *d;
    d = Py_InitModule3("extdemo", methods, "");
    PyDict_SetItemString(d, "val", PyInt_FromLong(EXTDEMO));    
}
"""

extdemo_setup_py = """
from distutils.core import setup, Extension

setup(name = "extdemo", version = "1.4", url="http://www.zope.org",
      author="Demo", author_email="demo@demo.com",
      ext_modules = [Extension('extdemo', ['extdemo.c'])],
      )
"""

def add_source_dist(test):
    import tarfile
    tmp = tempfile.mkdtemp('test-sdist')
    open(os.path.join(tmp, 'extdemo.c'), 'w').write(extdemo_c);
    open(os.path.join(tmp, 'setup.py'), 'w').write(extdemo_setup_py);
    open(os.path.join(tmp, 'README'), 'w').write("");
    open(os.path.join(tmp, 'MANIFEST.in'), 'w').write("include *.c\n");
    here = os.getcwd()
    os.chdir(tmp)
    status = os.spawnl(os.P_WAIT, sys.executable, sys.executable,
                       os.path.join(tmp, 'setup.py'), '-q', 'sdist')
    os.chdir(here)
    assert status == 0
    if sys.platform == 'win32':
        sname = 'extdemo-1.4.zip'
    else:
        sname = 'extdemo-1.4.tar.gz'

    shutil.move(
        os.path.join(tmp, 'dist', sname),
        os.path.join(test.globs['sample_eggs'], sname),
        )
    
def make_tree(test):
    sample_eggs = test.globs['sample_eggs']
    tree = dict(
        [(n, open(os.path.join(sample_eggs, n), 'rb').read())
         for n in os.listdir(sample_eggs)
         ])
    tree['index'] = {}
    return tree
    
class Server(BaseHTTPServer.HTTPServer):

    def __init__(self, tree, *args):
        BaseHTTPServer.HTTPServer.__init__(self, *args)
        self.tree = tree

    __run = True
    def serve_forever(self):
        while self.__run:
            self.handle_request()

    def handle_error(self, *_):
        self.__run = False

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

    def __init__(self, request, address, server):
        self.tree = server.tree
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(
            self, request, address, server)

    def do_GET(self):
        if '__stop__' in self.path:
           raise SystemExit
       
        tree = self.tree
        for name in self.path.split('/'):
            if not name:
                continue
            tree = tree.get(name)
            if tree is None:
                self.send_response(404, 'Not Found')
                out = '<html><body>Not Found</body></html>'
                self.send_header('Content-Length', str(len(out)))
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(out)
                return

        self.send_response(200)
        if isinstance(tree, dict):
            out = ['<html><body>\n']
            items = tree.items()
            items.sort()
            for name, v in items:
                if isinstance(v, dict):
                    name += '/'
                out.append('<a href="%s">%s</a><br>\n' % (name, name))
            out.append('</body></html>\n')
            out = ''.join(out)
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
        else:
            out = tree
            self.send_header('Content-Length', len(out))
            if name.endswith('.egg'):
                self.send_header('Content-Type', 'application/zip')
            elif name.endswith('.gz'):
                self.send_header('Content-Type', 'application/x-gzip')
            elif name.endswith('.zip'):
                self.send_header('Content-Type', 'application/x-gzip')
            else:
                self.send_header('Content-Type', 'text/html')
        self.end_headers()

        self.wfile.write(out)
                
    def log_request(*s):
        pass

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
    raise RuntimeError, "Can't find port"

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
        urllib2.urlopen(url+'__stop__')
    except Exception:
        pass
    if thread is not None:
        thread.join() # wait for thread to stop

def setUpServer(test, tree):
    port, thread = _start_server(tree, name=test.name)
    link_server = 'http://localhost:%s/' % port
    test.globs['link_server'] = link_server
    test.globs['__tearDown__'].append(lambda: stop_server(link_server, thread))
        

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
        except socket.error, e:
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
