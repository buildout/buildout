from setuptools import setup

setup(
    name = "showversions",
    entry_points = {'zc.buildout': ['default = showversions:Recipe']},
)
