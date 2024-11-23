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

import argparse
import json
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
from insiders._internal.config import Config
from insiders._internal.logger import configure_logging

# TODO: Re-organize all this.
from insiders._internal.ops.backlog import get_backlog, print_backlog
from insiders._internal.ops.projects import new_public_and_insiders_github_projects

_GROUP_GLOBAL = (15, "Global options")
_GROUP_SUBCOMMANDS = (100, "Subcommands")


def from_config(attr_name: str) -> Any:
    config = CommandMain._load_config()
    return getattr(config, attr_name)


@dataclass(frozen=True)
class FromConfig(cappa.ValueFrom):
    conf_name: str

    def __init__(self, attr_name: str, conf_name: str) -> None:
        super().__init__(from_config, attr_name)
        object.__setattr__(self, "conf_name", conf_name)

    def __str__(self) -> str:
        return f"configuration value `{self.conf_name}`"


# ============================================================================ #
# Projects                                                                     #
# ============================================================================ #
@cappa.command(name="project", help="Manage projects (GitHub and local copies).")
@dataclass(kw_only=True)
class CommandProject:
    """Command to manage projects on GitHub and locally."""

    subcommand: An[cappa.Subcommands[CommandProjectCreate | CommandProjectCheck], Doc("The selected subcommand.")]


@cappa.command(
    name="create",
    help="Create public/insiders repositories.",
    description=cleandoc(
        """
        This command will do several things:

        - Create public and insiders repositories on GitHub
            (using the provided namespace, username, repository name, description, etc.).
        - Clone these two repositories locally (using the provided repository paths).
        - Initialize the public repository with a `README` and a dummy CI job that always passes.
        - Optionally initialize the insiders repository by generating initial contents
            using the specified [Copier](https://copier.readthedocs.io/en/stable/) template.

        *Example 1 - Project in user's namespace*

        The insiders namespace, insiders repository name and username are inferred
        from the namespace and repository name.

        ```bash
        insiders create \\
            -n pawamoy \\
            -r mkdocs-ultimate \\
            -d "The ultimate plugin for MkDocs (??)" \\
            -p ~/data/dev/mkdocs-ultimate \\
            -P ~/data/dev/insiders/mkdocs-ultimate \\
            -t gh:pawamoy/copier-pdm
        ```

        *Example 2 - Project in another namespace:*

        The insiders namespace, insiders repository name and username are different,
        so must be provided explicitly:

        ```bash
        insiders create \\
            -n mkdocstrings \\
            -r rust \\
            -d "A Rust handler for mkdocstrings" \\
            -p ~/data/dev/mkdocstrings-rust \\
            -P ~/data/dev/insiders/mkdocstrings-rust \\
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

    namespace: An[
        str,
        cappa.Arg(short="-n", long=True),
        Doc("""Namespace of the public repository."""),
    ]
    repo: An[
        str,
        cappa.Arg(short="-r", long=True),
        Doc("""Name of the public repository."""),
    ]
    description: An[
        str,
        cappa.Arg(short="-d", long=True),
        Doc("""Shared description."""),
    ]
    repo_path: An[
        Path,
        cappa.Arg(short="-p", long=True),
        Doc("""Local path in which to clone the public repository."""),
    ]
    insiders_repo_path: An[
        Path,
        cappa.Arg(short="-P", long=True),
        Doc("""Local path in which to clone the insiders repository."""),
    ]
    insiders_namespace: An[
        str | None,
        cappa.Arg(short="-N", long=True),
        Doc("""Namespace of the insiders repository. Defaults to the public namespace."""),
    ] = None
    insiders_repo: An[
        str | None,
        cappa.Arg(short="-R", long=True),
        Doc("""Name of the insiders repository. Defaults to the public name."""),
    ] = None
    username: An[
        str | None,
        cappa.Arg(short="-u", long=True),
        Doc("""Username. Defaults to the public namespace value."""),
    ] = None
    copier_template: An[
        str | None,
        cappa.Arg(short="-t", long=True),
        Doc("""Copier template to initialize the local insiders repository with."""),
    ] = None
    register_pypi: An[
        bool,
        cappa.Arg(short="-i", long=True),
        Doc("""Whether to register the project name on PyPI as version 0.0.0."""),
    ] = False

    def __call__(self) -> int:
        new_public_and_insiders_github_projects(
            public_namespace=self.namespace,
            public_name=self.repo,
            description=self.description,
            public_repo_path=self.repo_path,
            insiders_repo_path=self.insiders_repo_path,
            insiders_namespace=self.insiders_namespace,
            insiders_name=self.insiders_repo,
            github_username=self.username,
            copier_template=self.copier_template,
        )
        if self.register_pypi:
            pypi.reserve_pypi(username=self.username or self.namespace, name=self.repo, description=self.description)
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
        raise NotImplementedError("Not implemented yet.")


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
        cappa.Arg(short="-u", long=True),
        Doc("Username on PyPI (your account)."),
    ]
    name: An[
        str,
        cappa.Arg(short="-n", long=True),
        Doc("Name to register."),
    ]
    description: An[
        str,
        cappa.Arg(short="-d", long=True),
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

    dist_dir: An[
        Path,
        cappa.Arg(short="-d", long=True),
        Doc("Directory where the distributions are stored."),
    ] = defaults.DEFAULT_DIST_DIR

    def __call__(self) -> int:
        index = Index(dist_dir=self.dist_dir)
        for dist in index.list():
            print(dist)
        return 0


@cappa.command(
    name="add",
    help="Add insiders repositories.",
    description="Add a repository to the watched repositories.",
)
@dataclass(kw_only=True)
class CommandIndexAdd:
    """Command to add a repository to the watched repositories."""

    @staticmethod
    def _repo_pkg(args: list[str]) -> list[tuple[str, str]]:
        try:
            return [tuple(arg.split(":", 1)) for arg in args]  # type: ignore[misc]
        except ValueError as error:
            raise argparse.ArgumentTypeError("Repositories must be of the form NAMESPACE/PROJECT:PACKAGE") from error

    repositories: An[
        list[tuple[str, str]],
        cappa.Arg(required=True, num_args=-1, parse=_repo_pkg),
        Doc("List of NAMESPACE/PROJECT:PACKAGE repositories."),
    ]

    git_dir: An[
        Path,
        cappa.Arg(short="-r", long=True),
        Doc("Directory where the repositories are cloned."),
    ] = defaults.DEFAULT_REPO_DIR

    url: An[
        str,
        cappa.Arg(short="-i", long=True),
        Doc("URL of the index to upload packages to."),
    ] = defaults.DEFAULT_INDEX_URL

    def __call__(self) -> int:
        index = Index(url=self.url, git_dir=self.git_dir)
        for namespace, project in self.repositories:
            index.add(namespace, project)
        return 0


@cappa.command(
    name="remove",
    help="Remove insiders repositories.",
    description="Remove a repository from the watched repositories.",
)
@dataclass(kw_only=True)
class CommandIndexRemove:
    """Command to remove a repository from the watched repositories."""

    repositories: An[
        list[str],
        cappa.Arg(),
        Doc("List of repository names."),
    ] = field(default_factory=list)

    repo_dir: An[
        Path,
        cappa.Arg(short="-r", long=True),
        Doc("Directory where the repositories are cloned."),
    ] = defaults.DEFAULT_REPO_DIR

    def __call__(self) -> int:
        index = Index(git_dir=self.repo_dir)
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

    repo_dir: An[
        Path,
        cappa.Arg(short="-r", long=True),
        Doc("Directory where the repositories are cloned."),
    ] = defaults.DEFAULT_REPO_DIR

    # TODO: Normalize option across commands.
    index_url: An[
        str,
        cappa.Arg(short="-i", long=True),
        Doc("URL of the index to upload packages to."),
    ] = defaults.DEFAULT_INDEX_URL

    repositories: An[
        list[str],
        cappa.Arg(num_args=-1),
        Doc("List of repository names."),
    ] = field(default_factory=list)

    def __call__(self) -> int:
        index = Index(url=self.index_url, git_dir=self.repo_dir)
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

    url: An[
        str,
        cappa.Arg(short=False, long=True),
        Doc("URL of the index to upload packages to."),
    ] = defaults.DEFAULT_INDEX_URL

    repo_dir: An[
        Path,
        cappa.Arg(short="-r", long=True),
        Doc("Directory where the repositories are cloned."),
    ] = defaults.DEFAULT_REPO_DIR

    dist_dir: An[
        Path,
        cappa.Arg(short="-d", long=True),
        Doc("Directory where the distributions are stored."),
    ] = defaults.DEFAULT_DIST_DIR

    background: An[
        bool,
        cappa.Arg(short="-b", long=True),
        Doc("Run the server in the background."),
    ] = False

    def __call__(self) -> int:
        index = Index(url=self.url, dist_dir=self.dist_dir)
        index.start(background=self.background)
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
            print(error, file=sys.stderr)
            return 1
        return 0


# ============================================================================ #
# Teams                                                                        #
# ============================================================================ #
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

    team: An[
        str,
        cappa.Arg(num_args=1),
        Doc("The GitHub team to sync sponsors with."),
    ]
    github_sponsored_account: An[
        str,
        cappa.Arg(short=False, long=True),
        Doc("""The sponsored account on GitHub Sponsors."""),
    ]
    polar_sponsored_account: An[
        str,
        cappa.Arg(short=False, long=True),
        Doc("""The sponsored account on Polar."""),
    ]
    min_amount: An[
        int,
        cappa.Arg(short=False, long=True),
        Doc("""Minimum amount to be considered an Insider."""),
    ]
    github_team: An[
        str,
        cappa.Arg(short=False, long=True),
        Doc("""The GitHub team to sync."""),
    ]
    github_include_users: An[
        list[str],
        cappa.Arg(short=False, long=True, default=FromConfig("github_include_users", "github.include-users")),
        Doc("""Users that should always be in the team."""),
    ]
    github_exclude_users: An[
        list[str],
        cappa.Arg(short=False, long=True, default=FromConfig("github_exclude_users", "github.exclude-users")),
        Doc("""Users that should never be in the team."""),
    ]
    github_organization_members: An[
        dict[str, list[str]],
        cappa.Arg(short=False, long=True),
        Doc("""A mapping of users belonging to sponsoring organizations."""),
    ]
    github_token: An[
        str,
        cappa.Arg(short=False, long=True, default=cappa.Env("GITHUB_TOKEN")),
        Doc("""A GitHub token. Recommended scopes: `admin:org` and `read:user`."""),
    ]

    def __call__(self) -> int:
        # TODO: Gather sponsors from configured platforms.
        with GitHub(self.github_token) as github:
            github.sync_team(
                self.team,
                min_amount=self.min_amount,
                include_users=set(self.github_include_users),
                exclude_users=set(self.github_exclude_users),
                org_users=self.github_organization_members,  # type: ignore[arg-type]
            )
        return 0


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
        raise NotImplementedError("Not implemented yet.")


@cappa.command(name="team", help="Manage GitHub teams.")
@dataclass(kw_only=True)
class CommandTeam:
    """Command to manage GitHub teams."""

    subcommand: An[cappa.Subcommands[CommandTeamList | CommandTeamSync], Doc("The selected subcommand.")]


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

    github_namespaces: An[
        list[str],
        cappa.Arg(
            long=True,
            num_args=-1,
            default=cappa.Env("BACKLOG_NAMESPACES") | FromConfig("backlog_namespaces", "backlog.namespaces"),
        ),
        Doc("Namespaces to fetch issues from."),
    ]

    github_token: An[
        str,
        cappa.Arg(
            short=False,
            long=True,
            default=cappa.Env("GITHUB_TOKEN") | FromConfig("github_token", "github.token-command"),
        ),
        Doc("""A GitHub token. Recommended scopes: `read:user`."""),
    ]

    polar_token: An[
        str,
        cappa.Arg(
            short=False,
            long=True,
            default=cappa.Env("POLAR_TOKEN") | FromConfig("polar_token", "polar.token-command"),
        ),
        Doc("""A Polar token. Recommended scopes: `user:read`, `issues:read`, `subscriptions:read`."""),
    ]

    github_organization_members: An[
        dict[str, list[str]],
        cappa.Arg(
            short=False,
            long=True,
            default=FromConfig("github_organization_members", "github.organization-members"),
        ),
        Doc("""A mapping of users belonging to sponsoring organizations."""),
    ] = field(default_factory=dict)

    @staticmethod
    def _parse_sort(arg: str) -> list[Callable]:
        return Config._eval_sort(arg.split(",")) or []

    sort: An[
        list[Callable],
        cappa.Arg(
            short="-s",
            long=True,
            parse=_parse_sort,
            default=FromConfig("backlog_sort", "backlog.sort"),
        ),
        Doc("Sort strategy."),
    ] = field(default_factory=list)

    issue_labels: An[
        dict[str, str],
        cappa.Arg(short=False, long=True, default=FromConfig("backlog_issue_labels", "backlog.issue-labels")),
        Doc("Issue labels to keep in issues metadata, and how they are represented."),
    ] = field(default_factory=dict)

    public: An[
        bool,
        cappa.Arg(short=False, long=True),
        Doc("Only use public sponsorships."),
    ] = False

    limit: An[
        int,
        cappa.Arg(short=False, long=True, default=FromConfig("backlog_limit", "backlog.limit")),
        Doc("Limit the number of issues to display."),
    ] = 0

    def __call__(self) -> int:
        github_context = GitHub(self.github_token)
        polar_context = Polar(self.polar_token) if self.polar_token else nullcontext()
        with github_context as github, polar_context as polar, Console().status("") as status:
            status.update("Fetching sponsors from GitHub")
            sponsors = github.get_sponsors(self.github_organization_members, exclude_private=self.public)
            if polar:
                status.update("Fetching sponsors from Polar")
                sponsors.merge(polar.get_sponsors(exclude_private=self.public))
            status.update("Fetching issues from GitHub")
            backlog = get_backlog(
                self.github_namespaces,
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
        configure_logging(command.log_level, command.log_path, allow="pypiserver")

    version: An[
        bool,
        cappa.Arg(
            short="-V",
            long=True,
            action=_print_and_exit(debug.get_version),
            num_args=0,
        ),
        Doc("Print the program version and exit."),
    ] = False

    debug_info: An[
        bool,
        cappa.Arg(long=True, action=_print_and_exit(debug.print_debug_info), num_args=0),
        Doc("Print debug information."),
    ] = False

    config: An[
        Config,
        cappa.Arg(
            short="-c",
            long=True,
            parse=_load_config,
            group=_GROUP_GLOBAL,
            propagate=True,
        ),
        Doc("Path to the configuration file."),
    ] = field(default_factory=Config.from_default_location)

    log_level: An[
        Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        cappa.Arg(short="-L", long=True, parse=str.upper, group=_GROUP_GLOBAL, propagate=True),
        Doc("Log level to use when logging messages."),
    ] = "INFO"

    log_path: An[
        str | None,
        cappa.Arg(short="-P", long=True, group=_GROUP_GLOBAL, propagate=True),
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
        group=_GROUP_GLOBAL,
        help="Print shell-specific completion source.",
    )
    help_option: cappa.Arg = cappa.Arg(
        short="-h",
        long=True,
        action=cappa.ArgAction.help,
        group=_GROUP_GLOBAL,
        help="Print the program help and exit.",
    )
    help_formatter = cappa.HelpFormatter(default_format="Default: `{default}`.")

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


if __name__ == "__main__":
    sys.exit(main(["backlog", "list"]))
