Buildout Egg-Installation Recipe
================================

The egg-installation recipe installes eggs into a buildout eggs
directory.  It also generates scripts in a buildout bin directory with 
egg paths baked into them.

The recipe provides the following options:

eggs
    A list of eggs to install given as one ore more setuptools
    requirement strings.  Each string must be given on a separate
    line.

find-links
    One or more addresses of link servers to be searched for
    distributions.  This is optional.  If not specified, links
    specified in the buildout section will be used, if any.

index
    The optional address of a distribution index server.  If not
    specified, then the option from the buildout section will be
    used.  If not specified in the part data or in the buildout
    section, then http://www.python.org/pypi is used.

python
    The name of a section defining the Python executable to use.
    This defaults to buildout.
    
unzip
   The value of this option must be either true or false. If the value
   is true, then the installed egg will be unzipped. Note that this is
   only effective when an egg is installed.  If a zipped egg already 
   exists in the eggs directory, it will not be unzipped.

To do
-----

- Some way to freeze the egg-versions used.  This includes some way to
  record which versions were selected dynamially and then a way to
  require that the recorded versions be used in a later run.

- More control over script generation.  In particular, some way to 
  specify data t be recored in the script.

- Honor the buildout offline option.

- Windows suppprt

  - Generate exe files

  - Make sure tests work under windows
