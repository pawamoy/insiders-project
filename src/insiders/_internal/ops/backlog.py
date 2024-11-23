from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated as An

from loguru import logger
from typing_extensions import Doc

from insiders._internal.models import Backlog
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from insiders._internal.clients.github import GitHub
    from insiders._internal.clients.polar import Polar
    from insiders._internal.models import Sponsors

label_name = {
    "feature": "✨",
    "bug": "🐞",
    "docs": "📘",
    "insiders": "🔒",
}

label_color = {
    "feature": "#008672",
    "bug": "#B60205",
    "docs": "#1345ca",
    "insiders": "#008672",
}

def print_backlog(
    backlog: An[Backlog, Doc("The backlog to print.")],
    *,
    pledges: An[bool, Doc("Whether to print issue pledges.")] = True,
) -> None:
    """Print the backlog."""
    table = Table(title="Backlog")
    table.add_column("Issue", no_wrap=True)
    table.add_column("Author", no_wrap=True)
    table.add_column("Labels", no_wrap=False)
    table.add_column("Funding", no_wrap=True)
    if pledges:
        table.add_column("Pledged", no_wrap=True)
    table.add_column("Upvotes", no_wrap=True)
    table.add_column("Title")

    if pledges:
        for issue in backlog.issues:
            iid = f"{issue.repository}#{issue.number}"
            table.add_row(
                f"[link=https://github.com/{issue.repository}/issues/{issue.number}]{iid}[/link]",
                f"[link=https://github.com/{issue.author.name}]{issue.author.name}[/link]",
                "".join(f"[{label_color[label]}]{label_name[label]}[/]" for label in sorted(issue.labels)),
                f"💖{issue.funding}",
                f"💲{issue.pledged}",
                f"👍{len(issue.upvotes)}",
                issue.title,
            )
    else:
        for issue in backlog.issues:
            iid = f"{issue.repository}#{issue.number}"
            table.add_row(
                f"[link=https://github.com/{issue.repository}/issues/{issue.number}]{iid}[/link]",
                f"[link=https://github.com/{issue.author.name}]{issue.author.name}[/link]",
                "".join(f"[{label_color[label]}]{label_name[label]}[/]" for label in sorted(issue.labels)),
                f"💖{issue.funding}",
                f"👍{len(issue.upvotes)}",
                issue.title,
            )

    console = Console()
    console.print(table)


def get_backlog(
    github_namespaces: list[str],
    github: GitHub,
    polar: Polar | None = None,
    sponsors: Sponsors | None = None,
    issue_labels: set[str] | None = None,
) -> Backlog:
    github_users = [user for user in sponsors.grantees if user.platform == "github"] if sponsors else None

    github_issues = github.get_issues(github_namespaces, github_users, allow_labels=issue_labels)
    logger.debug(f"Got {len(github_issues)} issues from GitHub")

    if polar:
        polar_issues = polar.get_issues(github_namespaces, github_users)
        logger.debug(f"Got {len(polar_issues)} issues from Polar")
        for key, github_issue in github_issues.items():
            if key in polar_issues and (polar_issues[key].upvotes or polar_issues[key].pledged):
                github_issue.pledged = polar_issues[key].pledged

    return Backlog(issues=list(github_issues.values()))
