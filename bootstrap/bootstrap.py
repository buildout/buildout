##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, re, shutil, sys, tempfile, textwrap, urllib, urllib2

# We have to manually parse our options rather than using one of the stdlib
# tools because we want to pass the ones we don't recognize along to
# zc.buildout.buildout.main.

configuration = {
    '--ez_setup-source': 'http://peak.telecommunity.com/dist/ez_setup.py',
    '--version': '',
    '--download-base': None,
    '--eggs': None}

helpstring = __doc__ + textwrap.dedent('''
    This script recognizes the following options itself.  The first option it
    encounters that is not one of these will cause the script to stop parsing
    options and pass the rest on to buildout.  Therefore, if you want to use
    any of the following options *and* buildout command-line options like
    -c, first use the following options, and then use the buildout options.

    Options:
      --version=ZC_BUILDOUT_VERSION
                Specify a version number of the zc.buildout to use
      --ez_setup-source=URL_OR_FILE
                Specify a URL or file location for the ez_setup file.
                Defaults to
                %(--ez_setup-source)s
      --download-base=URL_OR_DIRECTORY
                Specify a URL or directory for downloading setuptools and
                zc.buildout.  Defaults to PyPI.
      --eggs=DIRECTORY
                Specify a directory for storing eggs.  Defaults to a temporary
                directory that is deleted when the bootstrap script completes.

    By using --ez_setup-source and --download-base to point to local resources,
    you can keep this script from going over the network.
    ''' % configuration)
match_equals = re.compile(r'(%s)=(.*)' % ('|'.join(configuration),)).match
args = sys.argv[1:]
if args == ['--help']:
    print helpstring
    sys.exit(0)

# If we end up using a temporary directory for storing our eggs, this will
# hold the path of that directory.  On the other hand, if an explicit directory
# is specified in the argv, this will remain None.
tmpeggs = None

while args:
    val = args[0]
    if val in configuration:
        del args[0]
        if not args or args[0].startswith('-'):
            print "ERROR: %s requires an argument."
            print helpstring
            sys.exit(1)
        configuration[val] = args[0]
    else:
        match = match_equals(val)
        if match and match.group(1) in configuration:
            configuration[match.group(1)] = match.group(2)
        else:
            break
    del args[0]

for name in ('--ez_setup-source', '--download-base'):
    val = configuration[name]
    if val is not None and '://' not in val: # We're being lazy.
        configuration[name] = 'file://%s' % (
            urllib.pathname2url(os.path.abspath(os.path.expanduser(val))),)

if (configuration['--download-base'] and
    not configuration['--download-base'].endswith('/')):
    # Download base needs a trailing slash to make the world happy.
    configuration['--download-base'] += '/'

if not configuration['--eggs']:
    configuration['--eggs'] = tmpeggs = tempfile.mkdtemp()
else:
    configuration['--eggs'] = os.path.abspath(
        os.path.expanduser(configuration['--eggs']))

# The requirement is what we will pass to setuptools to specify zc.buildout.
requirement = 'zc.buildout'
if configuration['--version']:
    requirement += '==' + configuration['--version']

try:
    import setuptools # A flag.  Sometimes pkg_resources is installed alone.
    import pkg_resources
except ImportError:
    ez_code = urllib2.urlopen(
        configuration['--ez_setup-source']).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setuptools_args = dict(to_dir=configuration['--eggs'], download_delay=0)
    if configuration['--download-base']:
        setuptools_args['download_base'] = configuration['--download-base']
    ez['use_setuptools'](**setuptools_args)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c
cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(configuration['--eggs'])]

if configuration['--download-base']:
    cmd.extend(['-f', quote(configuration['--download-base'])])

cmd.append(requirement)

ws = pkg_resources.working_set
env = dict(
    os.environ,
    PYTHONPATH=ws.find(pkg_resources.Requirement.parse('setuptools')).location)

is_jython = sys.platform.startswith('java')
if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else: # Windows needs this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occured when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(configuration['--eggs'])
ws.require(requirement)
import zc.buildout.buildout
args.append('bootstrap')
zc.buildout.buildout.main(args)
if tmpeggs is not None:
    shutil.rmtree(tmpeggs)
