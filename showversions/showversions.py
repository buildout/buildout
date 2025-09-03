import pkg_resources
import sys

print_ = lambda *a: sys.stdout.write(' '.join(map(str, a))+'\\n')

class Recipe:
    def __init__(self, buildout, name, options):
        pass
    def install(self):
        for project in ['zc.buildout']:
            req = pkg_resources.Requirement.parse(project)
            print_(project, pkg_resources.working_set.find(req).version)
        return ()
    update = install
