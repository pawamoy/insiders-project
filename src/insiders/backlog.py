"""Backlog management."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

import httpx

if TYPE_CHECKING:
    from insiders.sponsors import Sponsor


@dataclass
class Issue:
    """An issue."""

    repository: str
    number: int
    title: str
    created: str
    author: str
    upvotes: int
    pledged: int


IssueDict = dict[tuple[str, str], Issue]


def get_github_issues() -> IssueDict:
    """Get issues from GitHub."""
    issues = {}
    items = json.loads(
        subprocess.getoutput(  # noqa: S605
            "gh search issues "  # noqa: S607
            "user:pawamoy org:mkdocstrings "
            "sort:created state:open "
            "--json repository,number,title,url,author,createdAt "
            "--limit 1000",
        ),
    )
    for item in items:
        iid = (item["repository"]["nameWithOwner"], item["number"])
        issues[iid] = Issue(
            repository=item["repository"]["nameWithOwner"],
            number=item["number"],
            title=item["title"],
            created=item["createdAt"],
            author=item["author"]["login"],
            upvotes=0,
            pledged=0,
        )
    return issues


def get_polar_issues(token: str, github_issues: IssueDict | None = None) -> IssueDict:
    """Get issues from Polar."""
    issues = github_issues if github_issues is not None else {}
    with httpx.Client() as client:
        page = 1
        while True:
            response = client.get(
                "https://api.polar.sh/v1/issues/",
                params={
                    "external_organization_name": ["pawamoy", "mkdocstrings"],
                    # "is_badged": True,
                    "sorting": "-created_at",
                    "limit": 100,
                    "page": page,
                },
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",  # Scope: issues:read, user:read.
                },
            )
            data = response.json()
            if not data["items"]:
                break
            page += 1
            for item in data["items"]:
                repository_name = f'{item["repository"]["organization"]["name"]}/{item["repository"]["name"]}'
                iid = (repository_name, item["number"])
                if iid in issues:  # GitHub issues are the source of truth.
                    issues[iid].upvotes = item["reactions"]["plus_one"]
                    issues[iid].pledged = int(item["funding"]["pledges_sum"]["amount"] / 100)
    return issues


class _Sort:
    def __init__(self, *funcs: Callable[[Issue], Any]):
        self.funcs = list(funcs)

    def add(self, func: Callable[[Issue], Any]) -> None:
        self.funcs.append(func)

    def __call__(self, issue: Issue) -> tuple:
        return tuple(func(issue) for func in self.funcs)


def get_backlog(
    sponsors: list[Sponsor] | None = None,
    min_tiers: int | None = None,
    min_pledge: int | None = None,
    polar_token: str | None = None,
) -> list[Issue]:
    """Get the backlog of issues."""
    _sort = _Sort()
    # TODO: Use max amount between user amount and their orgs' amounts.
    # Example: if user is a member of org1 and org2, and user amount is 10, org1 amount is 20, and org2 amount is 30,
    # then the user amount should be 30.
    sponsors_dict = {sponsor.account.name: sponsor for sponsor in (sponsors or ())}
    if sponsors is not None and min_tiers is not None:
        _sort.add(lambda issue: sp.amount if (sp := sponsors_dict.get(issue.author)) and sp.amount >= min_tiers else 0)
    elif sponsors is not None:
        _sort.add(lambda issue: sp.amount if (sp := sponsors_dict.get(issue.author)) else 0)
    if min_pledge is not None:
        _sort.add(lambda issue: issue.pledged if issue.pledged >= min_pledge else 0)
    else:
        _sort.add(lambda issue: issue.pledged)
    _sort.add(lambda issue: issue.upvotes)
    _sort.add(lambda issue: issue.created)

    issues = get_github_issues()
    if polar_token:
        issues = get_polar_issues(polar_token, issues)
    return sorted(issues.values(), key=_sort, reverse=True)


def print_backlog(backlog: list[Issue], *, pledges: bool = True, rich: bool = True) -> None:
    """Print the backlog."""
    if rich:
        from rich.console import Console
        from rich.table import Table

        table = Table(title="Backlog")
        table.add_column("Issue", style="underline", no_wrap=True)
        table.add_column("Author", no_wrap=True)
        if pledges:
            table.add_column("Pledged", justify="right", no_wrap=True)
        table.add_column("Upvotes", justify="right", no_wrap=True)
        table.add_column("Title")

        if pledges:
            for issue in backlog:
                iid = f"{issue.repository}#{issue.number}"
                table.add_row(
                    f"[link=https://github.com/{issue.repository}/issues/{issue.number}]{iid}[/link]",
                    f"[link=https://github.com/{issue.author}]{issue.author}[/link]",
                    f"💲{issue.pledged}",
                    f"👍{issue.upvotes}",
                    issue.title,
                )
        else:
            for issue in backlog:
                iid = f"{issue.repository}#{issue.number}"
                table.add_row(
                    f"[link=https://github.com/{issue.repository}/issues/{issue.number}]{iid}[/link]",
                    f"[link=https://github.com/{issue.author}]{issue.author}[/link]",
                    f"👍{issue.upvotes}",
                    issue.title,
                )

        console = Console()
        console.print(table)

    else:
        for issue in backlog:
            iid = f"{issue.repository}#{issue.number}"
            pledged = f"💲{issue.pledged} " if pledges else ""
            upvotes = f"👍{issue.upvotes}"
            pledged_upvotes = f"{pledged}{upvotes}"
            print(f"{iid:44}  {pledged_upvotes:12}  {issue.author:26}  {issue.title}")  # noqa: T201
