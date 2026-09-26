"""Tests for the dagger CI module's job table (dagger/src/buildout_ci/jobs.py)."""

import ast
import importlib.util
import sys
from collections import Counter
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "run-tests.yml"
UV_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "test-uv.yml"
JOBS_PATH = REPO_ROOT / "dagger" / "src" / "buildout_ci" / "jobs.py"

MAKE_AND_PYTEST = (("make",), ("make", "pytest"))
MAKE_TEST_UV = (("make", "test-uv"),)


def _load_jobs():
    # Load jobs.py straight from its file: importing the buildout_ci
    # package would execute its SDK-generated __init__.py, which imports
    # dagger — these tests must also run where the SDK is not installed.
    spec = importlib.util.spec_from_file_location("buildout_ci_jobs", JOBS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


jobs = _load_jobs()


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW_PATH.read_text())


@pytest.fixture(scope="module")
def uv_workflow():
    return yaml.safe_load(UV_WORKFLOW_PATH.read_text())


def _devenv_run(step_run):
    """Extract (pinned python, make command) from a `devenv shell ... -- make ...` run line."""
    segments = step_run.split(" -- ")
    python = "3.12"  # the devenv default (languages.python.version in devenv.nix)
    for segment in segments:
        if "languages.python.version:string" in segment:
            python = segment.split('"')[1]
    return python, tuple(segments[-1].split())


def _workflow_cells(data):
    """Derive the job cells .github/workflows/run-tests.yml defines.

    Returns {Job name: expected Job fields}. The windows job has no
    cell: the dagger module runs Linux containers only. The dagger job
    defines no cells either: its family matrix is checked separately.
    """
    wf = data["jobs"]
    cells = {}

    # setuptools matrix; the workflow skips the pytest step on 63.0.0
    matrix = wf["setuptools"]["strategy"]["matrix"]
    for st in matrix["setuptools-version"]:
        commands = (("make",),) if st == "63.0.0" else MAKE_AND_PYTEST
        cells[f"setuptools-{st}"] = {
            "python": matrix["python-version"][0],
            "commands": commands,
            "family": "setuptools",
            "setuptools": st,
        }

    # setuptools61 is much slower, so the workflow runs make test-small only
    matrix = wf["setuptools61"]["strategy"]["matrix"]
    cells["setuptools-61-test-small"] = {
        "python": matrix["python-version"][0],
        "commands": (("make", "test-small"),),
        "family": "setuptools",
        "setuptools": matrix["setuptools-version"][0],
    }

    # python matrix, pinned to the last setuptools all pythons support
    matrix = wf["python"]["strategy"]["matrix"]
    for py in matrix["python-version"]:
        cells[f"python-{py}"] = {
            "python": py,
            "commands": MAKE_AND_PYTEST,
            "family": "python",
            "setuptools": matrix["setuptools-version"][0],
        }

    # pip matrix: pip version x setuptools version
    matrix = wf["pip"]["strategy"]["matrix"]
    for pip in matrix["pip-version"]:
        for st in matrix["setuptools-version"]:
            cells[f"pip-{pip}-st-{st}"] = {
                "python": matrix["python-version"][0],
                "commands": MAKE_AND_PYTEST,
                "family": "pip",
                "setuptools": st,
                "pip": pip,
            }

    # the macos job, named mac in the Job table
    matrix = wf["mac"]["strategy"]["matrix"]
    cells["mac"] = {
        "python": matrix["python-version"][0],
        "commands": MAKE_AND_PYTEST,
        "family": "python",
        "setuptools": matrix["setuptools-version"][0],
    }

    # static tier: the lint, typecheck, and complexity jobs
    steps = {step["name"]: step for step in wf["lint"]["steps"] if "name" in step}
    python, command = _devenv_run(steps["Run ruff"]["run"])
    cells["ruff"] = {"python": python, "commands": (command,), "family": "static"}
    steps = {step["name"]: step for step in wf["typecheck"]["steps"] if "name" in step}
    python, command = _devenv_run(steps["Run ty"]["run"])
    cells["ty"] = {"python": python, "commands": (command,), "family": "static"}
    steps = {step["name"]: step for step in wf["complexity"]["steps"] if "name" in step}
    python, command = _devenv_run(steps["Run complexity gate"]["run"])
    cells["radon"] = {"python": python, "commands": (command,), "family": "static"}
    steps = {step["name"]: step for step in wf["typecheck-any"]["steps"] if "name" in step}
    python, command = _devenv_run(steps["Run mypy"]["run"])
    cells["mypy"] = {"python": python, "commands": (command,), "family": "static"}

    # coverage variants
    for wf_name, job_name in (
        ("coverage", "coverage-legacy"),
        ("coverage-pytest", "coverage-pytest"),
        ("coverage-unittests", "coverage-unittests"),
    ):
        steps = {step["name"]: step for step in wf[wf_name]["steps"] if "name" in step}
        run_step = next(step for step in steps.values() if "coverage" in step["run"])
        python, command = _devenv_run(run_step["run"])
        cells[job_name] = {"python": python, "commands": (command,), "family": "coverage"}

    # generate-scripts matrix: package x python, driving the scripts makefile
    scripts = wf["generate-scripts"]
    matrix = scripts["strategy"]["matrix"]
    steps = {step["name"]: step for step in scripts["steps"] if "name" in step}
    bootstrap = steps["Setup buildout virtualenv"]["run"].split(" -- ")[-1].split()
    makefile = bootstrap[bootstrap.index("-f") + 1]
    for py in matrix["python-version"]:
        for pkg in matrix["package"]:
            cells[f"scripts-{pkg}-py{py}"] = {
                "python": py,
                "commands": jobs._scripts_commands(makefile),
                "family": "scripts",
                "package": pkg,
            }

    return cells


def _uv_workflow_cells(data):
    """Derive the job cells .github/workflows/test-uv.yml defines.

    The uv parallel set mirrors the setuptools, python, and mac jobs of
    run-tests.yml with the legacy suite driven through the uv installer,
    adds a uv version matrix (UV_VERSION pins the uv under test), and
    reruns the generate-scripts job through the uv installer. Every
    suite cell runs `make test-uv` only: there is no uv variant of the
    pytest step, and the pip matrix is not mirrored (the uv seam never
    spawns pip). The windows job has no cell: the dagger module runs
    Linux containers only. Run-step commands and env are parsed from
    the yaml so the cells fail drift if the workflow stops invoking
    test-uv or drops the installer pin.
    """
    wf = data["jobs"]
    cells = {}

    def uv_commands(job):
        steps = {step["name"]: step for step in job["steps"] if "name" in step}
        run = steps["Run tests (uv installer)"]["run"]
        return (tuple(run.split(" -- ")[-1].split()),)

    matrix = wf["setuptools"]["strategy"]["matrix"]
    for st in matrix["setuptools-version"]:
        cells[f"setuptools-{st}-uv"] = {
            "python": matrix["python-version"][0],
            "commands": uv_commands(wf["setuptools"]),
            "family": "uv",
            "setuptools": st,
            "installer": "uv",
        }

    matrix = wf["python"]["strategy"]["matrix"]
    for py in matrix["python-version"]:
        cells[f"python-{py}-uv"] = {
            "python": py,
            "commands": uv_commands(wf["python"]),
            "family": "uv",
            "setuptools": matrix["setuptools-version"][0],
            "installer": "uv",
        }

    # the uv version matrix: UV_VERSION pins the uv under test
    matrix = wf["uv"]["strategy"]["matrix"]
    steps = {step["name"]: step for step in wf["uv"]["steps"] if "name" in step}
    for uv in matrix["uv-version"]:
        assert steps["Run tests (uv installer)"]["env"]["UV_VERSION"] == "${{matrix.uv-version}}"
        cells[f"uv-{uv}"] = {
            "python": matrix["python-version"][0],
            "commands": uv_commands(wf["uv"]),
            "family": "uv",
            "setuptools": matrix["setuptools-version"][0],
            "installer": "uv",
            "uv": uv,
        }

    matrix = wf["mac"]["strategy"]["matrix"]
    cells["mac-uv"] = {
        "python": matrix["python-version"][0],
        "commands": uv_commands(wf["mac"]),
        "family": "uv",
        "setuptools": matrix["setuptools-version"][0],
        "installer": "uv",
    }

    # the uv variant of generate-scripts: the installer default rides
    # the run step's env, and the download-cache check drops away
    # (installer = uv does not populate the buildout download cache)
    scripts = wf["generate-scripts"]
    matrix = scripts["strategy"]["matrix"]
    steps = {step["name"]: step for step in scripts["steps"] if "name" in step}
    assert steps["Run buildout"]["env"]["buildout_testing_installer"] == "uv"
    bootstrap = steps["Setup buildout virtualenv"]["run"].split(" -- ")[-1].split()
    makefile = bootstrap[bootstrap.index("-f") + 1]
    for py in matrix["python-version"]:
        for pkg in matrix["package"]:
            cells[f"scripts-uv-{pkg}-py{py}"] = {
                "python": py,
                "commands": jobs._scripts_commands(makefile, check_downloads=False),
                "family": "scripts",
                "package": pkg,
                "installer": "uv",
            }

    return cells


def test_jobs_module_imports_nothing_from_dagger():
    # dagger/tests must be able to load jobs.py without the SDK installed
    tree = ast.parse(JOBS_PATH.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots = {node.module.split(".")[0]}
        else:
            continue
        assert "dagger" not in roots


def test_workflow_cells_match_job_table(workflow, uv_workflow):
    cells = _workflow_cells(workflow) | _uv_workflow_cells(uv_workflow)
    assert len(cells) == 82
    by_name = {job.name: job for job in jobs.JOBS}
    missing = set(cells) - set(by_name)
    assert not missing, f"workflow cells without a Job row: {sorted(missing)}"
    for name, expected in cells.items():
        job = by_name[name]
        assert job.python == expected["python"], name
        assert job.commands == expected["commands"], name
        assert job.family == expected["family"], name
        for pin in ("setuptools", "pip", "package", "installer", "uv"):
            if pin in expected:
                assert getattr(job, pin) == expected[pin], name
    extra = set(by_name) - set(cells)
    # scripts-head-* transcribes the setuptools-head makefile variants
    # (.github/workflows/Makefile-scripts-setuptools-head) that this
    # branch's workflow does not run; module-tests is the harness itself.
    unexpected = {name for name in extra if not name.startswith("scripts-head-")} - {"module-tests"}
    assert not unexpected, f"Job rows matching no workflow cell: {sorted(unexpected)}"
    assert sum(name.startswith("scripts-head-") for name in extra) == 10
    assert "module-tests" in extra


def test_dagger_matrix_matches_families(workflow):
    family = workflow["jobs"]["dagger"]["strategy"]["matrix"]["family"]
    assert family == list(jobs.FAMILIES) + ["module"]


def test_family_invariants():
    assert set(jobs.VALID_FAMILIES) == set(jobs.FAMILIES) | {"module"}
    for job in jobs.JOBS:
        assert job.family in jobs.VALID_FAMILIES
    assert set(jobs.FAMILY_MINUTES) == set(jobs.FAMILIES)
    counts = Counter(job.family for job in jobs.JOBS)
    assert counts == {
        "setuptools": 10,
        "python": 6,
        "pip": 14,
        "scripts": 34,
        "static": 4,
        "coverage": 3,
        "uv": 21,
        "module": 1,
    }
    names = [job.name for job in jobs.JOBS]
    assert len(names) == len(set(names)), "duplicate job names"
    assert len(jobs.JOBS) == 93


def test_select_jobs_pip():
    selected = jobs._select_jobs("pip")
    expected = [
        f"pip-{pip}-st-{st}"
        for pip in ("21.3.1", "22.3.1", "23.3.2", "24.3.1", "25.3", "26.1.2", "26.2.1")
        for st in ("65.7.0", "75.8.2")
    ]
    assert [job.name for job in selected] == expected


def test_select_jobs_all():
    assert jobs._select_jobs("") == list(jobs.JOBS)


def test_select_jobs_unknown_family():
    with pytest.raises(ValueError) as excinfo:
        jobs._select_jobs("bogus")
    message = str(excinfo.value)
    assert "bogus" in message
    for family in jobs.VALID_FAMILIES:
        assert family in message


def test_scripts_commands_shape():
    commands = jobs._scripts_commands(".github/workflows/Makefile-scripts")
    assert len(commands) == 4
    # the makefile argument threads through to the buildout bootstrap
    assert commands[0] == ("make", "-f", ".github/workflows/Makefile-scripts", "sandbox/bin/buildout")
    # the buildout config path references PYTHON_VERSION
    config_args = [arg for command in commands for arg in command if "scripts-" in arg]
    assert config_args
    assert all("${PYTHON_VERSION}" in arg for arg in config_args)


def test_scripts_commands_makefile_threads_through():
    commands = jobs._scripts_commands("Makefile-sentinel")
    assert "Makefile-sentinel" in commands[0]


def test_scripts_commands_uv_drops_downloads_check():
    # installer = uv does not populate the buildout download cache, so
    # the uv variant asserts on the eggs only
    commands = jobs._scripts_commands(".github/workflows/Makefile-scripts", check_downloads=False)
    assert len(commands) == 4
    assert commands[3] == ("sh", "-c", 'test -n "$(ls -A sandbox/eggs)"')
