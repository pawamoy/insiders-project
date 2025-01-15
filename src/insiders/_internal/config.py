from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, fields
from dataclasses import field as dataclass_field
from typing import TYPE_CHECKING, Any, overload

from insiders._internal.defaults import DEFAULT_CONF_PATH
from insiders._internal.models import Backlog  # noqa: F401

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

    def __init__(self, key: str, transform: str | None = None) -> None:
        self.key = key
        self.name = key.replace("-", "_").replace(".", "_")
        self.transform = transform

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"<Unset({self.name!r})>"

    def __str__(self) -> str:
        # The string representation is used in the CLI, to show the default values.
        return f"`{self.key}` config-value"


def config_field(key: str, transform: str | None = None) -> Unset:
    """Get a dataclass field with a TOML key."""
    return dataclass_field(default=Unset(key, transform=transform))


@dataclass(kw_only=True)
class Config:
    """Configuration for the insiders project."""

    # Sponsors fields.
    sponsors_minimum_amount: int | Unset = config_field("sponsors.minimum-amount")

    # Backlog fields.
    backlog_namespaces: list[str] | Unset = config_field("backlog.namespaces")
    backlog_sort: list[Callable] | Unset = config_field("backlog.sort", transform="_eval_sort")
    backlog_limit: int | Unset = config_field("backlog.limit")
    backlog_issue_labels: dict[str, str] | Unset = config_field("backlog.issue-labels")

    # GitHub fields.
    github_token_command: str | Unset = config_field("github.token-command")
    github_organization_members: dict[str, set[str]] | Unset = config_field("github.organization-members")
    github_project_namespace: str | Unset = config_field("github.project-namespace")
    github_insiders_project_namespace: str | Unset = config_field("github.insiders-project-namespace")
    github_username: str | Unset = config_field("github.username")
    github_insiders_team: str | Unset = config_field("github.insiders-team")
    github_sponsored_account: str | Unset = config_field("github.sponsored-account")
    github_include_users: set[str] | Unset = config_field("github.include-users")
    github_exclude_users: set[str] | Unset = config_field("github.exclude-users")

    # Project fields.
    project_copier_template: str | Unset = config_field("project.copier-template")
    project_register_on_pypi: bool | Unset = config_field("project.register-on-pypi")
    project_directory: str | Unset = config_field("project.directory")

    # PyPI fields.
    pypi_username: str | Unset = config_field("pypi.username")

    # Index fields.
    index_distributions_directory: str | Unset = config_field("index.distributions-directory")
    index_sources_directory: str | Unset = config_field("index.sources-directory")
    index_url: str | Unset = config_field("index.url")
    index_start_in_background: bool | Unset = config_field("index.start-in-background")
    index_log_path: str | Unset = config_field("index.log-path")

    # Polar fields.
    polar_token_command: str | Unset = config_field("polar.token-command")
    polar_sponsored_account: str | Unset = config_field("polar.sponsored-account")

    @property
    def github_token(self) -> str | Unset:
        """Get the GitHub token."""
        if isinstance(self.github_token_command, Unset):
            return self.github_token_command
        return subprocess.getoutput(self.github_token_command)  # noqa: S605

    @property
    def polar_token(self) -> str | Unset:
        """Get the Polar token."""
        if isinstance(self.polar_token_command, Unset):
            return self.polar_token_command
        return subprocess.getoutput(self.polar_token_command)  # noqa: S605

    @overload
    @staticmethod
    def _eval_sort(strats: Unset) -> Unset: ...

    @overload
    @staticmethod
    def _eval_sort(strats: list[str]) -> list[Callable]: ...

    @staticmethod
    def _eval_sort(strats: list[str] | Unset) -> list[Callable] | Unset:
        if isinstance(strats, Unset):
            return strats
        callables = []
        for strat in strats:
            if not strat.endswith(")"):
                strat += "()"  # noqa: PLW2901
            # TODO: Parse AST instead of using eval.
            callables.append(eval(f"Backlog.SortStrategy.{strat}"))  # noqa: S307
        return callables

    @classmethod
    def _get(cls, data: dict, *keys: str, default: Unset, transform: Callable[[Any], Any] | None = None) -> Any:
        """Get a value from a nested dictionary."""
        for key in keys:
            if key not in data:
                return default
            data = data[key]
        if transform:
            return transform(data)
        return data

    @classmethod
    def from_file(cls, path: str | Path) -> Config:
        """Load configuration from a file."""
        with open(path, "rb") as file:
            data = tomllib.load(file)
        return cls(
            **{
                field.name: cls._get(
                    data,
                    *field.default.key.split("."),  # type: ignore[union-attr]
                    default=field.default,  # type: ignore[arg-type]
                    transform=getattr(cls, field.default.transform or "", None),  # type: ignore[union-attr]
                )
                for field in fields(cls)
            },
        )

    @classmethod
    def from_default_location(cls) -> Config:
        """Load configuration from the default location."""
        if DEFAULT_CONF_PATH.exists():
            return cls.from_file(DEFAULT_CONF_PATH)
        return cls()
