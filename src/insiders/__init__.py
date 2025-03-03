"""insiders package.

Manage your Insiders projects.
"""

from __future__ import annotations

from insiders._internal.cli import (
    CommandBacklog,
    CommandIndex,
    CommandIndexAdd,
    CommandIndexList,
    CommandIndexLogs,
    CommandIndexRemove,
    CommandIndexStart,
    CommandIndexStatus,
    CommandIndexStop,
    CommandIndexUpdate,
    CommandMain,
    CommandProject,
    CommandProjectCheck,
    CommandProjectCreate,
    CommandProjectPyPIRegister,
    CommandSponsors,
    CommandSponsorsList,
    CommandSponsorsShow,
    CommandSponsorsTeamList,
    CommandSponsorsTeamSync,
    main,
)
from insiders._internal.clients.github import GitHub
from insiders._internal.clients.index import Index
from insiders._internal.clients.polar import Polar
from insiders._internal.clients.pypi import reserve_pypi
from insiders._internal.config import Config, Unset, config_field
from insiders._internal.defaults import (
    DEFAULT_CONF_DIR,
    DEFAULT_CONF_PATH,
    DEFAULT_DIST_DIR,
    DEFAULT_INDEX_URL,
    DEFAULT_PORT,
    DEFAULT_REPO_DIR,
)
from insiders._internal.models import Account, Backlog, Beneficiary, Issue, Sponsors, Sponsorship, SponsorshipPlatform
from insiders._internal.ops.backlog import get_backlog, print_backlog
from insiders._internal.ops.projects import new_public_and_insiders_github_projects
from insiders._internal.ops.report import update_numbers_file, update_sponsors_file
from insiders._internal.ops.sponsors import print_sponsors

__all__: list[str] = [
    "DEFAULT_CONF_DIR",
    "DEFAULT_CONF_PATH",
    "DEFAULT_DIST_DIR",
    "DEFAULT_INDEX_URL",
    "DEFAULT_PORT",
    "DEFAULT_REPO_DIR",
    "Account",
    "Backlog",
    "Beneficiary",
    "CommandBacklog",
    "CommandIndex",
    "CommandIndexAdd",
    "CommandIndexList",
    "CommandIndexLogs",
    "CommandIndexRemove",
    "CommandIndexStart",
    "CommandIndexStatus",
    "CommandIndexStop",
    "CommandIndexUpdate",
    "CommandMain",
    "CommandProject",
    "CommandProjectCheck",
    "CommandProjectCreate",
    "CommandProjectPyPIRegister",
    "CommandSponsors",
    "CommandSponsorsList",
    "CommandSponsorsShow",
    "CommandSponsorsTeamList",
    "CommandSponsorsTeamSync",
    "Config",
    "GitHub",
    "Index",
    "Issue",
    "Polar",
    "Sponsors",
    "Sponsorship",
    "SponsorshipPlatform",
    "Unset",
    "config_field",
    "get_backlog",
    "main",
    "new_public_and_insiders_github_projects",
    "print_backlog",
    "print_sponsors",
    "reserve_pypi",
    "update_numbers_file",
    "update_sponsors_file",
]
