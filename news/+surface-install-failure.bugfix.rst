A failing ``pip``/``uv`` install subprocess is now reported as a clean
user error whose message ends with the command's own output, so the
actual diagnostic (for example a missing system header while building an
sdist) is the last thing on screen.  Previously the captured output went
to a detached ``print`` that could surface after the report or not at
all, and the failure was mislabeled "An internal error occurred due to a
bug in either zc.buildout or in a recipe being used", followed by a
traceback.  [gotcha]
