from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from insiders._internal.defaults import DEFAULT_CONF_PATH

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

# YORE: EOL 3.10: Replace block with line 2.
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class Unset:
    """A sentinel value for unset configuration options."""

    def __repr__(self) -> str:
        return "<unset>"


@dataclass(kw_only=True)
class Config:
    """Configuration for the insiders project."""

    unset: ClassVar[Unset] = Unset()

    sponsors_minimum_amount: int | Unset = unset

    backlog_namespaces: list[str] | Unset = unset
    backlog_sort: list[Callable] | Unset = unset

    github_token_command: str | Unset = unset
    github_organization_members: dict[str, set[str]] | Unset = unset
    github_project_namespace: str | Unset = unset
    github_insiders_project_namespace: str | Unset = unset
    github_username: str | Unset = unset
    github_insiders_team: str | Unset = unset
    github_sponsored_account: str | Unset = unset
    github_privileged_users: set[str] | Unset = unset

    project_copier_template: str | Unset = unset
    project_register_on_pypi: bool | Unset = unset
    project_directory: str | Unset = unset

    pypi_username: str | Unset = unset

    index_distribution_directory: str | Unset = unset
    index_source_directory: str | Unset = unset
    index_url: str | Unset = unset
    index_start_in_background: bool | Unset = unset
    index_log_level: str | Unset = unset
    index_log_path: str | Unset = unset

    polar_token_command: str | Unset = unset
    polar_sponsored_account: str | Unset = unset

    @property
    def github_token(self) -> str | Unset:
        """Get the GitHub token."""
        if isinstance(self.github_token_command, Unset):
            return self.unset
        return subprocess.getoutput(self.github_token_command)  # noqa: S605

    @property
    def polar_token(self) -> str | Unset:
        """Get the Polar token."""
        if isinstance(self.polar_token_command, Unset):
            return self.unset
        return subprocess.getoutput(self.polar_token_command)  # noqa: S605

    @classmethod
    def _get(cls, data: dict, *keys: str) -> Any:
        """Get a value from a nested dictionary."""
        for key in keys:
            if key not in data:
                return cls.unset
            data = data[key]
        return data

    @classmethod
    def from_file(cls, path: str | Path) -> Config:
        """Load configuration from a file."""
        with open(path, "rb") as file:
            data = tomllib.load(file)
        return cls(
            sponsors_minimum_amount=cls._get(data, "sponsors", "minimum-amount"),
            backlog_namespaces=cls._get(data, "backlog", "namespaces"),
            backlog_sort=cls._get(data, "backlog", "sort"),
            github_token_command=cls._get(data, "github", "token-command"),
            github_organization_members=cls._get(data, "github", "organization-members"),
            github_project_namespace=cls._get(data, "github", "project-namespace"),
            github_insiders_project_namespace=cls._get(data, "github", "insiders-project-namespace"),
            github_username=cls._get(data, "github", "username"),
            github_insiders_team=cls._get(data, "github", "insiders-team"),
            github_sponsored_account=cls._get(data, "github", "sponsored-account"),
            github_privileged_users=cls._get(data, "github", "privileged-users"),
            project_copier_template=cls._get(data, "project", "copier-template"),
            project_register_on_pypi=cls._get(data, "project", "register-on-pypi"),
            project_directory=cls._get(data, "project", "directory"),
            pypi_username=cls._get(data, "pypi", "username"),
            index_distribution_directory=cls._get(data, "index", "distribution-directory"),
            index_source_directory=cls._get(data, "index", "source-directory"),
            index_url=cls._get(data, "index", "url"),
            index_start_in_background=cls._get(data, "index", "start-in-background"),
            index_log_level=cls._get(data, "index", "log-level"),
            index_log_path=cls._get(data, "index", "log-path"),
            polar_token_command=cls._get(data, "polar", "token-command"),
            polar_sponsored_account=cls._get(data, "polar", "sponsored-account"),
        )

    @classmethod
    def from_default_location(cls) -> Config:
        """Load configuration from the default location."""
        if DEFAULT_CONF_PATH.exists():
            return cls.from_file(DEFAULT_CONF_PATH)
        return cls()
