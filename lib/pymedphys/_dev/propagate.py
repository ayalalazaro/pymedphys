# Copyright (C) 2020 Simon Biggs

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import re
import subprocess
import textwrap
from typing import List, Optional

from pymedphys._imports import tomlkit

from .paths import DEPENDENCY_EXTRA_PATH, LIBRARY_PATH, REPO_ROOT

PYPROJECT_TOML_PATH = REPO_ROOT.joinpath("pyproject.toml")

POETRY_LOCK_PATH = REPO_ROOT.joinpath("poetry.lock")
PYPROJECT_TOML_HASH_PATH = REPO_ROOT.joinpath("pyproject.hash")

VERSION_PATH = LIBRARY_PATH.joinpath("_version.py")

REQUIREMENTS_CONFIG = (
    # Extras | Filename | Include PyMedPhys | Make it an editable dev install
    (["user"], "requirements.txt", True, False),
    # (["all"], "requirements-all.txt", True, True),
    # (["user", "tests"], "requirements-deploy.txt", False, None),
    # (["icom"], "requirements-icom.txt", False, None),
    # (["cli"], "requirements-cli.txt", False, None),
    # (["tests"], "requirements-tests.txt", False, None),
    (["docs"], "requirements-docs.txt", True, True),
)

AUTOGEN_MESSAGE = [
    "# DO NOT EDIT THIS FILE!",
    "# This file has been autogenerated by `poetry run pymedphys dev propagate`",
]


def propagate_all(args):
    if args.update:
        subprocess.check_call("poetry update", shell=True)

    propagate_version()
    propagate_extras()
    propagate_lock_requirements_and_hash()


def propagate_lock_requirements_and_hash():
    """Propagate poetry.lock, requirements.txt, and pyproject.hash

    Order here is important. Lock file propagation from pyproject.toml
    is needed to create an up to date requirements. Poetry.lock file
    creation is non-deterministic via OS, so the hash propagation is
    undergone last to verify that this step has been run to its
    completion for the given pyproject.toml file.

    """

    _update_poetry_lock()
    _propagate_requirements()
    _propagate_pyproject_hash()


def _update_poetry_lock():
    subprocess.check_call("poetry lock --no-update", shell=True)


def read_pyproject():
    with open(PYPROJECT_TOML_PATH) as f:
        pyproject_contents = tomlkit.loads(f.read())

    return pyproject_contents


def get_version_string():
    pyproject_contents = read_pyproject()
    version_string = pyproject_contents["tool"]["poetry"]["version"]

    return version_string


def propagate_version():
    version_string = get_version_string()
    version_list = re.split(r"[-\.]", version_string)

    for i, item in enumerate(version_list):
        try:
            version_list[i] = int(item)
        except ValueError:
            pass

    version_contents = textwrap.dedent(
        f"""\
        {AUTOGEN_MESSAGE[0]}
        {AUTOGEN_MESSAGE[1]}

        version_info = {version_list}
        __version__ = "{version_string}"
        """
    )

    with open(VERSION_PATH, "w") as f:
        f.write(version_contents)

    subprocess.run(["ruff", "format", str(VERSION_PATH)])


def _propagate_requirements():
    """Propagates requirement files for use without Poetry."""
    for extras, filename, include_pymedphys, editable in REQUIREMENTS_CONFIG:
        _make_requirements_txt(
            extras=extras,
            filename=filename,
            include_pymedphys=include_pymedphys,
            editable=editable,
        )


def _make_requirements_txt(
    extras: List[str],
    filename: str,
    include_pymedphys: bool,
    editable: Optional[bool] = None,
):
    """Create a requirements.txt file with poetry pins.

    Parameters
    ----------
    extras : List[str]
        A list of pip extras to include within the requirements file.
    filename : str
        The filename of the requirements file. Will be created in the
        repo root.
    include_pymedphys : bool
        Whether or not the requirements file should include an
        installation of the git repo.
    editable : bool
        Whether or not the pymedphys install should be 'editable'.
    """
    if not include_pymedphys and editable is not None:
        raise ValueError("Setting editable only works if using `include_pymedphys`")

    if include_pymedphys and editable is None:
        raise ValueError("When using `include_pymedphys` need to also set `editable`")

    filepath = REPO_ROOT.joinpath(filename)

    poetry_environment_flags = " ".join([f"-E {item}" for item in extras])

    # TODO: Once the hashes pinning issue in poetry is fixed, remove the
    # --without-hashes. See <https://github.com/python-poetry/poetry/issues/1584>
    # for more details.
    subprocess.check_call(
        (
            "poetry export --without-hashes "
            + poetry_environment_flags
            + " -f requirements.txt --output "
            + filename
        ),
        shell=True,
        cwd=REPO_ROOT,
    )

    if include_pymedphys:
        pymedphys_install_command = f".[{','.join(extras)}]\n"
        if editable:
            pymedphys_install_command = f"-e {pymedphys_install_command}"

        with open(filepath, "a") as f:
            f.write(pymedphys_install_command)


def propagate_extras():
    pyproject_contents = read_pyproject()

    deps = pyproject_contents["tool"]["poetry"]["dependencies"]

    extras = {}

    for key in deps:
        value = deps[key]
        comment = value.trivia.comment

        if comment.startswith("# groups"):
            split = comment.split("=")
            assert len(split) == 2
            groups = json.loads(split[-1])

            for group in groups:
                try:
                    extras[group].append(key)
                except KeyError:
                    extras[group] = [key]

    for group, deps in extras.items():
        extras[group] = sorted(deps)

    extras = tomlkit.item(
        extras, _parent=pyproject_contents["tool"]["poetry"], _sort_keys=True
    )

    for _, deps in extras.items():
        if len(deps.as_string()) > 88:
            deps.multiline(True)

    if pyproject_contents["tool"]["poetry"]["extras"] != extras:
        pyproject_contents["tool"]["poetry"]["extras"] = extras

        with open(PYPROJECT_TOML_PATH, "w") as f:
            f.write(tomlkit.dumps(pyproject_contents))

    with open(DEPENDENCY_EXTRA_PATH, "w") as f:
        f.write(tomlkit.dumps(extras))


def _propagate_pyproject_hash():
    """Store the pyproject content hash metadata for verification of propagation."""

    with open(POETRY_LOCK_PATH) as f:
        poetry_lock_contents = tomlkit.loads(f.read())

    content_hash = poetry_lock_contents["metadata"]["content-hash"]

    with open(PYPROJECT_TOML_HASH_PATH, "w") as f:
        f.write(f"{content_hash}\n")
