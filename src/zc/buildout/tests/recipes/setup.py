from setuptools import setup

entry_points = (
'''
[zc.buildout]
mkdir = mkdir:Mkdir
debug = debug:Debug
environ = environ:Environ
''')

setup(
    name="recipes",
    entry_points=entry_points,
)
