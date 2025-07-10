import tomllib
from pathlib import Path
from typing import NotRequired, ReadOnly, Required, cast

from typing_extensions import TypedDict

PYPROJECT_PATH = Path(__file__).parent.parent / "pyproject.toml"


class ProjectInfo(TypedDict):
    """[project]セクションの型定義"""

    name: ReadOnly[Required[str]]
    version: ReadOnly[NotRequired[str]]
    description: ReadOnly[NotRequired[str]]
    readme: ReadOnly[NotRequired[str | dict[str, str]]]
    requires_python: ReadOnly[NotRequired[str]]
    license: ReadOnly[NotRequired[str | dict[str, str]]]
    authors: ReadOnly[NotRequired[list[dict[str, str]]]]
    maintainers: ReadOnly[NotRequired[list[dict[str, str]]]]
    keywords: ReadOnly[NotRequired[list[str]]]
    classifiers: ReadOnly[NotRequired[list[str]]]
    dependencies: ReadOnly[NotRequired[list[str]]]
    dynamic: ReadOnly[NotRequired[list[str]]]


class ProjectUrls(TypedDict):
    """[project.urls]セクションの型定義"""

    homepage: ReadOnly[NotRequired[str]]
    documentation: ReadOnly[NotRequired[str]]
    repository: ReadOnly[NotRequired[str]]
    changelog: ReadOnly[NotRequired[str]]
    bug_tracker: ReadOnly[NotRequired[str]]


class PyProjectToml(TypedDict, total=False):
    """pyproject.toml全体の型定義

    https://peps.python.org/pep-0621/
    """

    project: ReadOnly[Required[ProjectInfo]]
    urls: ReadOnly[NotRequired[ProjectUrls]]


def get_package_metadata() -> PyProjectToml:
    """Return the package metadata."""
    with PYPROJECT_PATH.open("rb") as f:
        return cast(PyProjectToml, tomllib.load(f))


METADATA = get_package_metadata()
NAME = METADATA["project"]["name"]
VERSION = METADATA["project"].get("version", "unknown")
