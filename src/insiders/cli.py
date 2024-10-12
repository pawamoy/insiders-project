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

from dataclasses import asdict, dataclass
from functools import wraps
from inspect import cleandoc
from pathlib import Path
from typing import Annotated as An
from typing import Any, Callable

import cappa
from typing_extensions import Doc

from insiders import debug

NAME = "insiders"


def print_and_exit(
    func: An[Callable[[], str | None], Doc("A function that returns or prints a string.")],
    code: An[int, Doc("The status code to exit with.")] = 0,
) -> Callable[[], None]:
    """Argument action callable to print something and exit immediately."""

    @wraps(func)
    def _inner() -> None:
        raise cappa.Exit(func() or "", code=code)

    return _inner


@dataclass(kw_only=True)
class HelpOption:
    """Reusable class to share a `-h`, `--help` option."""

    help: An[
        bool,
        cappa.Arg(
            short="-h",
            long=True,
            action=cappa.ArgAction.help,
        ),
        Doc("Print the program help and exit."),
    ] = False

    @property
    def _options(self) -> dict[str, Any]:
        options = asdict(self)
        options.pop("help", None)
        return options


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
class CommandCreate(HelpOption):
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

    def __call__(self) -> int:  # noqa: D102
        from insiders.github import new_project
        from insiders.pypi import reserve_pypi

        options = self._options
        options.pop("register_pypi")
        new_project(**options)
        if self.register_pypi:
            reserve_pypi(username=self.username or self.namespace, name=self.repo, description=self.description)
        return 0


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
class CommandPyPIRegister(HelpOption):
    """Command to register a project name on PyPI."""

    username: An[
        str,
        cappa.Arg(short="-u", long=True),
        Doc("""Username on PyPI (your account)."""),
    ]
    name: An[
        str,
        cappa.Arg(short="-n", long=True),
        Doc("""Name to register."""),
    ]
    description: An[
        str,
        cappa.Arg(short="-d", long=True),
        Doc("""Description of the project on PyPI."""),
    ]

    def __call__(self) -> Any:  # noqa: D102
        from insiders.pypi import reserve_pypi

        reserve_pypi(self.username, self.name, self.description)
        return 0


@cappa.command(name="pypi", help="Manage PyPI-related things.")
@dataclass(kw_only=True)
class CommandPyPI(HelpOption):
    """Command to manage PyPI-related things."""

    subcommand: An[cappa.Subcommands[CommandPyPIRegister], Doc("The selected subcommand.")]


@cappa.command(
    name=NAME,
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
class CommandMain(HelpOption):
    """Command to manage your Insiders projects."""

    subcommand: An[cappa.Subcommands[CommandCreate | CommandPyPI], Doc("The selected subcommand.")]

    version: An[
        bool,
        cappa.Arg(
            short="-V",
            long=True,
            action=print_and_exit(debug.get_version),
            num_args=0,
            help="Print the program version and exit.",
        ),
    ] = False

    debug_info: An[
        bool,
        cappa.Arg(long=True, action=print_and_exit(debug.print_debug_info), num_args=0),
        Doc("Print debug information."),
    ] = False

    completion: An[
        bool,
        cappa.Arg(
            long=True,
            action=cappa.ArgAction.completion,
            choices=("complete", "generate"),
            help="Print shell-specific completion source.",
        ),
    ] = False


def main(
    args: An[list[str] | None, Doc("Arguments passed from the command line.")] = None,
) -> An[int, Doc("An exit code.")]:
    """Run the main program.

    This function is executed when you type `insiders` or `python -m insiders`.
    """
    output = cappa.Output(error_format=f"[bold]{NAME}[/]: [bold red]error[/]: {{message}}")
    return cappa.invoke(CommandMain, argv=args, output=output, backend=cappa.backend, completion=False, help=False)
