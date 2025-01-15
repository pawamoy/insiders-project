"""PyPI integration."""

from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Annotated as An

from build import ProjectBuilder
from build.env import DefaultIsolatedEnv
from failprint import Capture
from pypi_insiders.logger import log_captured, logger, redirect_output_to_logging
from twine.commands.upload import upload
from twine.settings import Settings
from typing_extensions import Doc

# TODO: Rewrite as a proper Client subclass.


def _git_user_name(default: str = "") -> str:
    return subprocess.getoutput("git config user.name").strip() or default  # noqa: S605,S607


def _git_user_email(default: str = "") -> str:
    return subprocess.getoutput("git config user.email").strip() or default  # noqa: S605,S607


def reserve_pypi(
    username: An[str, Doc("Username on PyPI.")],
    name: An[str, Doc("Name to reserve.")],
    description: An[str, Doc("Description of the project on PyPI.")],
) -> None:
    """Reserve a name on PyPI."""
    with TemporaryDirectory(prefix="insiders-") as tmpdir:
        repo = Path(tmpdir, name)
        repo.mkdir()
        dist = repo / "dist"

        logger.info(f"Preparing package {name}, {description}")
        repo.joinpath("pyproject.toml").write_text(
            dedent(
                f"""
                [project]
                name = "{name}"
                version = "0.0.0"
                description = "{description} Available to sponsors only."
                authors = [{{name = "{_git_user_name()}", email = "{_git_user_email()}"}}]
                readme = "README.md"
                requires-python = ">=3.8"
                classifiers = ["Development Status :: 1 - Planning"]
                """,
            ).lstrip(),
        )

        repo.joinpath("README.md").write_text(
            dedent(
                f"""
                # {name}

                {description}

                This project is currently available to [sponsors](https://github.com/sponsors/{username}) only.
                See https://{username}.github.io/{name}/insiders.
                """,
            ).lstrip(),
        )

        logger.info("Building distributions")
        for distribution in ("sdist", "wheel"):
            with DefaultIsolatedEnv() as env:
                builder = ProjectBuilder.from_isolated_env(env, repo)
                env.install(builder.build_system_requires)
                with Capture.BOTH.here() as captured:
                    env.install(builder.get_requires_for_build(distribution))
                    builder.build(distribution, str(dist))
                log_captured(str(captured), level="debug", pkg="build")

        logger.info("Uploading distributions")
        with redirect_output_to_logging(stdout_level="debug"):
            upload(
                Settings(
                    non_interactive=True,
                    skip_existing=True,
                    username="__token__",
                    disable_progress_bar=True,
                    verbose=True,
                ),
                [str(file) for file in dist.iterdir()],
            )
