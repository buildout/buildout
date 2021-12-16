import logging
import subprocess
import sys
import os
import tempfile
import zc.buildout
import shutil
import re
from pkg_resources import Requirement
from distutils.errors import DistutilsError


URL_SCHEME = re.compile('([-+.a-z0-9]{2,}):', re.I).match
logger = logging.getLogger('zc.buildout.pipindex')


def parse_requirement_arg(spec):
    try:
        return Requirement.parse(spec)
    except ValueError:
        raise DistutilsError(
            "Not a URL, existing file, or requirement spec: %r" % (spec,)
        )


class Index(object):

    def __init__(self, index, links, allow_hosts, env):
        self.index = index
        self.links = links
        self.allow_hosts = allow_hosts
        self.env = env

    def obtain(self, requirement):
        return None

    def __getitem__(self, key):
        return []

    def download(self, spec, tmp):

        piptmp = tempfile.mkdtemp()
        try:
            if isinstance(spec, Requirement):
                self._run_pip(['download', '--no-deps', '-d', piptmp, spec])
            else:
                scheme = URL_SCHEME(spec)
                if scheme:
                    exit_code = subprocess.call(['wget', '-q', '-P', piptmp, spec])
                elif os.path.exists(spec):
                    # Existing file or directory, just return it
                    return spec
                else:
                    spec = parse_requirement_arg(spec)
                    args = ['download', '--index', self.index, '--no-deps', '-d', piptmp, spec]
                    if self.links:
                        args.extend(['--find-links', self.links])
                    self._run_pip(args)
            files = os.listdir(piptmp)
            assert len(files) == 1
            file = files[0]
            shutil.move(os.path.join(piptmp, file), tmp)
            result = os.path.join(tmp, os.path.basename(file))
            assert os.path.exists(result)
            return unicode(result)
        finally:
            zc.buildout.rmtree.rmtree(piptmp)

    def _run_pip(self, args):
        cmdargs = [sys.executable, '-m', 'pip']
        cmdargs.extend(args)
        exit_code = subprocess.call(list(cmdargs), env=self.env)

        if exit_code:
            logger.error(
                "An error occurred when trying to install %s. "
                "Look above this message for any errors that "
                "were output by pip install.")
            sys.exit(1)

