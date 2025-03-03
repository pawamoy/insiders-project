from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, fields
from dataclasses import field as dataclass_field
from typing import TYPE_CHECKING, Any, overload
from typing import Annotated as An

from typing_extensions import Doc

from insiders._internal.defaults import DEFAULT_CONF_PATH
from insiders._internal.logger import _logger
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
        self.key: An[str, Doc("TOML key.")] = key
        self.name: An[str, Doc("Config variable name.")] = key.replace("-", "_").replace(".", "_")
        self.transform: An[str | None, Doc("Name of the method to call to transform the config value.")] = transform

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

    # ----------------------------------------------------------------------- #
    # Backlog fields.                                                         #
    # ----------------------------------------------------------------------- #
    backlog_namespaces: list[str] | Unset = config_field("backlog.namespaces")
    """GitHub namespaces to fetch issues from."""

    backlog_sort: list[Callable] | Unset = config_field("backlog.sort", transform="_eval_sort")
    """Sort strategies to apply to the backlog."""

    backlog_limit: int | Unset = config_field("backlog.limit")
    """Limit the number of displayed issues."""

    backlog_issue_labels: dict[str, str] | Unset = config_field("backlog.issue-labels")
    """Map of label names to their display value (emojis, typically)."""

    backlog_github_token_command: str | Unset = config_field("backlog.github-token-command")
    """Command to obtain a GitHub token for the backlog."""

    @property
    def backlog_github_token(self) -> str | Unset:
        """Get the GitHub token for backlog operations."""
        if isinstance(self.backlog_github_token_command, Unset):
            return self.backlog_github_token_command
        return subprocess.getoutput(self.backlog_github_token_command)  # noqa: S605

    backlog_polar_token_command: str | Unset = config_field("backlog.polar-token-command")
    """Command to obtain a Polar token for the backlog."""

    @property
    def backlog_polar_token(self) -> str | Unset:
        """Get the Polar token for backlog operations."""
        if isinstance(self.backlog_polar_token_command, Unset):
            return self.backlog_polar_token_command
        return subprocess.getoutput(self.backlog_polar_token_command)  # noqa: S605

    # ----------------------------------------------------------------------- #
    # Index fields.                                                           #
    # ----------------------------------------------------------------------- #
    index_url: str | Unset = config_field("index.url")
    """URL of the index server."""

    index_start_in_background: bool | Unset = config_field("index.start-in-background")
    """Whether to start the index server in the background."""

    index_distributions_directory: str | Unset = config_field("index.distributions-directory")
    """Directory to store generated Python project distributions."""

    index_sources_directory: str | Unset = config_field("index.sources-directory")
    """Directory to store project sources (cloned repositories)."""

    index_log_path: str | Unset = config_field("index.log-path")
    """Where to write the index server logs to."""

    # ----------------------------------------------------------------------- #
    # Project fields.                                                         #
    # ----------------------------------------------------------------------- #
    project_github_username: str | Unset = config_field("project.github-username")
    """GitHub username to use for operations."""

    project_namespace: str | Unset = config_field("project.namespace")
    """GitHub namespace to create public projects in."""

    project_insiders_namespace: str | Unset = config_field("project.insiders-namespace")
    """GitHub namespace to create insiders projects in."""

    project_directory: str | Unset = config_field("project.directory")
    """Directory in which to clone created public projects."""

    project_insiders_directory: str | Unset = config_field("project.insiders-directory")
    """Directory in which to clone created private projects."""

    project_register_on_pypi: bool | Unset = config_field("project.register-on-pypi")
    """Whether to register new projects on PyPI after creating them."""

    project_pypi_username: str | Unset = config_field("project.pypi-username")
    """PyPI username to use when registering projects on PyPI."""

    project_post_creation_command: str | list[str] | Unset = config_field("project.post-creation-command")
    """Command to run after creating a project."""

    project_copier_template: str | Unset = config_field("project.copier-template")
    """Copier template to generate new projects with."""

    project_copier_template_answers: dict[str, str] | Unset = config_field("project.copier-template-answers")
    """Copier template answers to use when generating a project."""

    # ----------------------------------------------------------------------- #
    # Sponsors fields.                                                        #
    # ----------------------------------------------------------------------- #
    sponsors_minimum_amount: int | Unset = config_field("sponsors.minimum-amount")
    """Minimum sponsorship amount to be considered an insider."""

    sponsors_github_sponsored_account: str | Unset = config_field("sponsors.github-sponsored-account")
    """GitHub account receiving sponsorships."""

    sponsors_github_token_command: str | Unset = config_field("sponsors.github-token-command")
    """Command to obtain a GitHub token."""

    @property
    def sponsors_github_token(self) -> str | Unset:
        """Get the GitHub token for sponsors operations."""
        if isinstance(self.sponsors_github_token_command, Unset):
            return self.sponsors_github_token_command
        return subprocess.getoutput(self.sponsors_github_token_command)  # noqa: S605

    sponsors_github_beneficiaries: dict[str, set[str]] | Unset = config_field("sponsors.github-beneficiaries")
    """Map of GitHub sponsors to their beneficiaries."""

    sponsors_polar_sponsored_account: str | Unset = config_field("sponsors.polar-sponsored-account")
    """Polar account receiving sponsorships."""

    sponsors_polar_token_command: str | Unset = config_field("sponsors.polar-token-command")
    """Command to obtain a Polar token for the sponsors."""

    @property
    def sponsors_polar_token(self) -> str | Unset:
        """Get the Polar token for sponsors operations."""
        if isinstance(self.sponsors_polar_token_command, Unset):
            return self.sponsors_polar_token_command
        return subprocess.getoutput(self.sponsors_polar_token_command)  # noqa: S605

    sponsors_polar_beneficiaries: dict[str, set[str]] | Unset = config_field("sponsors.polar-beneficiaries")
    """Map of Polar sponsors to their beneficiaries."""

    sponsors_insiders_team: str | Unset = config_field("sponsors.insiders-team")
    """GitHub team to add insiders to."""

    sponsors_include_users: set[str] | Unset = config_field("sponsors.include-users")
    """GitHub users to always include in the insiders team (even non-sponsors)."""

    sponsors_exclude_users: set[str] | Unset = config_field("sponsors.exclude-users")
    """GitHub users to never include in the insiders team (even sponsors)."""

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
        # Load data from the file.
        with open(path, "rb") as file:
            data = tomllib.load(file)

        # Check for unknown configuration keys.
        field_keys = [field.default.key for field in fields(cls)]  # type: ignore[union-attr]
        unknown_keys = []
        for top_level_key, top_level_value in data.items():
            for key in top_level_value.keys():  # noqa: SIM118
                final_key = f"{top_level_key}.{key}"
                if final_key not in field_keys:
                    unknown_keys.append(final_key)
        if unknown_keys:
            _logger.warning(f"Unknown configuration keys: {', '.join(unknown_keys)}")

        # Create a configuration instance.
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
