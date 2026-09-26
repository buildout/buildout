"""The CI job table for the buildout-ci dagger module.

Pure data plus selection helpers: this module imports nothing from
dagger, so the tests in dagger/tests can load it without the SDK.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    name: str
    python: str
    commands: tuple[tuple[str, ...], ...]
    family: str
    setuptools: str = "75.8.2"
    pip: str = ""
    package: str = ""
    # the [buildout] installer the cell exercises; "uv" rows run
    # make test-uv, which self-contains buildout_testing_installer=uv
    installer: str = "pip"
    pip_install: tuple[str, ...] = ()
    # pinned uv release under test (the uv version matrix); threaded as
    # UV_VERSION, which the Makefile's test-uv target turns into a
    # repo-local `uv tool install` first on PATH
    uv: str = ""


FAMILIES = ("setuptools", "python", "pip", "scripts", "static", "coverage", "uv")

# valid --family values: the repo families plus the harness's own
# module family (kept out of FAMILIES: it runs no repo workflow job)
VALID_FAMILIES = FAMILIES + ("module",)

# rough duration hints for scheduling only, not gates
FAMILY_MINUTES = {"coverage": 15, "pip": 8, "python": 7, "setuptools": 4, "scripts": 1, "static": 1, "uv": 35}


def _scripts_commands(makefile: str, check_downloads: bool = True) -> tuple[tuple[str, ...], ...]:
    # installer = uv does not populate the buildout download cache (uv
    # keeps downloads in its own cache), so uv cells assert on eggs only
    checks = 'test -n "$(ls -A sandbox/eggs)"'
    if check_downloads:
        checks += ' && test -n "$(ls -A sandbox/downloads/dist)"'
    return (
        ("make", "-f", makefile, "sandbox/bin/buildout"),
        ("sh", "-c", "sandbox/bin/buildout -v -c .github/workflows/scripts-${PYTHON_VERSION}.cfg annotate buildout"),
        ("sh", "-c", "sandbox/bin/buildout -c .github/workflows/scripts-${PYTHON_VERSION}.cfg"),
        ("sh", "-c", checks),
    )


def _build_jobs() -> tuple[Job, ...]:
    make_and_pytest: tuple[tuple[str, ...], ...] = (("make",), ("make", "pytest"))
    # No Windows job from run-tests.yml: this podman host runs Linux containers only.
    return (
        *(
            Job(
                name=f"setuptools-{st}",
                python="3.10",
                # the workflow skips the pytest step on setuptools 63.0.0
                commands=(("make",),) if st == "63.0.0" else make_and_pytest,
                family="setuptools",
                setuptools=st,
            )
            for st in (
                "63.0.0",
                "65.7.0",
                "69.5.1",
                "74.1.3",
                "75.9.1",
                "79.0.1",
                "80.2.0",
                "80.10.2",
                "81.0.0",
            )
        ),
        Job(
            name="ruff",
            python="3.12",
            commands=(("make", "lint"),),
            family="static",
            # pin to the devenv-provided ruff (devenv.lock nixpkgs rev),
            # so the local gate matches CI exactly
            pip_install=("ruff==0.16.6",),
        ),
        Job(
            name="ty",
            python="3.12",
            commands=(("make", "typecheck"),),
            family="static",
            # pin to the devenv-provided ty: newer ty emits diagnostics
            # inside third-party eggs on the search path
            pip_install=("ty==0.0.78",),
        ),
        Job(
            name="radon",
            python="3.12",
            commands=(("make", "complexity"),),
            family="static",
            # pin to the devenv-provided radon (devenv.lock nixpkgs rev),
            # so the local gate matches CI exactly
            pip_install=("radon==6.0.1",),
        ),
        Job(
            name="mypy",
            python="3.12",
            commands=(("make", "typecheck-any"),),
            family="static",
            # pin to the devenv-provided mypy (devenv.lock nixpkgs rev),
            # so the local gate matches CI exactly
            pip_install=("mypy==2.1.0",),
        ),
        Job(
            name="setuptools-61-test-small",
            python="3.10",
            commands=(("make", "test-small"),),
            family="setuptools",
            setuptools="61.0.0",
        ),
        *(
            Job(
                name=f"python-{py}",
                python=py,
                commands=make_and_pytest,
                family="python",
                setuptools="75.6.0",
            )
            for py in ("3.9", "3.11", "3.12", "3.13", "3.14")
        ),
        *(
            Job(
                name=f"pip-{pip}-st-{st}",
                python="3.10",
                commands=make_and_pytest,
                family="pip",
                setuptools=st,
                pip=pip,
            )
            for pip in ("21.3.1", "22.3.1", "23.3.2", "24.3.1", "25.3", "26.1.2", "26.2.1")
            for st in ("65.7.0", "75.8.2")
        ),
        # named after the macos workflow job: same make targets, but in a Linux container
        Job(name="mac", python="3.10", commands=make_and_pytest, family="python"),
        # the test-uv.yml parallel set: the legacy suite through the uv
        # install pipeline. No pytest step there (no uv variant of it)
        # and no pip matrix (the uv seam never spawns pip).
        *(
            Job(
                name=f"setuptools-{st}-uv",
                python="3.10",
                commands=(("make", "test-uv"),),
                family="uv",
                setuptools=st,
                installer="uv",
            )
            for st in (
                "63.0.0",
                "65.7.0",
                "69.5.1",
                "74.1.3",
                "75.9.1",
                "79.0.1",
                "80.2.0",
                "80.10.2",
                "81.0.0",
            )
        ),
        *(
            Job(
                name=f"python-{py}-uv",
                python=py,
                commands=(("make", "test-uv"),),
                family="uv",
                setuptools="75.6.0",
                installer="uv",
            )
            for py in ("3.9", "3.11", "3.12", "3.13", "3.14")
        ),
        Job(name="mac-uv", python="3.10", commands=(("make", "test-uv"),), family="uv", installer="uv"),
        # the uv version matrix: the legacy suite through the uv pipeline
        # with the uv under test pinned (UV_VERSION) to the earliest
        # supported 0.12.x (the setup.py floor) and the five most recent,
        # on the most recent setuptools (81.0.0 caps the declared
        # setuptools<82 range)
        *(
            Job(
                name=f"uv-{uv}",
                python="3.12",
                commands=(("make", "test-uv"),),
                family="uv",
                setuptools="81.0.0",
                installer="uv",
                uv=uv,
            )
            for uv in ("0.12.11", "0.12.13", "0.12.14", "0.12.15", "0.12.16", "0.12.17")
        ),
        # the uv variant of run-tests.yml's generate-scripts: same
        # packages and pythons, with buildout_testing_installer=uv set
        # between bootstrap and the buildout runs (see main.py's _run)
        *(
            Job(
                name=f"scripts-uv-{pkg}-py{py}",
                python=py,
                commands=_scripts_commands(".github/workflows/Makefile-scripts", check_downloads=False),
                family="scripts",
                package=pkg,
                installer="uv",
            )
            for py in ("3.9", "3.10", "3.11", "3.12", "3.13", "3.14")
            for pkg in ("zest.releaser", "pyspf")
        ),
        Job(name="coverage-legacy", python="3.12", commands=(("make", "coverage"),), family="coverage"),
        Job(name="coverage-pytest", python="3.12", commands=(("make", "coverage-pytest"),), family="coverage"),
        Job(name="coverage-unittests", python="3.12", commands=(("make", "coverage-unittests"),), family="coverage"),
        *(
            Job(
                name=f"scripts-{pkg}-py{py}",
                python=py,
                commands=_scripts_commands(".github/workflows/Makefile-scripts"),
                family="scripts",
                package=pkg,
            )
            for py in ("3.9", "3.10", "3.11", "3.12", "3.13", "3.14")
            for pkg in ("zest.releaser", "pyspf")
        ),
        *(
            Job(
                name=f"scripts-head-{pkg}-py{py}",
                python=py,
                commands=_scripts_commands(".github/workflows/Makefile-scripts-setuptools-head"),
                family="scripts",
                package=pkg,
            )
            for py in ("3.10", "3.11", "3.12", "3.13", "3.14")
            for pkg in ("zest.releaser", "pyspf")
        ),
        # the harness itself, dogfooded as a CI cell: Source ignores
        # dagger/src (module edits must not bust cell caches), so
        # main.py grafts the dagger/ dir into /src for this family
        Job(
            name="module-tests",
            python="3.12",
            commands=(("python", "-m", "pytest", "dagger/tests", "-v"),),
            family="module",
            pip_install=("pytest==8.4.2", "pyyaml==6.0.3"),
        ),
    )


JOBS = _build_jobs()


def _find_job(name: str) -> Job:
    for job in JOBS:
        if job.name == name:
            return job
    valid = "\n".join(job.name for job in JOBS)
    raise ValueError(f"unknown job {name!r}; valid jobs:\n{valid}")


def _check_family(family: str) -> None:
    if not family or family in VALID_FAMILIES:
        return
    valid = "\n".join(VALID_FAMILIES)
    raise ValueError(f"unknown family {family!r}; valid families:\n{valid}")


def _select_jobs(family: str) -> list[Job]:
    _check_family(family)
    return [job for job in JOBS if not family or job.family == family]
