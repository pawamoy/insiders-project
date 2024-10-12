"""GitHub integration."""

from functools import partial
from pathlib import Path
from typing import Annotated as An

from copier import run_copy
from pypi_insiders.logger import logger, run
from typing_extensions import Doc

_gh_repo_create = partial(run, "gh", "repo", "create")


def new_project(
    *,
    namespace: An[str, Doc("Namespace of the public repository.")],
    repo: An[str, Doc("Name of the public repository.")],
    description: An[str, Doc("Shared description.")],
    repo_path: An[str | Path, Doc("Local path in which to clone the public repository.")],
    insiders_repo_path: An[str | Path, Doc("Local path in which to clone the insiders repository.")],
    insiders_namespace: An[
        str | None,
        Doc("Namespace of the insiders repository. Defaults to the public namespace."),
    ] = None,
    insiders_repo: An[str | None, Doc("Name of the insiders repository. Defaults to the public name.")] = None,
    username: An[str | None, Doc("Username. Defaults to the public namespace value.")] = None,
    copier_template: An[str | None, Doc("Copier template to initialize the local insiders repository with.")] = None,
) -> None:
    """Create a new Insiders project on GitHub (public and private repositories)."""
    username = username or namespace
    insiders_namespace = insiders_namespace or f"{username}-insiders"
    insiders_repo = insiders_repo or repo
    public_description = f"{description} Available to sponsors only."

    logger.debug("Creating new project with these settings:")
    logger.debug(f"- public repo:   {namespace}/{repo} cloned in {repo_path}")
    logger.debug(f"- insiders repo: {insiders_namespace}/{insiders_repo} cloned in {insiders_repo_path}")

    common_opts = ("--disable-wiki", "--homepage", f"https://{namespace}.github.io/{repo}")
    public_opts = ("--description", public_description, "--public", *common_opts)
    insiders_opts = ("--description", description, "--private", "--disable-issues", *common_opts)
    _gh_repo_create(f"{namespace}/{repo}", *public_opts)
    _gh_repo_create(f"{insiders_namespace}/{insiders_repo}", *insiders_opts)

    repo_path = Path(repo_path)
    run("git", "clone", f"git@github.com:{namespace}/{repo}", repo_path)

    if not copier_template and username == "pawamoy":
        if "handler for mkdocstrings" in description:
            copier_template = "gh:mkdocstrings/handler-template"
        else:
            copier_template = "gh:pawamoy/copier-uv"

    defaults = {}
    release_command = None
    if copier_template and username == "pawamoy":
        defaults = {
            "project_name": repo,
            "project_description": description,
            "author_username": username,
            "repository_namespace": namespace,
            "repository_name": repo,
            "insiders": True,
            "insiders_repository_name": insiders_repo,
            "public_release": False,
        }
        release_command = "python scripts/make setup changelog release version=0.1.0".split()

    if copier_template:
        run_copy(
            copier_template,
            repo_path,
            user_defaults=defaults,
            overwrite=True,
            unsafe=True,
        )

    commit_message = f"feat: Generate project with {copier_template} Copier template"
    run("git", "-C", repo_path, "add", "-A")
    run("git", "-C", repo_path, "commit", "-m", commit_message)

    if release_command:
        run(*release_command, cwd=repo_path)
    else:
        run("git", "-C", repo_path, "push")

    insiders_repo_path = Path(insiders_repo_path)
    run("git", "clone", f"git@github.com:{insiders_namespace}/{insiders_repo}", insiders_repo_path)
    run("git", "-C", insiders_repo_path, "remote", "add", "upstream", f"git@github.com:{namespace}/{repo}")
    run("git", "-C", insiders_repo_path, "pull", "upstream", "main")
