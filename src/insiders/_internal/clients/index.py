# Manage PyPI-like index.

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated as An
from urllib.parse import urlparse

import psutil
from build.__main__ import build_package
from failprint import Capture
from packaging.version import InvalidVersion, Version
from pypiserver.__main__ import main as serve
from twine.commands.upload import upload
from twine.settings import Settings
from typing_extensions import Doc
from unearth import PackageFinder

from insiders._internal import defaults
from insiders._internal.logger import log_captured, logger, redirect_output_to_logging, run

# YORE: EOL 3.10: Replace block with line 2.
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any


def _normalize_version(version: str) -> str:
    if version[0] == "v":
        version = version[1:]
    return version.replace("+", ".").replace("-", ".")


class GitCache:
    """A cache for local clones of configured repositories."""

    def __init__(self, cache_dir: str | Path = defaults.DEFAULT_REPO_DIR) -> None:
        """Initialize the cache.

        Parameters:
            cache_dir: The directory in which to clone the repositories.
        """
        self.cache_dir: Path = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)

    def _git(self, repo: str, *args: str, **kwargs: Any) -> str:
        cached_repo = self.cache_dir / repo
        return run("git", "-C", cached_repo, *args, **kwargs)

    def list(self) -> Iterator[str]:
        """List the repositories in the cache.

        Returns:
            An iterator over the repository names.
        """
        yield from (repo.name for repo in self.cache_dir.iterdir())

    def exists(self, repo: str) -> bool:
        """Check if a repository already exists.

        Parameters:
            repo: The repository to check.

        Returns:
            True or false.
        """
        return self.cache_dir.joinpath(repo).exists()

    def clone(self, repo: str, url: str) -> Path:
        """Clone a repository.

        Parameters:
            repo: The repository to clone.

        Returns:
            The path to the cloned repository.
        """
        logger.debug(f"{repo}: Cloning {url}")
        cached_repo = self.cache_dir / repo
        cached_repo.parent.mkdir(exist_ok=True)
        run("git", "clone", url, cached_repo)
        return cached_repo

    def checkout(self, repo: str, ref: str) -> None:
        """Checkout a ref.

        Parameters:
            repo: The repository to work on.
        """
        logger.debug(f"{repo}: Checking out {ref}")
        self._git(repo, "checkout", ref)

    def checkout_origin_head(self, repo: str) -> None:
        """Checkout origin's HEAD again.

        Parameters:
            repo: The repository to work on.
        """
        logger.debug(f"{repo}: Checking out origin's HEAD")
        self._git(repo, "remote", "set-head", "origin", "--auto")
        ref = self._git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
        self.checkout(repo, ref.strip().split("/")[3])

    def pull(self, repo: str) -> None:
        """Pull latest changes.

        Parameters:
            repo: The repository to work on.
        """
        logger.debug(f"{repo}: Pulling latest changes")
        self._git(repo, "pull")

    def dist_name(self, repo: str) -> str:
        """Get the distribution name.

        Parameters:
            repo: The repository to work on.

        Returns:
            The distribution name.
        """
        with self.cache_dir.joinpath(repo, "pyproject.toml").open("rb") as file:
            return tomllib.load(file)["project"]["name"]

    def latest_tag(self, repo: str) -> str:
        """Get the latest Git tag.

        Parameters:
            repo: The repository to work on.

        Returns:
            A tag.
        """
        return self._git(repo, "describe", "--tags", "--abbrev=0").strip()

    def remove(self, repo: str) -> None:
        """Remove a repository from the cache.

        Parameters:
            repo: The repository to remove.
        """
        shutil.rmtree(self.cache_dir / repo, ignore_errors=True)

    def remove_dist(self, repo: str) -> None:
        """Remove the `dist` folder of a repository.

        Parameters:
            repo: The repository to work on.
        """
        shutil.rmtree(self.cache_dir.joinpath(repo, "dist"), ignore_errors=True)

    def build(self, repo: str) -> Iterator[Path]:
        """Build distributions.

        Parameters:
            repo: The repository to work on.

        Returns:
            File path for each distribution.
        """
        cached_repo = self.cache_dir / repo
        with Capture.BOTH.here() as captured:
            build_package(cached_repo, cached_repo / "dist", distributions=["sdist", "wheel"])
        log_captured(str(captured), level="debug", pkg="build")
        return cached_repo.joinpath("dist").iterdir()


class Index:
    """Index of repositories."""

    def __init__(
        self,
        url: str = defaults.DEFAULT_INDEX_URL,
        git_dir: Path = defaults.DEFAULT_REPO_DIR,
        dist_dir: Path = defaults.DEFAULT_DIST_DIR,
    ) -> None:
        """Initialize the index.

        Parameters:
            conf_path: The path to the configuration file.
        """
        self.url: An[str, Doc("The URL of the index.")] = url
        self.git_dir: An[Path, Doc("The directory in which to clone the repositories.")] = git_dir
        self.dist_dir: An[Path, Doc("The directory in which to store the distributions.")] = dist_dir

        parsed = urlparse(url)
        self.port: An[int, Doc("The port of the index server.")] = parsed.port or 80

        self.dist_dir.mkdir(parents=True, exist_ok=True)
        self._git_cache = GitCache(self.git_dir)
        self._finder = PackageFinder(index_urls=[f"{self.url}/simple"])

    def add(self, git_url: str, repo: str | None = None) -> None:
        """Add a repository to the index."""
        repo = repo or git_url.split("/")[-1].replace(".git", "")
        cache = self._git_cache
        if not cache.exists(repo):
            cache.clone(repo, git_url)
            cache.checkout(repo, cache.latest_tag(repo))
            self.upload(cache.build(repo))

    def remove(self, repo: str) -> None:
        """Remove a repository from the index."""
        try:
            dist_name = self._git_cache.dist_name(repo).replace("-", "_")
        except FileNotFoundError:
            logger.warning(f"{repo}: Repository not found, skipping")
            return
        self._git_cache.remove(repo)
        for dist in self.dist_dir.glob(f"{dist_name}-*"):
            dist.unlink()

    def list_distributions(self) -> Iterator[Path]:
        """List the distributions in the index."""
        yield from self.dist_dir.iterdir()

    def list_projects(self) -> Iterator[Path]:
        """List the projects in the index."""
        yield from self._git_cache.cache_dir.iterdir()

    def update(self, projects: Iterable[str] | None = None) -> None:
        """Update PyPI packages.

        For each configured repository, pull latest contents,
        checkout latest tag, and if the corresponding version is not present on the index,
        build and upload distributions.
        """
        cache = self._git_cache
        projects = projects or sorted(cache.list())
        for name in projects:
            if not cache.exists(name):
                logger.warning(f"{name}: Repository not found, skipping")
                continue
            dist_name = cache.dist_name(name)
            logger.info(f"{name}: Updating sources")
            cache.checkout_origin_head(name)
            cache.pull(name)

            latest_tag = cache.latest_tag(name)
            if latest_tag:
                logger.debug(f"{name}: Latest tag is {latest_tag}")
            else:
                logger.debug(f"{name}: No tags found")
                continue
            latest_version = self.latest(dist_name)
            if latest_version:
                logger.debug(f"{name}: Latest PyPI version is {latest_version}")

            normal_tag = _normalize_version(latest_tag)
            normal_version = _normalize_version(latest_version or "0.0.0")
            if latest_version is None or normal_tag != normal_version:
                try:
                    if Version(normal_tag) < Version(normal_version):
                        logger.warning(f"Latest tag {latest_tag} is older than latest PyPI version {latest_version}")
                        if self.exists(dist_name, normal_tag):
                            continue
                except InvalidVersion:
                    pass
                logger.info(f"{name}: Building and uploading {normal_tag} (current: {normal_version})")
                cache.remove_dist(name)
                cache.checkout(name, latest_tag)
                new_dists = cache.build(name)
                self.upload(new_dists)
                logger.success(f"{name}: Built and published version {normal_tag}")

    def start(self, *, background: bool = False, log_path: str | None = None) -> None:
        """Start the server."""
        if background and os.fork():
            return
        args = [
            "run",
            str(self.dist_dir),
            f"-p{self.port}",
            "-a.",
            "-P.",
            "--log-stream=none",
        ]
        if log_path:
            args.extend(("--log-file", log_path))
        serve(args)

    def stop(self) -> An[bool, Doc("Whether the server was stopped or not.")]:
        """Stop the server."""
        for proc in psutil.process_iter():
            try:
                cmdline = " ".join(proc.cmdline())
            except psutil.Error:
                continue
            if "insiders index start" in cmdline:
                proc.kill()
                return True
        return False

    def status(self) -> An[dict | None, Doc("Some metadata about the server process.")]:
        """Return the server status as a dict of metadata."""
        for proc in psutil.process_iter():
            try:
                cmdline = " ".join(proc.cmdline())
            except psutil.Error:
                continue
            if "insiders index start" in cmdline:
                return proc.as_dict(attrs=("ppid", "create_time", "username", "name", "cmdline", "pid"))
        return None

    def logs(self) -> str:
        """Return the logs file path."""
        if not (status := self.status()):
            raise FileNotFoundError("Server not running")
        for index, arg in enumerate(status["cmdline"][1:], 1):
            if arg.startswith("-p"):
                if len(arg) > 2:  # noqa: PLR2004
                    return arg[2:]
                return status["cmdline"][index + 1]
            if arg.startswith("--server-log-path"):
                if len(arg) > 18:  # noqa: PLR2004
                    return arg[18:]
                return status["cmdline"][index + 1]
        raise FileNotFoundError("Logs file not found")

    def latest(
        self,
        name: An[str, Doc("The package name (distribution name).")],
    ) -> An[str | None, Doc("The version as a string, or none.")]:
        """Get the latest version of a package."""
        result = self._finder.find_best_match(name, allow_prereleases=True, allow_yanked=True)
        return result.best.version if result.best else None

    def exists(
        self,
        name: An[str, Doc("The package name (distribution name).")],
        version: An[str, Doc("The package version.")],
    ) -> An[bool, Doc("Whether the package version exists or not.")]:
        """Tell if a package version exists."""
        result = self._finder.find_best_match(f"{name}=={version}", allow_prereleases=True, allow_yanked=True)
        return bool(result.best)

    def upload(self, dists: An[Iterable[str | Path], Doc("The distributions to upload.")]) -> None:
        """Upload distributions."""
        with redirect_output_to_logging(stdout_level="debug"):
            upload(
                Settings(
                    non_interactive=True,
                    skip_existing=True,
                    repository_url=self.url,
                    username="",
                    password="",
                    disable_progress_bar=True,
                    verbose=True,
                ),
                [str(dist) for dist in dists],
            )
