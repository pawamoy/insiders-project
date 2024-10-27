"""Sync GitHub sponsors with GitHub teams."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from loguru import logger

from insiders.sponsors import Sponsor, get_github_sponsors

# TODO: Pass token through parameters instead of using global env var.
# permissions: admin:org and read:user
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# TODO: Maybe pass already instantiated client.
def get_github_team_members(org: str, team: str) -> set[str]:
    """Get members of a GitHub team."""
    page = 1
    members = set()
    while True:
        response = httpx.get(
            f"https://api.github.com/orgs/{org}/teams/{team}/members",
            params={"per_page": 100, "page": page},
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
        )
        response.raise_for_status()
        response_data = response.json()
        members |= {member["login"] for member in response_data}
        if len(response_data) < 100:  # noqa: PLR2004
            break
        page += 1
    return {user["login"] for user in response.json()}


# TODO: Maybe pass already instantiated client.
def get_github_team_invites(org: str, team: str) -> set[str]:
    """Get pending invitations to a GitHub team."""
    response = httpx.get(
        f"https://api.github.com/orgs/{org}/teams/{team}/invitations",
        params={"per_page": 100},
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
    )
    response.raise_for_status()
    return {user["login"] for user in response.json()}


# TODO: Maybe pass already instantiated client.
def grant_access_to_github_team(user: str, org: str, team: str) -> None:
    """Grant access to a user to a GitHub team."""
    with httpx.Client() as client:
        response = client.put(
            f"https://api.github.com/orgs/{org}/teams/{team}/memberships/{user}",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.error(f"Couldn't add @{user} to {org}/{team} team: {error}")
            if response.content:
                response_body = response.json()
                logger.error(f"{response_body['message']} See {response_body['documentation_url']}")
        else:
            logger.info(f"@{user} added to {org}/{team} team")


# TODO: Maybe pass already instantiated client.
def revoke_access_from_github_team(user: str, org: str, team: str) -> None:
    """Revoke access from a user to a GitHub team."""
    with httpx.Client() as client:
        response = client.delete(
            f"https://api.github.com/orgs/{org}/teams/{team}/memberships/{user}",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.error(f"Couldn't remove @{user} from {org}/{team} team: {error}")
            if response.content:
                response_body = response.json()
                logger.error(f"{response_body['message']} See {response_body['documentation_url']}")
        else:
            logger.info(f"@{user} removed from {org}/{team} team")


def sync_github_team(
    team: str,
    min_amount: int,
    privileged_users: set[str],
    org_users: dict[str, set[str]],
    token: str,
) -> list[Sponsor]:
    """Sync sponsors with members of a GitHub team."""
    sponsors = get_github_sponsors(token=token)

    eligible_orgs = {
        sponsor.account.name for sponsor in sponsors if sponsor.account.org and sponsor.amount >= min_amount
    }
    eligible_users = {
        sponsor.account.name for sponsor in sponsors if not sponsor.account.org and sponsor.amount >= min_amount
    }
    eligible_users |= privileged_users
    for eligible_org in eligible_orgs:
        eligible_users |= org_users.get(eligible_org, set())

    # TODO: Fetch org users from GitHub directly:
    # https://docs.github.com/en/rest/orgs/members?apiVersion=2022-11-28#list-organization-members.
    # If the org sponsors for $10 dollars, do nothing.
    # If the org sponsors for $50 dollars, and the org has more than 5 members, do nothing (can't decide).
    # If the org sponsors for $100 dollars, and the org has 10 or less members, add them to the team.

    org, team = team.split("/", 1)
    members = get_github_team_members(org, team) | get_github_team_invites(org, team)
    # revoke accesses
    for user in members:
        if user not in eligible_users:
            revoke_access_from_github_team(user, org, team)
    # grant accesses
    for user in eligible_users:
        if user not in members:
            grant_access_to_github_team(user, org, team)

    return sponsors


def update_numbers_file(sponsors: list[Sponsor], filepath: Path = Path("numbers.json")) -> None:
    """Update the file storing sponsorship numbers."""
    with filepath.open("w") as f:
        json.dump(
            {
                "total": sum(sponsor.amount for sponsor in sponsors),
                "count": len(sponsors),
            },
            f,
            indent=2,
        )


def update_sponsors_file(
    sponsors: list[Sponsor],
    filepath: Path = Path("sponsors.json"),
    *,
    exclude_private: bool = True,
) -> None:
    """Update the file storing sponsors info."""
    with filepath.open("w") as f:
        json.dump(
            [sponsor.account.as_dict() for sponsor in sponsors if not sponsor.private or not exclude_private],
            f,
            indent=2,
        )
