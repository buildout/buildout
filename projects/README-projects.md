# Test projects

## Introduction

Within this `projects` directory are two sub directories: `packages` and `buildouts`.
For now, each contains only one package or buildout directory, but I want that to grow.
I want to use this to really test some common scenarios in a debuggable way.
Meaning: no doctests, simply run `bin/buildout` with a config, so you can add a breakpoint.


## Usage:

Within the main directory, so one level up, you can run:

```
make test-projects
```

Within the `projects` directory, you can just run all projects:

```
make
```

Or run a single one:

```
make simple
```

In the `Makefile` we go to one of the buildout directories.
Then we run `bin/buildout` from the top-level directory.


## Buildouts

Each sub directory has a `buildout.cfg` that does the following:

* `develop` one or more of our packages.
* Create a `bin/testscript` that has all those packages.
  With this you can check if you can import them.
* Automatically create the console scripts that each package defines.
  With this you can check that entry points are found correctly and the script works.


### Current buildouts

* `simple`: `hatchdemo` and `setuptoolsdemo` packages
* `namespaces`: `ns.hat` and `ns.tools` packages
* `final`: all packages in final form, installed from a wheel


## Packages

Each package registers a console script so you can check that the package can find itself.
I want to focus on modern packaging methods:

* No `setup.py`, just `pyproject.toml`.
* Everything in a `src` directory.
* Not just `setuptools`, also `hatchling` or other projects.
* Only native namespaces, when used.


### Current packages:

* `hatchdemo`: basic package using `hatchling`
* `setuptoolsdemo`: basic package using `setuptools`
* `ns.hat`: namespace package using `hatchling`
* `ns.tools`: namespace package using `setuptools`


### New package

To create a new package, you can do:

```
uvx hatch new <name>
```

I don't yet know if that can handle namespaces.
If you want a `setuptools` package, you can just do the same, and edit `pyproject.toml`.

Afterwards, register a console script in `pyroject.toml`:

```
[project.scripts]
hatchdemo = "hatchdemo:main"
```

And add a function in the `__init__.py` of the package, printing the name of the package:

```
def main():
    print("hatchdemo main script")
```

Or you copy an existing demo package and go from there.


## Compare with pip/uv

Each buildout config should have a mirror in a requirements file in the `requirements` directory.
If any scripts don't work there, there is not much point in trying to get this to work in Buildout.

```
make pips
```
