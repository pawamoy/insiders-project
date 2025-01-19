from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Annotated as An

import httpx
from typing_extensions import Doc

from insiders._internal.clients import Client
from insiders._internal.logger import logger
from insiders._internal.models import Issue, IssueDict, Org, Sponsors, Sponsorship, User

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


_GRAPHQL_SPONSORS_QUERY = """
query {
    viewer {
        sponsorshipsAsMaintainer(
            first: 100
            after: %s
            includePrivate: true
            orderBy: {
                field: CREATED_AT
                direction: DESC
            }
        )
        {
            pageInfo {
                hasNextPage
                endCursor
            }
            nodes {
                createdAt
                isOneTimePayment
                privacyLevel
                sponsorEntity {
                    ...on Actor {
                        __typename
                        login
                        avatarUrl
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

_GRAPHQL_ISSUES_QUERY = """
query {
    search(
        first: 100
        after: %(after)s
        query: "%(query)s"
        type: ISSUE
    )
    {
        pageInfo {
            hasNextPage
            endCursor
        }
        nodes {
            __typename
            ... on Issue {
                author {
                    login
                }
                title
                number
                repository {
                    nameWithOwner
                }
                createdAt
                labels(first: 10) {
                    nodes {
                        name
                    }
                }
                reactions(first: 100) {
                    nodes {
                        content
                        user {
                            login
                        }
                    }
                }
            }
        }
    }
}
"""


class GitHub(Client):
    """GitHub client."""

    name = "GitHub"

    def __init__(
        self,
        token: An[str, Doc("""A GitHub token. Recommended scopes: `admin:org` and `read:user`.""")],
    ) -> None:
        """Initialize GitHub API client."""
        self.http_client = httpx.Client(
            base_url="https://api.github.com",
            headers={"Authorization": f"Bearer {token}"},
        )

    def get_org_members(
        self,
        org: An[str, Doc("The organization name.")],
    ) -> An[set[str], Doc("A set of member names.")]:
        """Get organization members (username only)."""
        page = 1
        members = set()
        while True:
            response = self.http_client.get(f"/orgs/{org}/members", params={"per_page": 100, "page": page})
            response.raise_for_status()
            response_data = response.json()
            for member in response_data:
                members.add(member["login"])
            if len(response_data) < 100:  # noqa: PLR2004
                break
            page += 1
        return members

    def get_sponsors(
        self,
        org_members_map: An[
            Mapping[str, Iterable[str]] | None,
            Doc("A mapping of organization name to members."),
        ] = None,
        *,
        exclude_private: bool = False,
    ) -> An[Sponsors, Doc("Sponsors data.")]:
        """Get GitHub sponsors."""
        logger.debug("Fetching sponsors from GitHub.")
        sponsorships = []
        user_accounts = {}
        cursor = "null"

        while True:
            # Get sponsors data.
            logger.debug(f"Fetching page of sponsors from GitHub with cursor {cursor}.")
            payload = {"query": _GRAPHQL_SPONSORS_QUERY % cursor}
            response = self.http_client.post("/graphql", json=payload)
            response.raise_for_status()

            # Process sponsors data.
            data = response.json()["data"]
            for item in data["viewer"]["sponsorshipsAsMaintainer"]["nodes"]:
                if item["isOneTimePayment"]:
                    continue
                private = item["privacyLevel"].lower() == "private"
                if private and exclude_private:
                    continue

                # Determine account.
                account: User | Org
                account_data = {
                    "name": item["sponsorEntity"]["login"],
                    "image": item["sponsorEntity"]["avatarUrl"],
                    "url": item["sponsorEntity"]["url"],
                    "platform": "github",
                }
                if item["sponsorEntity"]["__typename"].lower() == "organization":
                    account = Org(**account_data)
                    logger.debug(f"Found org: @{account.name}")
                else:
                    account = User(**account_data)
                    logger.debug(f"Found user: @{account.name}")
                    user_accounts[account.name] = account

                # Record sponsorship.
                sponsorships.append(
                    Sponsorship(
                        private=private,
                        created=datetime.strptime(item["createdAt"], "%Y-%m-%dT%H:%M:%SZ"),  # noqa: DTZ007
                        amount=item["tier"]["monthlyPriceInDollars"],
                        account=account,
                    ),
                )

            # Check for next page.
            if data["viewer"]["sponsorshipsAsMaintainer"]["pageInfo"]["hasNextPage"]:
                cursor = f'"{data["viewer"]["sponsorshipsAsMaintainer"]["pageInfo"]["endCursor"]}"'
            else:
                break

        # Consolidate data.
        logger.debug(f"Processing {len(sponsorships)} sponsorships from GitHub.")
        for sponsorship in sponsorships:
            # Accounts link back to their sponsorship.
            sponsorship.account.sponsorships.append(sponsorship)
            # Add users as org members, link their org sponsorship.
            if sponsorship.account.is_org and org_members_map and sponsorship.account.name in org_members_map:
                org_members = org_members_map[sponsorship.account.name]
                actual_org_members = self.get_org_members(sponsorship.account.name)
                for org_member in org_members:
                    if org_member not in user_accounts:
                        user_accounts[org_member] = User(name=org_member, platform="github")
                    org_member_account = user_accounts[org_member]
                    verified = org_member in actual_org_members
                    sponsorship.account.users[org_member] = (org_member_account, verified)  # type: ignore[union-attr]
                    logger.debug(f"Found org member: @{sponsorship.account.name}/{org_member} (verified: {verified})")
                    org_member_account.sponsorships.append(sponsorship)

        return Sponsors(sponsorships=sponsorships)

    def get_team_members(
        self,
        org: An[str, Doc("The organization name.")],
        team: An[str, Doc("The team name.")],
    ) -> An[set[str], Doc("A set of member names.")]:
        """Get members of a GitHub team."""
        logger.debug(f"Fetching members of {org}/{team} team.")
        page = 1
        members = set()
        while True:
            response = self.http_client.get(f"/orgs/{org}/teams/{team}/members", params={"per_page": 100, "page": page})
            response.raise_for_status()
            response_data = response.json()
            members |= {member["login"] for member in response_data}
            if len(response_data) < 100:  # noqa: PLR2004
                break
            page += 1
        return members

    def get_team_invites(
        self,
        org: An[str, Doc("The organization name.")],
        team: An[str, Doc("The team name.")],
    ) -> An[set[str], Doc("A set of member names.")]:
        """Get pending invitations to a GitHub team."""
        logger.debug(f"Fetching pending invitations to {org}/{team} team.")
        page = 1
        invites = set()
        while True:
            response = self.http_client.get(f"/orgs/{org}/teams/{team}/invitations", params={"per_page": 100})
            response.raise_for_status()
            response_data = response.json()
            invites |= {invite["login"] for invite in response_data}
            if len(response_data) < 100:  # noqa: PLR2004
                break
            page += 1
        return invites

    def get_failed_invites(
        self,
        org: An[str, Doc("The organization name.")],
    ) -> An[set[str], Doc("A set of member names.")]:
        logger.debug(f"Fetching failed invitations to {org} organization.")
        page = 1
        invites = set()
        while True:
            response = self.http_client.get(f"/orgs/{org}/failed_invitations", params={"per_page": 100})
            response.raise_for_status()
            response_data = response.json()
            invites |= {invite["login"] for invite in response_data}
            if len(response_data) < 100:  # noqa: PLR2004
                break
            page += 1
        return invites

    def grant_access(
        self,
        user: An[str, Doc("A username.")],
        org: An[str, Doc("An organization name.")],
        team: An[str, Doc("A team name.")],
    ) -> None:
        """Grant access to a user to a GitHub team."""
        logger.debug(f"Granting @{user} access to {org}/{team} team.")
        response = self.http_client.put(f"/orgs/{org}/teams/{team}/memberships/{user}")
        response.raise_for_status()
        # try:
        #     response.raise_for_status()
        # except httpx.HTTPError as error:
        #     logger.error(f"Couldn't add @{user} to {org}/{team} team: {error}")
        #     if response.content:
        #         response_body = response.json()
        #         logger.error(f"{response_body['message']} See {response_body['documentation_url']}")
        # else:
        #     logger.info(f"@{user} added to {org}/{team} team")

    def revoke_access(
        self,
        user: An[str, Doc("A username.")],
        org: An[str, Doc("An organization name.")],
        team: An[str, Doc("A team name.")],
    ) -> None:
        """Revoke access from a user to a GitHub team."""
        logger.debug(f"Revoking access from @{user} to {org}/{team} team.")
        response = self.http_client.delete(f"/orgs/{org}/teams/{team}/memberships/{user}")
        response.raise_for_status()
        # try:
        #     response.raise_for_status()
        # except httpx.HTTPError as error:
        #     logger.error(f"Couldn't remove @{user} from {org}/{team} team: {error}")
        #     if response.content:
        #         response_body = response.json()
        #         logger.error(f"{response_body['message']} See {response_body['documentation_url']}")
        # else:
        #     logger.info(f"@{user} removed from {org}/{team} team")

    def get_issues(
        self,
        github_accounts: An[Iterable[str], Doc("A list of GitHub account names.")],
        known_github_users: An[Iterable[User] | None, Doc("Known user accounts.")] = None,
        *,
        allow_labels: An[set[str] | None, Doc("A set of labels to keep.")] = None,
    ) -> An[IssueDict, Doc("A dictionary of issues.")]:
        """Get issues from GitHub."""
        logger.debug("Fetching issues from GitHub.")

        known_users = {account.name: account for account in (known_github_users or ())}
        issues = {}
        allow_labels = allow_labels or set()
        cursor = "null"
        users_query = " ".join(f"user:{user}" for user in github_accounts)
        query = f"{users_query} sort:created state:open"

        while True:
            # Get issues data.
            logger.debug(f"Fetching page of issues from GitHub with cursor {cursor}.")
            payload = {"query": _GRAPHQL_ISSUES_QUERY % {"after": cursor, "query": query}}
            response = self.http_client.post("/graphql", json=payload)
            response.raise_for_status()

            # Process issues data.
            data = response.json()["data"]
            for issue in data["search"]["nodes"]:
                if issue["__typename"] != "Issue":
                    continue
                author_id = issue["author"]["login"].removesuffix("[bot]")
                repository = issue["repository"]["nameWithOwner"]
                title = issue["title"]
                number = issue["number"]
                created_at = datetime.strptime(issue["createdAt"], "%Y-%m-%dT%H:%M:%SZ")  # noqa: DTZ007
                labels = {label["name"] for label in issue["labels"]["nodes"] if label["name"] in allow_labels}

                if author_id not in known_users:
                    known_users[author_id] = User(name=author_id, platform="github")
                author = known_users[author_id]

                upvotes = set()
                for reaction in issue["reactions"]["nodes"]:
                    if reaction["content"] == "THUMBS_UP":
                        upvoter_id = reaction["user"]["login"]
                        if upvoter_id not in known_users:
                            known_users[upvoter_id] = User(name=upvoter_id, platform="github")
                        upvoter = known_users[upvoter_id]
                        upvotes.add(upvoter)

                iid = (repository, number)
                issues[iid] = Issue(
                    repository=repository,
                    number=number,
                    title=title,
                    created=created_at,
                    author=author,
                    upvotes=upvotes,
                    labels=labels,
                    platform="github",
                )

            # Check for next page.
            if data["search"]["pageInfo"]["hasNextPage"]:
                cursor = f'"{data["search"]["pageInfo"]["endCursor"]}"'
            else:
                break

        return issues

    def sync_team(
        self,
        team: An[str, Doc("GitHub team to sync sponsors with.")],
        *,
        sponsors: An[Sponsors | None, Doc("Sponsors data.")] = None,
        min_amount: An[int | None, Doc("Minimum amount to be considered a sponsor.")] = None,
        include_users: An[set[str] | None, Doc("Users to always grant access to.")] = None,
        exclude_users: An[set[str] | None, Doc("Users to never grant access to.")] = None,
        org_users: An[dict[str, set[str]] | None, Doc("Users to grant access to based on org.")] = None,
        dry_run: An[bool, Doc("Display changes without applying them.")] = False,
    ) -> None:
        """Sync sponsors with members of a GitHub team."""
        sponsors = sponsors or self.get_sponsors(org_users)

        eligible_users = {user.name for user in sponsors.users if not min_amount or user.tier_sum >= min_amount}
        if include_users:
            eligible_users |= include_users
        if exclude_users:
            eligible_users -= exclude_users

        org, team = team.split("/", 1)
        invitable_users = eligible_users - self.get_failed_invites(org)
        members = self.get_team_members(org, team) | self.get_team_invites(org, team)

        # Revoke accesses.
        for user in members:
            if user not in eligible_users:
                if dry_run:
                    logger.info(f"Would revoke access from @{user} to {org}/{team} team.")
                else:
                    self.revoke_access(user, org, team)

        # Grant accesses.
        for user in invitable_users:
            if user not in members:
                if dry_run:
                    logger.info(f"Would grant access to @{user} to {org}/{team} team.")
                else:
                    self.grant_access(user, org, team)

    def create_repo(
        self,
        repository: An[str, Doc("The repository, like `namespace/repo`.")],
        *,
        description: An[str | None, Doc("The repository description.")] = None,
        homepage: An[str | None, Doc("The repository homepage.")] = None,
        private: An[bool, Doc("Whether the repository is private.")] = False,
        has_issues: An[bool, Doc("Enable issues.")] = False,
        has_projects: An[bool, Doc("Enable projects.")] = False,
        has_wiki: An[bool, Doc("Enable the wiki.")] = False,
        has_discussions: An[bool, Doc("Enable discussions.")] = False,
    ) -> None:
        """Create a repository."""
        # NOTE: No way to create discussion categories via API.
        logger.debug(f"Creating repository {repository}.")

        # Determine account type.
        try:
            account, repo_name = repository.split("/")
        except ValueError:
            repo_name = repository
            url = "/user/repos"
        else:
            response = self.http_client.get(f"/users/{account}")
            response.raise_for_status()
            response_data = response.json()
            url = f"/orgs/{account}/repos" if response_data["type"] == "Organization" else "/user/repos"

        # Create the repository.
        response = self.http_client.post(
            url,
            params={
                "name": repo_name,
                "description": description,
                "homepage": homepage,
                "private": private,
                "has_issues": has_issues,
                "has_projects": has_projects,
                "has_wiki": has_wiki,
                "has_discussions": has_discussions,
            },
        )
        response.raise_for_status()
