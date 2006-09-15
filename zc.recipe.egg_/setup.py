from setuptools import setup, find_packages

name = "zc.recipe.egg"
setup(
    name = name,
    version = "1.0.0b1",
    author = "Jim Fulton",
    author_email = "jim@zope.com",
    description = "Recipe for installing Python package distributions as eggs",
    long_description = open('README.txt').read(),
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
    entry_points = {'zc.buildout': ['default = %s:Egg' % name,
                                    'custom = %s:Custom' % name,
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
