Fixed the test-suite flake behind the intermittent
``test_dependencylinks_option`` failure under pytest-xdist: the
``update_env`` fixture built fake zc.buildout releases with
``python -m build --sdist`` directly on the shared checkout, and
setuptools rewrote ``src/zc.buildout.egg-info`` in place.  Sample
buildouts develop zc.buildout from that checkout, so part signatures
hash ``src/``; a concurrent worker hashing the tree during the rewrite
window computed a different signature and parts flipped from
"Updating" to "Uninstalling/Installing".  The fake releases are now
built from a private copy of the tree.  [gotcha]
