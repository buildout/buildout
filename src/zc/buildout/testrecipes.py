
class Debug:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

    def install(self):
        items = self.options.items()
        items.sort()
        for option, value in items:
            print "  %s=%r" % (option, value)
        return ()

    update = install
