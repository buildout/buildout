import sys


class Debug:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

    def install(self):
        for option, value in sorted(self.options.items()):
            sys.stdout.write('%s %s\n' % (option, value))
        return ()

    update = install
