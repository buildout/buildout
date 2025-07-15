import os
import sys


class Environ:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.options = options

    def install(self):
        _ = self.options['name']
        sys.stdout.write('HOME %s\\n' % os.environ['HOME'])
        sys.stdout.write('USERPROFILE %s\\n' % os.environ['USERPROFILE'])
        sys.stdout.write('expanduser %s\\n' % os.path.expanduser('~'))
        return ()

    update = install
