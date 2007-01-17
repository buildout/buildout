import os
from setuptools import setup, find_packages

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

name = "zc.recipe.egg"
setup(
    name = name,
    version = "1.0.0b3",
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "Recipe for installing Python package distributions as eggs",
    long_description = (
        read('README.txt')
        + '\n' +
        read('CHANGES.txt')
        + '\n' +
        'Detailed Documentation\n'
        '**********************\n'
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'README.txt')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'selecting-python.txt')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'custom.txt')
        + '\n' +
        read('src', 'zc', 'recipe', 'egg', 'api.txt')
        + '\n' +
        'Download\n'
        '**********************\n'
        ),
    license = "ZPL 2.1",
    keywords = "development build",
    url='http://svn.zope.org/zc.buildout',

    packages = find_packages('src'),
    include_package_data = True,
    package_dir = {'':'src'},
    namespace_packages = ['zc', 'zc.recipe'],
    install_requires = ['zc.buildout >=1.0.0b3', 'setuptools'],
    tests_require = ['zope.testing'],
    test_suite = name+'.tests.test_suite',
    entry_points = {'zc.buildout': ['default = %s:Scripts' % name,
                                    'script = %s:Scripts' % name,
                                    'scripts = %s:Scripts' % name,
                                    'eggs = %s:Eggs' % name,
                                    'custom = %s:Custom' % name,
                                    'develop = %s:Develop' % name,
                                    ]
                    },
    zip_safe=False,
    classifiers = [
       'Framework :: Buildout',
       'Development Status :: 4 - Beta',
       'Intended Audience :: Developers',
       'License :: OSI Approved :: Zope Public License',
       'Topic :: Software Development :: Build Tools',
       'Topic :: Software Development :: Libraries :: Python Modules',
       ],
    )
