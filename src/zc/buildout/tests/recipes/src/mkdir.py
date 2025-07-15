# This is the final version of the mkdir.py file that we created
# in the buildout.txt tests.

import logging
import os
import zc.buildout


class Mkdir:

    def __init__(self, buildout, name, options):
        self.name, self.options = name, options

        # Normalize paths and check that their parent
        # directories exist:
        paths = []
        for path in options['path'].split():
            path = os.path.join(buildout['buildout']['directory'], path)
            if not os.path.isdir(os.path.dirname(path)):
                logging.getLogger(self.name).error(
                    'Cannot create %s. %s is not a directory.',
                    options['path'], os.path.dirname(options['path']))
                raise zc.buildout.UserError('Invalid Path')
            paths.append(path)
        options['path'] = ' '.join(paths)

    def install(self):
        paths = self.options['path'].split()
        for path in paths:
            logging.getLogger(self.name).info(
                'Creating directory %s', os.path.basename(path))
            os.mkdir(path)
            self.options.created(path)

        return self.options.created()

    def update(self):
        pass
