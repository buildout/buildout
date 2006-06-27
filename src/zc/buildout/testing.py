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

def cat(dir, *names):
    path = os.path.join(dir, *names)
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

def buildoutSetUp(test, clear_home=True):
    if clear_home:
        # we both need to make sure that HOME isn't set and be prepared
        # to restore whatever it was after the test.
        test.globs['_oldhome'] = os.environ.pop('HOME', None)

    temporary_directories = []
    def mkdtemp(*args):
        d = tempfile.mkdtemp(*args)
        temporary_directories.append(d)
        return d

    sample = mkdtemp('sample-buildout')
    for name in ('bin', 'eggs', 'develop-eggs', 'parts'):
        os.mkdir(os.path.join(sample, name))

    # make sure we can import zc.buildout and setuptools
    import zc.buildout, setuptools

    # Generate buildout script
    dest = os.path.join(sample, 'bin', 'buildout')
    open(dest, 'w').write(
        script_template % dict(python=sys.executable, path=sys.path)
        )
    try:
        os.chmod(dest, 0755)
    except (AttributeError, os.error):
        pass


    open(os.path.join(sample, 'buildout.cfg'), 'w').write(
        "[buildout]\nparts =\n"
        )
    open(os.path.join(sample, '.installed.cfg'), 'w').write(
        "[buildout]\nparts =\n"
        )

    test.globs.update(dict(
        __here = os.getcwd(),
        sample_buildout = sample,
        ls = ls,
        cat = cat,
        mkdir = mkdir,
        write = write,
        system = system,
        get = get,
        __original_wd__ = os.getcwd(),
        __temporary_directories__ = temporary_directories,
        mkdtemp = mkdtemp,
        ))

def buildoutTearDown(test):
    for d in test.globs['__temporary_directories__']:
        shutil.rmtree(d)
    os.chdir(test.globs['__original_wd__'])
    if test.globs.get('_oldhome') is not None:
        os.environ['HOME'] = test.globs['_oldhome']


script_template = '''\
#!%(python)s

import sys
sys.path[0:0] = %(path)r

from pkg_resources import load_entry_point
sys.exit(load_entry_point('zc.buildout', 'console_scripts', 'buildout')())
'''

def runsetup(d, executable):
    here = os.getcwd()
    try:
        os.chdir(d)
        os.spawnle(
            os.P_WAIT, executable, executable,
            'setup.py', '-q', 'bdist_egg',
            {'PYTHONPATH': os.path.dirname(pkg_resources.__file__)},
            )
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
            " zip_safe=True, version='1.%s')\n"
            % i
            )
        runsetup(sample, executable)

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

def multi_python(test):
    defaults = ConfigParser.RawConfigParser()
    defaults.readfp(open(os.path.join(os.environ['HOME'],
                                      '.buildout', 'default.cfg')))
    p23 = defaults.get('python2.3', 'executable')
    p24 = defaults.get('python2.4', 'executable')
    create_sample_eggs(test, executable=p23)
    create_sample_eggs(test, executable=p24)
    test.globs['python2_3_executable'] = p23
    test.globs['python2_4_executable'] = p24


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

def start_server(tree):
    port = get_port()
    threading.Thread(target=_run, args=(tree, port)).start()
    wait(port, up=True)
    return port

def stop_server(url):
    try:
        urllib2.urlopen(url+'__stop__')
    except Exception:
        pass

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
