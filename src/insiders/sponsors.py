"""Sponsors management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import httpx

GRAPHQL_SPONSORS = """
query {
    viewer {
        sponsorshipsAsMaintainer(
        first: 100,
        after: %s
        includePrivate: true,
        orderBy: {
            field: CREATED_AT,
            direction: DESC
        }
        ) {
        pageInfo {
            hasNextPage
            endCursor
        }
        nodes {
            createdAt,
            isOneTimePayment,
            privacyLevel,
            sponsorEntity {
            ...on Actor {
                __typename,
                login,
                avatarUrl,
                url
            }
            },
            tier {
            monthlyPriceInDollars
            }
        }
        }
    }
}
"""

SupportedPlatform = Literal["github", "polar", "kofi", "patreon", "liberapay"]


@dataclass
class Account:
    """A sponsor account."""

    name: str
    image: str
    url: str
    org: bool
    platform: SupportedPlatform

    def as_dict(self) -> dict:
        """Return account as a dictionary."""
        return {
            "name": self.name,
            "image": self.image,
            "url": self.url,
            "org": self.org,
            "platform": self.platform,
        }


@dataclass
class Sponsor:
    """A sponsor."""

    account: Account
    private: bool
    created: datetime
    amount: int


def get_github_sponsors(token: str) -> list[Sponsor]:
    """Get GitHub sponsors."""
    sponsors = []
    with httpx.Client() as client:
        cursor = "null"
        while True:
            # Get sponsors data
            payload = {"query": GRAPHQL_SPONSORS % cursor}
            response = client.post(
                "https://api.github.com/graphql",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},  # Scope: admin:org, read:user.
            )
            response.raise_for_status()

            # Post-process sponsors data
            data = response.json()["data"]
            for item in data["viewer"]["sponsorshipsAsMaintainer"]["nodes"]:
                if item["isOneTimePayment"]:
                    continue

                # Determine account
                account = Account(
                    name=item["sponsorEntity"]["login"],
                    image=item["sponsorEntity"]["avatarUrl"],
                    url=item["sponsorEntity"]["url"],
                    org=item["sponsorEntity"]["__typename"].lower() == "organization",
                    platform="github",
                )

                # Add sponsor
                sponsors.append(
                    Sponsor(
                        account=account,
                        private=item["privacyLevel"].lower() == "private",
                        created=datetime.strptime(item["createdAt"], "%Y-%m-%dT%H:%M:%SZ"),  # noqa: DTZ007
                        amount=item["tier"]["monthlyPriceInDollars"],
                    ),
                )

            # Check for next page
            if data["viewer"]["sponsorshipsAsMaintainer"]["pageInfo"]["hasNextPage"]:
                cursor = f'"{data["viewer"]["sponsorshipsAsMaintainer"]["pageInfo"]["endCursor"]}"'
            else:
                break

    return sponsors


def get_polar_sponsors() -> list[Sponsor]:
    """Get Polar sponsors."""
    raise NotImplementedError("Polar support is not implemented yet")


def get_kofi_sponsors() -> list[Sponsor]:
    """Get Ko-fi sponsors."""
    raise NotImplementedError("Ko-fi support is not implemented yet")


def get_patreon_sponsors() -> list[Sponsor]:
    """Get Patreon sponsors."""
    raise NotImplementedError("Patreon support is not implemented yet")


def get_liberapay_sponsors() -> list[Sponsor]:
    """Get Liberapay sponsors."""
    raise NotImplementedError("Liberapay support is not implemented yet")
