"""Module that contains the command line application."""

# Why does this file exist, and why not put this in `__main__`?
#
# You might be tempted to import things from `__main__` later,
# but that will cause problems: the code will get executed twice:
#
# - When you run `python -m insiders` python will execute
#   `__main__.py` as a script. That means there won't be any
#   `insiders.__main__` in `sys.modules`.
# - When you import `__main__` it will get executed again (as a module) because
#   there's no `insiders.__main__` in `sys.modules`.

from __future__ import annotations

import json
import shlex
import sys
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import wraps
from inspect import cleandoc
from pathlib import Path  # noqa: TC003
from typing import Annotated as An
from typing import Any, Callable, ClassVar, Literal

import cappa
from rich.console import Console
from typing_extensions import Doc

from insiders._internal import debug, defaults
from insiders._internal.clients import pypi
from insiders._internal.clients.github import GitHub
from insiders._internal.clients.index import Index
from insiders._internal.clients.polar import Polar
from insiders._internal.config import Config, Unset
from insiders._internal.logger import configure_logging

# TODO: Use PEP 727 everywhere.
# TODO: Re-organize all this.
from insiders._internal.ops.backlog import get_backlog, print_backlog
from insiders._internal.ops.projects import new_public_and_insiders_github_projects

_GROUP_ARGUMENTS = (10, "Arguments")
_GROUP_OPTIONS = (20, "Options")
_GROUP_GLOBAL_OPTIONS = (30, "Global options")
_GROUP_SUBCOMMANDS = (40, "Subcommands")


@dataclass(frozen=True)
class FromConfig(cappa.ValueFrom):
    def __init__(self, field: Unset | property, /) -> None:
        attr_name = field.fget.__name__ if isinstance(field, property) else field.name  # type: ignore[union-attr]
        super().__init__(self._from_config, attr_name=attr_name)

    @staticmethod
    def _from_config(attr_name: str) -> Any:
        config = CommandMain._load_config()
        value = getattr(config, attr_name)
        return cappa.Empty if isinstance(value, Unset) else value


# ============================================================================ #
# Projects                                                                     #
# ============================================================================ #
@cappa.command(name="project", help="Manage projects (GitHub and local copies).")
@dataclass(kw_only=True)
class CommandProject:
    """Command to manage projects on GitHub and locally."""

    subcommand: An[
        CommandProjectCreate | CommandProjectCheck,
        cappa.Subcommand(group=_GROUP_SUBCOMMANDS),
        Doc("The selected subcommand."),
    ]


@cappa.command(
    name="create",
    help="Create public/insiders repositories.",
    description=cleandoc(
        """
        This command will do several things:

        - Create public and insiders repositories on GitHub
            (using the provided namespace, username, repository name, description, etc.).
        - Clone these two repositories locally (using the provided repository paths).
        - Optionally initialize the public repository by generating initial contents
            using the specified [Copier](https://copier.readthedocs.io/en/stable/) template and answers.
        - Optionally run a post creation command into the public repository.
        - Pull the public contents into the insiders clone (by declaring an `upstream` remote).

        *Example 1 - Project in user's namespace*

        The insiders namespace, insiders repository name and username are inferred
        from the namespace and repository name.

        ```bash
        insiders create \\
            -n pawamoy \\
            -r mkdocs-ultimate \\
            -d "The ultimate plugin for MkDocs (??)" \\
            -o ~/data/dev \\
            -O ~/data/dev/insiders \\
            -t gh:pawamoy/copier-uv
        ```

        *Example 2 - Project in another namespace:*

        The insiders namespace, insiders repository name and username are different,
        so must be provided explicitly:

        ```bash
        insiders create \\
            -n mkdocstrings \\
            -r rust \\
            -d "A Rust handler for mkdocstrings" \\
            -o ~/data/dev \\
            -O ~/data/dev/insiders \\
            -N pawamoy-insiders \\
            -R mkdocstrings-rust \\
            -u pawamoy \\
            -t gh:mkdocstrings/handler-template
        ```
        """,
    ),
)
@dataclass(kw_only=True)
class CommandProjectCreate:
    """Command to create public/insiders repositories."""

    repository: An[
        str,
        cappa.Arg(short="-r", long=True, group=_GROUP_OPTIONS),
        Doc("""Name of the public repository."""),
    ]

    description: An[
        str,
        cappa.Arg(short="-d", long=True, group=_GROUP_OPTIONS),
        Doc("""Shared description."""),
    ]

    namespace: An[
        str,
        cappa.Arg(
            short="-n",
            long=True,
            default=FromConfig(Config.github_project_namespace),
            show_default=f"{Config.github_project_namespace}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Namespace of the public repository."""),
    ]

    project_directory: An[
        Path,
        cappa.Arg(
            short="-o",
            long=True,
            default=FromConfig(Config.project_directory),
            show_default=f"{Config.project_directory}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Directory in which to clone the public repository."""),
    ]

    insiders_repository: An[
        str | None,
        cappa.Arg(short="-R", long=True, show_default="public name", group=_GROUP_OPTIONS),
        Doc("""Name of the insiders repository."""),
    ] = None

    insiders_namespace: An[
        str | None,
        cappa.Arg(
            short="-N",
            long=True,
            default=FromConfig(Config.github_insiders_project_namespace),
            show_default=f"{Config.github_insiders_project_namespace} or public namespace",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Namespace of the insiders repository."""),
    ] = None

    insiders_project_directory: An[  # type: ignore[misc]
        Path,
        cappa.Arg(
            short="-O",
            long=True,
            default=FromConfig(Config.project_insiders_directory),
            show_default=f"{Config.project_insiders_directory}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Directory in which to clone the insiders repository."""),
    ]

    github_username: An[
        str | None,
        cappa.Arg(
            short="-u",
            long=True,
            default=FromConfig(Config.github_username),
            show_default=f"{Config.github_username} or public namespace",
            group=_GROUP_OPTIONS,
        ),
        Doc("""GitHub username."""),
    ] = None

    copier_template: An[
        str | None,
        cappa.Arg(
            short="-t",
            long=True,
            default=FromConfig(Config.project_copier_template),
            show_default=f"{Config.project_copier_template}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Copier template to generate new projects with."""),
    ] = None

    @staticmethod
    def _parse_dict(arg: str) -> dict[str, str]:
        return dict(pair.split("=", 1) for pair in arg.split(","))

    copier_template_answers: An[
        dict[str, str] | None,
        cappa.Arg(
            short="-a",
            long=True,
            parse=_parse_dict,
            default=FromConfig(Config.project_copier_template_answers),
            show_default=f"{Config.project_copier_template_answers}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Copier template answers to use when generating a project."""),
    ] = None

    post_creation_command: An[
        list[str] | None,
        cappa.Arg(
            short="-x",
            long=True,
            num_args=1,
            parse=shlex.split,
            default=FromConfig(Config.project_post_creation_command),
            show_default=f"{Config.project_post_creation_command}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Command to run after creating the public repository."""),
    ] = None

    register_on_pypi: An[
        bool,
        cappa.Arg(
            short="-i",
            long=True,
            default=FromConfig(Config.project_register_on_pypi),
            show_default=f"{Config.project_register_on_pypi}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Whether to register the project on PyPI after creating it."""),
    ] = False

    pypi_username: An[
        str | None,
        cappa.Arg(
            short="-y",
            long=True,
            default=FromConfig(Config.pypi_username),
            show_default=f"{Config.pypi_username}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""PyPI username to register the project with."""),
    ] = None

    def __call__(self) -> int:
        new_public_and_insiders_github_projects(
            public_namespace=self.namespace,
            public_name=self.repository,
            description=self.description,
            # We use the Insiders name here as it will generally be more independant of the namespace
            # (for example `mkdocstrings-python` instead of just `python`).
            public_repo_path=self.project_directory / (self.insiders_repository or self.repository),
            insiders_namespace=self.insiders_namespace,
            insiders_name=self.insiders_repository,
            insiders_repo_path=self.insiders_project_directory / (self.insiders_repository or self.repository),
            github_username=self.github_username,
            copier_template=self.copier_template,
            copier_template_answers=self.copier_template_answers,
            post_creation_command=self.post_creation_command,
        )
        if self.register_on_pypi:
            if not self.pypi_username:
                raise cappa.Exit("PyPI username must be provided to register the project on PyPI.", code=1)
            pypi.reserve_pypi(
                username=self.pypi_username,
                name=self.repository,
                description=self.description,
            )
        return 0


@cappa.command(
    name="check",
    help="Check public/insiders repositories.",
    description=cleandoc(
        """
        TODO. Check that everything is consistent.
        """,
    ),
)
@dataclass(kw_only=True)
class CommandProjectCheck:
    """Command to check GitHub projects."""

    def __call__(self) -> int:
        raise cappa.Exit("Not implemented yet.", code=1)


# ============================================================================ #
# PyPI                                                                         #
# ============================================================================ #
@cappa.command(name="pypi", help="Manage PyPI-related things.")
@dataclass(kw_only=True)
class CommandPyPI:
    """Command to manage PyPI-related things."""

    subcommand: An[
        CommandPyPIRegister,
        cappa.Subcommand(group=_GROUP_SUBCOMMANDS),
        Doc("The selected subcommand."),
    ]


@cappa.command(
    name="register",
    help="Register a name on PyPI.",
    description=cleandoc(
        """
        This will create a temporary project on your filesystem,
        then build both source and wheel distributions for it,
        and upload them to PyPI using Twine.

        After that, you will see an initial version 0.0.0
        of your project on PyPI.

        *Example*

        ```bash
        insiders pypi register -u pawamoy -n my-new-project -d "My new project!"
        ```

        Credentials must be configured in `~/.pypirc` to allow Twine to push to PyPI.
        For example, if you use [PyPI API tokens](https://pypi.org/help/#apitoken),
        add the token to your keyring:

        ```bash
        pipx install keyring
        keyring set https://upload.pypi.org/legacy/ __token__
        # __token__ is a literal string, do not replace it with your token.
        # The command will prompt you to paste your token.
        ```

        And configure `~/.pypirc`:

        ```ini
        [distutils]
        index-servers =
            pypi

        [pypi]
        username: __token__
        ```
        """,
    ),
)
@dataclass(kw_only=True)
class CommandPyPIRegister:
    """Command to register a project name on PyPI."""

    username: An[
        str,
        cappa.Arg(
            short="-u",
            long=True,
            default=FromConfig(Config.pypi_username),
            show_default=f"{Config.pypi_username}",
            group=_GROUP_OPTIONS,
        ),
        Doc("Username on PyPI (your account)."),
    ]

    name: An[
        str,
        cappa.Arg(short="-n", long=True, group=_GROUP_OPTIONS),
        Doc("Name to register."),
    ]

    description: An[
        str,
        cappa.Arg(short="-d", long=True, group=_GROUP_OPTIONS),
        Doc("Description of the project on PyPI."),
    ]

    def __call__(self) -> Any:
        pypi.reserve_pypi(self.username, self.name, self.description)
        return 0


# ============================================================================ #
# Index                                                                        #
# ============================================================================ #
@cappa.command(name="index", help="Manage the local index.")
@dataclass(kw_only=True)
class CommandIndex:
    """Command to manage the local index."""

    subcommand: An[
        CommandIndexList
        | CommandIndexAdd
        | CommandIndexRemove
        | CommandIndexUpdate
        | CommandIndexStart
        | CommandIndexStatus
        | CommandIndexStop
        | CommandIndexLogs,
        cappa.Subcommand(group=_GROUP_SUBCOMMANDS),
        Doc("The selected subcommand."),
    ]


@cappa.command(
    name="list",
    help="List insiders repositories.",
    description="List the watched repositories.",
)
@dataclass(kw_only=True)
class CommandIndexList:
    """Command to list the watched repositories."""

    sources_directory: An[
        Path,
        cappa.Arg(
            short="-s",
            long=True,
            default=FromConfig(Config.index_sources_directory),
            show_default=f"{Config.index_sources_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the sources are stored."),
    ] = defaults.DEFAULT_REPO_DIR

    distributions_directory: An[
        Path,
        cappa.Arg(
            short="-d",
            long=True,
            default=FromConfig(Config.index_distributions_directory),
            show_default=f"{Config.index_distributions_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the distributions are stored."),
    ] = defaults.DEFAULT_DIST_DIR

    dists: An[
        bool,
        cappa.Arg(short="-i", long=True, show_default="True", group=_GROUP_OPTIONS),
        Doc("List distributions."),
    ] = False

    projects: An[
        bool,
        cappa.Arg(short="-p", long=True, show_default="True", group=_GROUP_OPTIONS),
        Doc("List projects."),
    ] = False

    def __call__(self) -> int:
        index = Index(git_dir=self.sources_directory, dist_dir=self.distributions_directory)
        if self.dists is self.projects:
            print("Distributions:")
            for dist in sorted(index.list_distributions()):
                print(dist)
            print("\nProjects:")
            for project in sorted(index.list_projects()):
                print(project)
        elif self.dists:
            for dist in sorted(index.list_distributions()):
                print(dist)
        elif self.projects:
            for project in sorted(index.list_projects()):
                print(project)
        return 0


@cappa.command(
    name="add",
    help="Add insiders repositories.",
    description="Add a repository to the watched repositories.",
)
@dataclass(kw_only=True)
class CommandIndexAdd:
    """Command to add a repository to the watched repositories."""

    repositories: An[
        list[str],
        cappa.Arg(group=_GROUP_ARGUMENTS),
        Doc("List of repositories (GitHub namespace/project or Git URL git@host:repo)."),
    ]

    sources_directory: An[
        Path,
        cappa.Arg(
            short="-s",
            long=True,
            default=FromConfig(Config.index_sources_directory),
            show_default=f"{Config.index_sources_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the sources are stored."),
    ] = defaults.DEFAULT_REPO_DIR

    distributions_directory: An[
        Path,
        cappa.Arg(
            short="-d",
            long=True,
            default=FromConfig(Config.index_distributions_directory),
            show_default=f"{Config.index_distributions_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the distributions are stored."),
    ] = defaults.DEFAULT_DIST_DIR

    url: An[
        str,
        cappa.Arg(
            short="-u",
            long=True,
            default=FromConfig(Config.index_url),
            show_default=f"{Config.index_url} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("URL of the index to upload packages to."),
    ] = defaults.DEFAULT_INDEX_URL

    def __call__(self) -> int:
        index = Index(url=self.url, git_dir=self.sources_directory, dist_dir=self.distributions_directory)
        for project in self.repositories:
            index.add(project if project.startswith("git@") else f"git@github.com:{project}")
        return 0


@cappa.command(
    name="remove",
    help="Remove insiders repositories.",
    description="Remove a repository from the watched repositories.",
)
@dataclass(kw_only=True)
class CommandIndexRemove:
    """Command to remove a repository and its distributions (if served locally)."""

    repositories: An[
        list[str],
        cappa.Arg(group=_GROUP_ARGUMENTS),
        Doc("List of repository names."),
    ]

    sources_directory: An[
        Path,
        cappa.Arg(
            short="-s",
            long=True,
            default=FromConfig(Config.index_sources_directory),
            show_default=f"{Config.index_sources_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the sources are stored."),
    ] = defaults.DEFAULT_REPO_DIR

    distributions_directory: An[
        Path,
        cappa.Arg(
            short="-d",
            long=True,
            default=FromConfig(Config.index_distributions_directory),
            show_default=f"{Config.index_distributions_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the distributions are stored."),
    ] = defaults.DEFAULT_DIST_DIR

    def __call__(self) -> int:
        index = Index(git_dir=self.sources_directory, dist_dir=self.distributions_directory)
        for repo in self.repositories:
            index.remove(repo)
        return 0


@cappa.command(
    name="update",
    help="Update insiders packages.",
    description="Update watched projects.",
)
@dataclass(kw_only=True)
class CommandIndexUpdate:
    """Command to update watched projects."""

    repositories: An[
        list[str],
        cappa.Arg(group=_GROUP_ARGUMENTS),
        Doc("List of repository names."),
    ] = field(default_factory=list)

    sources_directory: An[
        Path,
        cappa.Arg(
            short="-s",
            long=True,
            default=FromConfig(Config.index_sources_directory),
            show_default=f"{Config.index_sources_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the sources are stored."),
    ] = defaults.DEFAULT_REPO_DIR

    distributions_directory: An[
        Path,
        cappa.Arg(
            short="-d",
            long=True,
            default=FromConfig(Config.index_distributions_directory),
            show_default=f"{Config.index_distributions_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the distributions are stored."),
    ] = defaults.DEFAULT_DIST_DIR

    url: An[
        str,
        cappa.Arg(
            short="-u",
            long=True,
            default=FromConfig(Config.index_url),
            show_default=f"{Config.index_url} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("URL of the index to upload packages to."),
    ] = defaults.DEFAULT_INDEX_URL

    def __call__(self) -> int:
        index = Index(url=self.url, git_dir=self.sources_directory, dist_dir=self.distributions_directory)
        index.update(self.repositories)
        return 0


@cappa.command(
    name="start",
    help="Start the server.",
    description="Start the server in the background.",
)
@dataclass(kw_only=True)
class CommandIndexStart:
    """Command to start the server."""

    sources_directory: An[
        Path,
        cappa.Arg(
            short="-s",
            long=True,
            default=FromConfig(Config.index_sources_directory),
            show_default=f"{Config.index_sources_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the sources are stored."),
    ] = defaults.DEFAULT_REPO_DIR

    distributions_directory: An[
        Path,
        cappa.Arg(
            short="-d",
            long=True,
            default=FromConfig(Config.index_distributions_directory),
            show_default=f"{Config.index_distributions_directory} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Directory where the distributions are stored."),
    ] = defaults.DEFAULT_DIST_DIR

    url: An[
        str,
        cappa.Arg(
            short="-u",
            long=True,
            default=FromConfig(Config.index_url),
            show_default=f"{Config.index_url} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("URL to serve the index at."),
    ] = defaults.DEFAULT_INDEX_URL

    background: An[
        bool,
        cappa.Arg(
            short="-b",
            long=True,
            default=FromConfig(Config.index_start_in_background),
            show_default=f"{Config.index_start_in_background} or {{default}}",
            group=_GROUP_OPTIONS,
        ),
        Doc("Run the server in the background."),
    ] = False

    log_path: An[
        str | None,
        cappa.Arg(
            short="-l",
            long=True,
            default=FromConfig(Config.index_log_path),
            show_default=f"{Config.index_log_path} or standard error",
            group=_GROUP_OPTIONS,
        ),
        Doc("Where to write index server logs."),
    ] = None

    def __call__(self) -> int:
        index = Index(url=self.url, git_dir=self.sources_directory, dist_dir=self.distributions_directory)
        index.start(background=self.background, log_path=self.log_path)
        return 0


@cappa.command(
    name="status",
    help="Show the server status.",
    description="Show the server status.",
)
@dataclass(kw_only=True)
class CommandIndexStatus:
    """Command to show the server status."""

    def __call__(self) -> int:
        proc_data = Index().status()
        if proc_data:
            print("Running:")
            print(json.dumps(proc_data, indent=2, sort_keys=True))
        else:
            print("Not running")
        return 0


@cappa.command(
    name="stop",
    help="Stop the server.",
    description="Stop the server.",
)
@dataclass(kw_only=True)
class CommandIndexStop:
    """Command to stop the server."""

    def __call__(self) -> int:
        return 0 if Index().stop() else 1


@cappa.command(
    name="logs",
    help="Show the server logs.",
    description="Show the server logs.",
)
@dataclass(kw_only=True)
class CommandIndexLogs:
    """Command to show the server logs."""

    def __call__(self) -> int:
        index = Index()
        try:
            print(index.logs())
        except FileNotFoundError as error:
            config = CommandMain._load_config()
            if isinstance(config.index_log_path, Unset):
                print(error, file=sys.stderr)
                return 1
            print(config.index_log_path)
        return 0


# ============================================================================ #
# Teams                                                                        #
# ============================================================================ #
@cappa.command(name="team", help="Manage GitHub teams.")
@dataclass(kw_only=True)
class CommandTeam:
    """Command to manage GitHub teams."""

    subcommand: An[cappa.Subcommands[CommandTeamList | CommandTeamSync], Doc("The selected subcommand.")]


@cappa.command(
    name="list",
    help="List members of a team.",
    description=cleandoc(
        """
        List the members of a GitHub team.
        """,
    ),
)
@dataclass(kw_only=True)
class CommandTeamList:
    """Command to list team memberships."""

    def __call__(self) -> int:
        raise cappa.Exit("Not implemented yet.", code=1)


@cappa.command(
    name="sync",
    help="Synchronize members of a team with current sponsors.",
    description=cleandoc(
        """
        Fetch current sponsors from GitHub,
        then grant or revoke access to a GitHub team
        for eligible sponsors.
        """,
    ),
)
@dataclass(kw_only=True)
class CommandTeamSync:
    """Command to sync team memberships with current sponsors."""

    github_insiders_team: An[
        str,
        cappa.Arg(
            short=False,
            long=False,
            num_args=1,
            default=FromConfig(Config.github_insiders_team),
            show_default=f"{Config.github_insiders_team}",
            group=_GROUP_ARGUMENTS,
        ),
        Doc("""The GitHub team to sync."""),
    ]

    github_sponsored_account: An[
        str,
        cappa.Arg(
            short=False,
            long=("--ghsa", "--github-sponsored-account"),
            default=FromConfig(Config.github_sponsored_account),
            show_default=f"{Config.github_sponsored_account} or none",
            group=_GROUP_OPTIONS,
        ),
        Doc("""The sponsored account on GitHub Sponsors."""),
    ] = ""

    github_include_users: An[
        list[str],
        cappa.Arg(
            short=False,
            long=("--ghiu", "--github-include-users"),
            default=FromConfig(Config.github_include_users),
            show_default=f"{Config.github_include_users}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Users that should always be in the team."""),
    ] = field(default_factory=list)

    github_exclude_users: An[
        list[str],
        cappa.Arg(
            short=False,
            long=("--gheu", "--github-exclude-users"),
            default=FromConfig(Config.github_exclude_users),
            show_default=f"{Config.github_exclude_users}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Users that should never be in the team."""),
    ] = field(default_factory=list)

    github_organization_members: An[
        dict[str, list[str]],
        cappa.Arg(
            short=False,
            long=("--ghom", "--github-organization-members"),
            default=FromConfig(Config.github_organization_members),
            show_default=f"{Config.github_organization_members}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""A mapping of users belonging to sponsoring organizations."""),
    ] = field(default_factory=dict)

    github_token: An[
        str,
        cappa.Arg(
            short=False,
            long=("--ght", "--github-token"),
            default=cappa.Env("GITHUB_TOKEN") | FromConfig(Config.github_token),
            show_default="`GITHUB_TOKEN` env-var or `github.token-command` config-value",
            group=_GROUP_OPTIONS,
        ),
        Doc("""A GitHub token. Recommended scopes: `admin:org` and `read:user`."""),
    ] = ""

    polar_sponsored_account: An[
        str,
        cappa.Arg(
            short=False,
            long=("--plsa", "--polar-sponsored-account"),
            default=FromConfig(Config.polar_sponsored_account),
            show_default=f"{Config.polar_sponsored_account} or none",
            group=_GROUP_OPTIONS,
        ),
        Doc("""The sponsored account on Polar."""),
    ] = ""

    polar_token: An[
        str,
        cappa.Arg(
            short=False,
            long=("--plt", "--polar-token"),
            default=cappa.Env("POLAR_TOKEN") | FromConfig(Config.polar_token),
            show_default="`POLAR_TOKEN` env-var or `polar.token-command` config-value",
            group=_GROUP_OPTIONS,
        ),
        Doc("""A Polar token. Recommended scopes: `user:read`, `issues:read`, `subscriptions:read`."""),
    ] = ""

    minimum_amount: An[
        int,
        cappa.Arg(
            short=True,
            long=True,
            default=FromConfig(Config.sponsors_minimum_amount),
            show_default=f"{Config.sponsors_minimum_amount} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("""Minimum amount to be considered an insider."""),
    ] = 0

    def __call__(self) -> int:
        # TODO: Gather sponsors from configured platforms.
        with GitHub(self.github_token) as github:
            github.sync_team(
                self.github_insiders_team,
                min_amount=self.minimum_amount,
                include_users=set(self.github_include_users),
                exclude_users=set(self.github_exclude_users),
                org_users=self.github_organization_members,  # type: ignore[arg-type]
            )
        return 0


# ============================================================================ #
# Backlog                                                                      #
# ============================================================================ #
@cappa.command(
    name="backlog",
    help="List the backlog.",
    description=cleandoc(
        """
        List the issues in the backlog.
        """,
    ),
)
@dataclass(kw_only=True)
class CommandBacklog:
    """Command to list the backlog of issues."""

    @staticmethod
    def _parse_sort(arg: str) -> list[Callable]:
        return Config._eval_sort(arg.split(",")) or []

    backlog_namespaces: An[
        list[str],
        cappa.Arg(
            short=False,
            long=False,
            default=cappa.Env("BACKLOG_NAMESPACES") | FromConfig(Config.backlog_namespaces),
            show_default=f"`BACKLOG_NAMESPACES` env-var or {Config.backlog_namespaces}",
            group=_GROUP_ARGUMENTS,
        ),
        Doc("Namespaces to fetch issues from."),
    ]

    issue_labels: An[
        dict[str, str],
        cappa.Arg(
            short=True,
            long=True,
            default=FromConfig(Config.backlog_issue_labels),
            show_default=f"{Config.backlog_issue_labels}",
            group=_GROUP_OPTIONS,
        ),
        Doc("Issue labels to keep in issues metadata, and how they are represented."),
    ] = field(default_factory=dict)

    limit: An[
        int,
        cappa.Arg(
            short=True,
            long=True,
            default=FromConfig(Config.backlog_limit),
            show_default=f"{Config.backlog_limit} or `{{default}}`",
            group=_GROUP_OPTIONS,
        ),
        Doc("Limit the number of issues to display."),
    ] = 0

    sort: An[
        list[Callable],
        cappa.Arg(
            short=True,
            long=True,
            parse=_parse_sort,
            default=FromConfig(Config.backlog_sort),
            show_default=f"{Config.backlog_sort}",
            group=_GROUP_OPTIONS,
        ),
        Doc("Sort strategy."),
    ] = field(default_factory=list)

    public: An[
        bool,
        cappa.Arg(short=False, long=True, show_default=False, group=_GROUP_OPTIONS),
        Doc("Only use public sponsorships."),
    ] = False

    polar_token: An[
        str,
        cappa.Arg(
            short=False,
            long=("--plt", "--polar-token"),
            default=cappa.Env("POLAR_TOKEN") | FromConfig(Config.polar_token),
            show_default="`POLAR_TOKEN` env-var or `polar.token-command` config-value",
            group=_GROUP_OPTIONS,
        ),
        Doc("""A Polar token. Recommended scopes: `user:read`, `issues:read`, `subscriptions:read`."""),
    ] = ""

    github_token: An[
        str,
        cappa.Arg(
            short=False,
            long=("--ght", "--github-token"),
            default=cappa.Env("GITHUB_TOKEN") | FromConfig(Config.github_token),
            show_default="`GITHUB_TOKEN` env-var or `github.token-command` config-value",
            group=_GROUP_OPTIONS,
        ),
        Doc("""A GitHub token. Recommended scopes: `read:user`."""),
    ] = ""

    github_organization_members: An[
        dict[str, list[str]],
        cappa.Arg(
            short=False,
            long=("--ghom", "--github-organization-members"),
            default=FromConfig(Config.github_organization_members),
            show_default=f"{Config.github_organization_members}",
            group=_GROUP_OPTIONS,
        ),
        Doc("""A mapping of users belonging to sponsoring organizations."""),
    ] = field(default_factory=dict)

    def __call__(self) -> int:
        github_context = GitHub(self.github_token)
        polar_context = Polar(self.polar_token) if self.polar_token else nullcontext()
        with github_context as github, polar_context as polar, Console().status("") as status:
            status.update("Fetching sponsors from GitHub")
            sponsors = github.get_sponsors(self.github_organization_members, exclude_private=self.public)
            if polar:
                status.update("Fetching sponsors from Polar")
                sponsors.merge(polar.get_sponsors(exclude_private=self.public))
            status.update(f"Fetching issues from GitHub{' and Polar' if isinstance(polar, Polar) else ''}")
            backlog = get_backlog(
                self.backlog_namespaces,
                github=github,
                polar=polar,
                sponsors=sponsors,
                issue_labels=set(self.issue_labels),
            )
        if self.sort:
            status.update("Sorting issues")
            backlog.sort(*self.sort)
        print_backlog(backlog, self.issue_labels, limit=self.limit)
        return 0


# ============================================================================ #
# Main                                                                         #
# ============================================================================ #
@cappa.command(
    name="insiders",
    help="Manage your Insiders projects.",
    description=cleandoc(
        """
        This tool lets you manage your local and remote Git repositories
        for projects that offer an [Insiders](https://pawamoy.github.io/insiders/) version.

        See the documentation / help text of the different subcommands available.

        *Example*

        ```bash
        insiders --debug-info
        ```
        """,
    ),
)
@dataclass(kw_only=True)
class CommandMain:
    """Command to manage your Insiders projects."""

    _CONFIG: ClassVar[Config | None] = None

    @staticmethod
    def _load_config(file: Path | None = None) -> Config:
        if CommandMain._CONFIG is None:
            CommandMain._CONFIG = Config.from_file(file) if file else Config.from_default_location()
        return CommandMain._CONFIG

    subcommand: An[
        CommandProject | CommandPyPI | CommandIndex | CommandBacklog | CommandTeam,
        cappa.Subcommand(group=_GROUP_SUBCOMMANDS),
        Doc("The selected subcommand."),
    ]

    @staticmethod
    def _print_and_exit(func: Callable[[], str | None], code: int = 0) -> Callable[[], None]:
        @wraps(func)
        def _inner() -> None:
            raise cappa.Exit(func() or "", code=code)

        return _inner

    @staticmethod
    def _configure_logging(command: CommandMain) -> None:
        configure_logging(command.log_level, command.log_path)

    version: An[
        bool,
        cappa.Arg(
            short="-V",
            long=True,
            action=_print_and_exit(debug.get_version),
            num_args=0,
            group=_GROUP_OPTIONS,
        ),
        Doc("Print the program version and exit."),
    ] = False

    debug_info: An[
        bool,
        cappa.Arg(long=True, action=_print_and_exit(debug.print_debug_info), num_args=0, group=_GROUP_OPTIONS),
        Doc("Print debug information."),
    ] = False

    config: An[
        Config,
        cappa.Arg(
            short="-c",
            long=True,
            parse=_load_config,
            propagate=True,
            show_default=f"`{defaults.DEFAULT_CONF_PATH}`",
            group=_GROUP_GLOBAL_OPTIONS,
        ),
        Doc("Path to the configuration file."),
    ] = field(default_factory=_load_config)

    log_level: An[
        Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        cappa.Arg(
            short="-L",
            long=True,
            parse=str.upper,
            propagate=True,
            show_default=True,
            group=_GROUP_GLOBAL_OPTIONS,
        ),
        Doc("Log level to use when logging messages."),
    ] = "INFO"

    log_path: An[
        str | None,
        cappa.Arg(short="-P", long=True, propagate=True, show_default="standard error", group=_GROUP_GLOBAL_OPTIONS),
        Doc("Write log messages to this file path."),
    ] = None


def main(
    args: An[list[str] | None, Doc("Arguments passed from the command line.")] = None,
) -> An[int, Doc("An exit code.")]:
    """Run the main program.

    This function is executed when you type `insiders` or `python -m insiders`.
    """
    output = cappa.Output(error_format="[bold]insiders[/]: [bold red]error[/]: {message}")
    completion_option: cappa.Arg = cappa.Arg(
        long=True,
        action=cappa.ArgAction.completion,
        choices=["complete", "generate"],
        group=_GROUP_GLOBAL_OPTIONS,
        help="Print shell-specific completion source.",
    )
    help_option: cappa.Arg = cappa.Arg(
        short="-h",
        long=True,
        action=cappa.ArgAction.help,
        group=_GROUP_GLOBAL_OPTIONS,
        help="Print the program help and exit.",
    )
    help_formatter = cappa.HelpFormatter(default_format="Default: {default}.")

    try:
        return cappa.invoke(
            CommandMain,
            argv=args,
            output=output,
            help=help_option,
            completion=completion_option,
            help_formatter=help_formatter,
            deps=[CommandMain._configure_logging],
        )
    except cappa.Exit as exit:
        return int(exit.code or 0)
