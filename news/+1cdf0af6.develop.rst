``develop-buildout`` documents dagger as the local pre-push CI gate:
replay cells on the committed tree (static gates included), the
measured boundary of what container cells catch versus what still
needs the runner, and how the engine's caches make the gate cheap on
a warm engine; plus the running-dagger-locally mechanics and two
module rules (exec-error output, ``ReturnType.ANY`` caching).
[gotcha]
