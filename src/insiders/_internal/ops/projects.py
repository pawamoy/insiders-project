from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Annotated as An
from typing import Any

from copier import run_copy as copier_run
from pypi_insiders.logger import run as run_and_log
from typing_extensions import Doc

from insiders._internal.logger import logger

_gh_repo_create = partial(run_and_log, "gh", "repo", "create")


def new_public_and_insiders_github_projects(
    *,
    public_namespace: An[str, Doc("Namespace of the public repository.")],
    public_name: An[str, Doc("Name of the public repository.")],
    description: An[str, Doc("Shared description.")],
    public_repo_path: An[str | Path, Doc("Local path in which to clone the public repository.")],
    insiders_namespace: An[
        str | None,
        Doc("Namespace of the insiders repository. Defaults to the public namespace."),
    ] = None,
    insiders_name: An[str | None, Doc("Name of the insiders repository. Defaults to the public name.")] = None,
    insiders_repo_path: An[str | Path, Doc("Local path in which to clone the insiders repository.")],
    github_username: An[str | None, Doc("Username. Defaults to the public namespace value.")] = None,
    copier_template: An[str | None, Doc("Copier template to initialize the local insiders repository with.")] = None,
    copier_template_answers: An[dict[str, Any] | None, Doc("Answers to the Copier template questions.")] = None,
    post_creation_command: An[
        str | list[str] | None,
        Doc("Command to run after creating the public repository."),
    ] = None,
) -> None:
    """Create a new Insiders project on GitHub (public and private repositories)."""
    github_username = github_username or public_namespace
    insiders_namespace = insiders_namespace or f"{github_username}-insiders"
    insiders_name = insiders_name or public_name
    public_description = f"{description} Available to sponsors only."

    logger.debug("Creating new project with these settings:")
    logger.debug(f"- public repo:   {public_namespace}/{public_name} cloned in {public_repo_path}")
    logger.debug(f"- insiders repo: {insiders_namespace}/{insiders_name} cloned in {insiders_repo_path}")

    common_opts = ("--disable-wiki", "--homepage", f"https://{public_namespace}.github.io/{public_name}")
    public_opts = ("--description", public_description, "--public", *common_opts)
    insiders_opts = ("--description", description, "--private", "--disable-issues", *common_opts)
    _gh_repo_create(f"{public_namespace}/{public_name}", *public_opts)
    _gh_repo_create(f"{insiders_namespace}/{insiders_name}", *insiders_opts)

    repo_path = Path(public_repo_path)
    run_and_log("git", "clone", f"git@github.com:{public_namespace}/{public_name}", repo_path)

    if copier_template:
        copier_run(
            copier_template,
            repo_path,
            user_defaults=copier_template_answers or {},
            overwrite=True,
            unsafe=True,
        )

    commit_message = f"feat: Generate project with {copier_template} Copier template"
    run_and_log("git", "-C", repo_path, "add", "-A")
    run_and_log("git", "-C", repo_path, "commit", "-m", commit_message)

    if isinstance(post_creation_command, str):
        run_and_log(post_creation_command, cwd=repo_path, shell=True)  # noqa: S604
    elif isinstance(post_creation_command, list):
        run_and_log(*post_creation_command, cwd=repo_path)
    else:
        run_and_log("git", "-C", repo_path, "push")

    insiders_repo_path = Path(insiders_repo_path)
    run_and_log("git", "clone", f"git@github.com:{insiders_namespace}/{insiders_name}", insiders_repo_path)
    run_and_log(
        "git",
        "-C",
        insiders_repo_path,
        "remote",
        "add",
        "upstream",
        f"git@github.com:{public_namespace}/{public_name}",
    )
    run_and_log("git", "-C", insiders_repo_path, "pull", "upstream", "main")
