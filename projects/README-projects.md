# Test projects

## Introduction

Within this `projects` directory are three directories: `packages`, `buildouts`, and `requirements`.
I want to use this to really test some common scenarios in a debuggable way.
Meaning: no doctests, simply run `bin/buildout` with a config, so you can add a breakpoint.


## Usage:

Within the main directory, so one level up, you can run:

```
make test-projects
```

This runs `make` within the `projects` directory, so you can also go to the `projects` directory yourself and run make:

```
make
```

Or run a single one:

```
make simple
```

In most of the `Makefile` targets we go to one of the buildout directories.
There we run `bin/buildout` from the top-level directory.


## Buildouts

Each sub directory has a `buildout.cfg` that does the following:

* `develop` zero, one, or more of our packages.
* Create a `bin/testscript` that has all those packages.
  With this you can check if you can import them.
* Automatically create the console scripts that each package defines.
  With this you can check that entry points are found correctly and the script works.

### Shared config

The buildouts extend `projects/buildout/shared.cfg` which has the common config.
Among others, it defines a download cache in `projects/downloads/dist`, and an eggs cache in `projects/eggs`.

### Downloads

The `make downloads` target creates final wheels of all our packages, and puts them in `projects/downloads/dist`, so buildouts can find them.

### Current buildouts

* `simple`: `hatchdemo` and `setuptoolsdemo` packages
* `namespaces`: `ns.ancient`, `ns.hat` and `ns.tools` packages
* `final`: all packages in final form, installed from a wheel in the downloads cache
* `mixed`: all namespace packages, some in development, some final

The buildout that I most expect to fail, is the mixed one.
But so far it works.


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
* `ns.ancient`: namespace package using `setuptools`, and still a `setup.py`


### New package

I created the basis of the `hatchdemo` package with this command:

```
uvx hatch new hatchdemo
```

So if you want to create a new package, you can use the same command.
But copying and editing is likely easier.
That is what I did for the other projects.
I removed lots of metadata though, which we did not need.

If you create your own package by hand, make sure to register a console script in `pyroject.toml`:

```
[project.scripts]
<script name> = "<package name>:main"
```

And add a function in the `__init__.py` of the package, printing the name of the package:

```
def main():
    print("<package name> main script")
```

Or you copy an existing demo package and go from there.


## Compare with pip/uv

Each buildout config should have a mirror in a requirements file in the `requirements` directory.
If any scripts don't work there, there is not much point in trying to get this to work in Buildout.

```
make pips
```

Note: when you run `make` or `make all`, the `pips` target is not run, as we only want to know if our buildouts work.
