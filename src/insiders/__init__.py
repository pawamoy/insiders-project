"""insiders package.

Manage your Insiders projects.
"""

from __future__ import annotations

from insiders._internal.cli import main
from insiders._internal.clients.github import GitHub
from insiders._internal.clients.index import Index
from insiders._internal.clients.polar import Polar
from insiders._internal.models import Account, Backlog, Issue, IssueDict, Org, Sponsors, Sponsorship, User
from insiders._internal.ops.backlog import get_backlog, print_backlog

__all__: list[str] = [
    "GitHub",
    "Polar",
    "Account",
    "Issue",
    "IssueDict",
    "Org",
    "Sponsors",
    "Sponsorship",
    "User",
    "Backlog",
    "main",
    "Index",
    "get_backlog",
    "print_backlog",
]
