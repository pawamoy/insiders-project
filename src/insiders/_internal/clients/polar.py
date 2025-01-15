from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Annotated as An

import httpx
from typing_extensions import Doc

from insiders._internal.clients import Client
from insiders._internal.logger import logger
from insiders._internal.models import Issue, Sponsors, Sponsorship, User

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from insiders._internal.models import IssueDict


class Polar(Client):
    """Polar client."""

    name = "Polar"

    def __init__(
        self,
        token: An[str, Doc("A Polar API token. Recommended scopes: `user:read`, `issues:read`, `subscriptions:read`.")],
    ) -> None:
        """Initialize Polar API client."""
        self.http_client = httpx.Client(
            base_url="https://api.polar.sh",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

    def get_sponsors(
        self,
        org_members_map: Mapping[str, Iterable[str]] | None = None,  # noqa: ARG002
        *,
        exclude_private: bool = False,  # noqa: ARG002
    ) -> An[Sponsors, Doc("Sponsors data.")]:
        """Get Polar sponsorships."""
        logger.debug("Fetching sponsors from Polar.")
        sponsorships = []
        page = 1
        items = []

        while True:
            logger.debug(f"Fetching page {page} of subscriptions from Polar.")
            response = self.http_client.get(
                "/v1/subscriptions/",
                params={
                    "active": True,
                    "sorting": "-started_at",  # To maintain order across pages.
                    "limit": 100,
                    "page": page,
                },
            )
            response.raise_for_status()
            data = response.json()
            items.extend(data["items"])
            if len(data["items"]) < 100:  # noqa: PLR2004
                break
            page += 1

        logger.debug(f"Processing {len(items)} subscriptions from Polar.")
        # Process sponsors data.
        for item in items:
            if not item["price"].get("price_amount"):
                continue

            # Determine account.
            account = User(
                name=item["user"]["public_name"],
                image=item["user"]["avatar_url"],
                url=f"https://polar.sh/{item['user']['public_name']}",
                platform="polar",
                platform_names={
                    "github": item["user"]["github_username"],
                },
            )
            logger.debug(f"Found user: @{account.name}")

            # Record sponsorship.
            sponsorships.append(
                Sponsorship(
                    private=False,
                    created=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"),  # noqa: DTZ007
                    amount=int(item["price"]["price_amount"] / 100),  # Polar stores in cents.
                    account=account,
                ),
            )

        return Sponsors(sponsorships=sponsorships)

    # Polar only supports fetching issues from GitHub for now.
    # Later, if it supports other platforms, we'll need to update this method.
    def get_issues(
        self,
        github_accounts: An[Iterable[str], Doc("GitHub accounts to fetch issues from.")],
        known_github_users: An[Iterable[User] | None, Doc("Known GitHub user accounts.")] = None,
    ) -> An[IssueDict, Doc("Issues data.")]:
        """Get issues from Polar."""
        page = 1
        items = []
        while True:
            logger.debug(f"Fetching page {page} of issues from Polar.")
            response = self.http_client.get(
                "/v1/issues/",
                params={
                    "external_organization_name": list(github_accounts),
                    "is_badged": True,
                    "sorting": "-created_at",  # To maintain order across pages.
                    "limit": 100,
                    "page": page,
                },
            )
            response.raise_for_status()
            data = response.json()
            items.extend(data["items"])
            if len(data["items"]) < 100:  # noqa: PLR2004
                break
            page += 1

        known_users = {account.name: account for account in (known_github_users or ())}
        issues = {}

        logger.debug(f"Processing {len(items)} issues from Polar.")
        for item in items:
            if item["state"] != "open":
                continue
            account_id = item["author"]["login"].removesuffix("[bot]")
            if account_id not in known_users:
                known_users[account_id] = User(name=account_id, platform="github")
            account = known_users[account_id]

            repository_name = f"{item['repository']['organization']['name']}/{item['repository']['name']}"
            iid = (repository_name, item["number"])
            issues[iid] = Issue(
                repository=repository_name,
                number=item["number"],
                title=item["title"],
                author=account,
                created=datetime.strptime(item["issue_created_at"], "%Y-%m-%dT%H:%M:%SZ"),  # noqa: DTZ007
                pledged=int(item["funding"]["pledges_sum"]["amount"] / 100),  # Polar stores in cents.
                platform="polar",
            )

        return issues
