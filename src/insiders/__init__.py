"""insiders package.

Manage your Insiders projects.
"""

from __future__ import annotations

from insiders._internal.cli import main
from insiders._internal.clients.github import GitHub
from insiders._internal.clients.index import Index
from insiders._internal.clients.polar import Polar
from insiders._internal.models import Account, Backlog, Issue, IssueDict, Sponsors, Sponsorship
from insiders._internal.ops.backlog import get_backlog, print_backlog
from insiders._internal.ops.report import update_numbers_file, update_sponsors_file
from insiders._internal.config import Config

__all__: list[str] = [
    "Account",
    "Backlog",
    "Config",
    "GitHub",
    "Index",
    "Issue",
    "IssueDict",
    "Polar",
    "Sponsors",
    "Sponsorship",
    "get_backlog",
    "main",
    "print_backlog",
    "update_numbers_file",
    "update_sponsors_file",
]
