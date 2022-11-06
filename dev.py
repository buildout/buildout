##############################################################################
#
# Copyright (c) 2005 Zope Foundation and Contributors.
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
"""Bootstrap the buildout project itself.

This is different from a normal bootstrapping process because the
buildout egg itself is installed as a develop egg.
"""
import sys

if sys.version_info < (2, 7):
    raise SystemError("Outside Python 2.7, no support for Python 2.x.")

if sys.version_info > (3, ) and sys.version_info < (3, 5):
    raise SystemError("No support for Python 3.x under 3.5.")


import os, shutil, subprocess, tempfile

os.environ["SETUPTOOLS_USE_DISTUTILS"] = "stdlib"

def main(args):
    for d in 'eggs', 'develop-eggs', 'bin', 'parts':
        if not os.path.exists(d):
            os.mkdir(d)

    bin_buildout = os.path.join('bin', 'buildout')
    if os.path.isfile(bin_buildout):
        os.remove(bin_buildout)

    if os.path.isdir('build'):
        shutil.rmtree('build')

    print("Current directory %s" % os.getcwd())

    #######################################################################
    def install_pip():
        print('')
        print('Install pip')
        print('')
        try:
            from urllib.request import urlopen
        except ImportError:
            from urllib2 import urlopen

        tmp = tempfile.mkdtemp(prefix='buildout-dev-')
        try:
            get_pip = os.path.join(tmp, 'get-pip.py')
            if sys.version_info < (3, ):
                GET_PIP_URL = 'https://bootstrap.pypa.io/pip/2.7/get-pip.py'
            elif (sys.version_info.major, sys.version_info.minor) == (3, 5):
                GET_PIP_URL = 'https://bootstrap.pypa.io/pip/3.5/get-pip.py'
            elif (sys.version_info.major, sys.version_info.minor) == (3, 6):
                GET_PIP_URL = 'https://bootstrap.pypa.io/pip/3.6/get-pip.py'
            else:
                GET_PIP_URL = 'https://bootstrap.pypa.io/pip/get-pip.py'
            with open(get_pip, 'wb') as f:
                f.write(urlopen(GET_PIP_URL).read())

            sys.stdout.flush()
            if subprocess.call([sys.executable, get_pip]):
                raise RuntimeError("Failed to install pip.")
        finally:
            shutil.rmtree(tmp)
        print("Restart")
        sys.stdout.flush()
        return_code = subprocess.call(
            [sys.executable] + sys.argv
        )
        sys.exit(return_code)

    try:
        import pip
        print('')
        try:
            print(subprocess.check_output(
                [sys.executable] + ['-m', 'pip', '--version'],
                stderr=subprocess.STDOUT,
            ).decode('utf8'))
            print('is installed.')
        except subprocess.CalledProcessError as e:
            # some debian/ubuntu based machines
            # have broken pip installs
            # that cannot import distutils or html5lib
            # thus try to install via get-pip
            if (b"ImportError" in e.output or
                   b"ModuleNotFoundError" in e.output):
                install_pip()
            raise e
    except ImportError:
        install_pip()

    ######################################################################
    def check_upgrade(package):
        print('')
        print('Try to upgrade %s' % package)
        print('')

        try:
            sys.stdout.flush()
            output = subprocess.check_output(
                [sys.executable] + ['-m', 'pip', 'install',
                '--disable-pip-version-check', '--upgrade', package],
                stderr=subprocess.STDOUT,
            )
            was_up_to_date = b"up-to-date" in output or b"already satisfied" in output
            if not was_up_to_date:
                print(output.decode('utf8'))
            return not was_up_to_date
        except subprocess.CalledProcessError as e:
            print(e.output)
            raise RuntimeError("Upgrade of %s failed." % package)

    def install_pinned_version(package, version):
        print('')
        print('Try to install version %s of %s' % (version, package))
        print('')

        try:
            sys.stdout.flush()
            output = subprocess.check_output(
                [sys.executable] + ['-m', 'pip', 'install',
                '--disable-pip-version-check', package+'=='+version],
                stderr=subprocess.STDOUT,
            )
            was_up_to_date = b"already satisfied" in output
            if not was_up_to_date:
                print(output.decode('utf8'))
            return not was_up_to_date
        except subprocess.CalledProcessError as e:
            print(e.output)
            raise RuntimeError(
                "Install version %s of %s failed." % (version, package)
            )

    def show(package):
        try:
            sys.stdout.flush()
            output = subprocess.check_output(
                [sys.executable, '-m', 'pip', 'show', package],
            )
            for line in output.splitlines():
                if line.startswith(b'Name') or line.startswith(b'Version'):
                    print(line.decode('utf8'))
        except subprocess.CalledProcessError:
            raise RuntimeError("Show version of %s failed." % package)


    need_restart = False

    package = 'pip'
    if args.pip_version:
        did_upgrade = install_pinned_version(package, args.pip_version)
    else:
        did_upgrade = check_upgrade(package)
    show(package)
    need_restart = need_restart or did_upgrade

    package = 'setuptools'
    if args.setuptools_version:
        did_upgrade = install_pinned_version(package, args.setuptools_version)
    else:
        did_upgrade = check_upgrade(package)
    show(package)
    need_restart = need_restart or did_upgrade

    package = 'wheel'
    did_upgrade = check_upgrade(package)
    show(package)
    need_restart = need_restart or did_upgrade

    if need_restart:
        print("Restart")
        sys.stdout.flush()
        return_code = subprocess.call(
            [sys.executable] + sys.argv
        )
        sys.exit(return_code)
    ######################################################################
    print('')
    print('Install buildout')
    print('')
    sys.stdout.flush()
    if subprocess.call(
        [sys.executable] +
        ['setup.py', '-q', 'develop', '-m', '-x', '-d', 'develop-eggs'],
        ):
        raise RuntimeError("buildout build failed.")

    import pkg_resources

    pkg_resources.working_set.add_entry('src')

    import zc.buildout.easy_install
    zc.buildout.easy_install.scripts(
        ['zc.buildout'], pkg_resources.working_set, sys.executable, 'bin')

    ######################################################################
    def install_coverage():
        print('')
        print('Install coverage')
        print('')
        bin_pip = os.path.join('bin', 'pip')
        if subprocess.call(
            [sys.executable] +
            ['-m', 'pip', 'install', 'coverage'],
            ):
            raise RuntimeError("coverage install failed.")

    try:
        import coverage
    except ImportError:
        install_coverage()

    ######################################################################
    print('')
    print('Run buildout')
    print('')
    bin_buildout = os.path.join('bin', 'buildout')

    if sys.platform.startswith('java'):
        # Jython needs the script to be called twice via sys.executable
        assert subprocess.Popen([sys.executable, bin_buildout, '-N']).wait() == 0

    sys.stdout.flush()
    sys.exit(subprocess.Popen(bin_buildout).wait())

def parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description='Setup buildout development environment')
    parser.add_argument('--pip-version', help='version of pip to install',
                        action='store')
    parser.add_argument('--setuptools-version', help='version of setuptools to install',
                        action='store')
    parser.add_argument('--no-clean', 
        help='not used in the code, find out if still needed in Makefile',
                        action='store_const', const='NO_CLEAN')

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    main(parse_args())
