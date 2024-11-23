"""Sponsors management."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any, Callable, Literal
from typing import Annotated as An

from typing_extensions import Doc

if TYPE_CHECKING:
    from datetime import datetime


SponsorshipPlatform = An[Literal["github", "polar", "kofi"], Doc("The supported sponsorship platforms.")]
IssuePlatform = An[Literal["github", "polar"], Doc("The supported issue platforms.")]


@dataclass(kw_only=True, eq=False, frozen=True)
class Account:
    """An account."""

    name: An[str, Doc("The name of the account.")]
    image: An[str | None, Doc("The image URL of the account.")] = None
    url: An[str | None, Doc("The URL of the account.")] = None
    platform: An[SponsorshipPlatform, Doc("The platform of the account.")]
    sponsorships: An[
        list[Sponsorship],
        Doc("List of sponsorships associated with the account"),
    ] = field(default_factory=list)
    platform_names: An[
        dict[SponsorshipPlatform, str],
        Doc("Names of the account on different platforms."),
    ] = field(default_factory=dict)

    def __post_init__(self):
        self.platform_names[self.platform] = self.name

    def __eq__(self, other: An[object, Doc("The other object to compare to.")]) -> bool:
        if not isinstance(other, Account):
            return NotImplemented
        return self.platform == other.platform and self.name == other.name

    def __hash__(self):
        return hash((self.platform, self.name))

    @property
    def is_org(self) -> bool:
        """Return whether the account is an org."""
        return isinstance(self, Org)

    @property
    def is_user(self) -> bool:
        """Return whether the account is a user."""
        return isinstance(self, User)

    @property
    def direct_sponsor(self) -> bool:
        """Return whether the account is a direct sponsor."""
        return any(sponsorship.account is self for sponsorship in self.sponsorships)

    @property
    def highest_tier(self) -> int:
        """Return the highest tier amount."""
        return max((sponsorship.amount for sponsorship in self.sponsorships), default=0)

    @property
    def tier_sum(self) -> int:
        """Return the sum of all tier amounts."""
        return sum((sponsorship.amount for sponsorship in self.sponsorships), start=0)


@dataclass(kw_only=True, eq=False, frozen=True)
class User(Account):
    """A user account."""


@dataclass(kw_only=True, eq=False, frozen=True)
class Org(Account):
    """An org account."""

    users: An[dict[str, tuple[User, bool]], Doc("Users of this organization.")] = field(default_factory=dict)


@dataclass(kw_only=True, eq=False, frozen=True)
class Sponsorship:
    """A sponsorship."""

    private: An[bool, Doc("Indicates if the sponsorship is private")] = True
    created: An[datetime, Doc("The creation date of the sponsorship")]
    amount: An[int, Doc("The amount of the sponsorship")]
    account: An[User | Org, Doc("The user or org account associated with the sponsorship")]
    linked_accounts: An[dict[str, User | Org], Doc("Linked user accounts")] = field(default_factory=dict)

    def __eq__(self, other: An[object, Doc("The other object to compare to.")]) -> bool:
        if not isinstance(other, Sponsorship):
            return NotImplemented
        return self.account == other.account

    def __hash__(self):
        return hash(self.account)

    @property
    def users(self) -> set[User]:
        """Set of user accounts affected by this sponsorship."""
        users = set()
        for account in (self.account, *self.linked_accounts.values()):
            if isinstance(account, User):
                users.add(account)
            else:
                for user, _ in account.users.values():
                    users.add(user)
        return users


@dataclass(kw_only=True, eq=False, frozen=True)
class Sponsors:
    """Wrapper class for sponsorships."""

    sponsorships: An[list[Sponsorship], Doc("Sponsorships.")] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.crosslink(create_missing_users=False)

    def merge(self, other: Sponsors, *, crosslink: bool = True) -> Sponsors:
        self.sponsorships.extend(other.sponsorships)
        if crosslink:
            self.crosslink(create_missing_users=True)
        return self

    @property
    def users(self) -> set[User]:
        """Set of user accounts affected by all sponsorships."""
        return {user for sponsorship in self.sponsorships for user in sponsorship.users}

    def crosslink(self, *, create_missing_users: bool = False) -> None:
        users_by_platform: dict[str, dict[str, User]] = defaultdict(dict)
        for user in self.users:
            users_by_platform[user.platform][user.name] = user

        for sponsorship in self.sponsorships:
            for platform, name in sponsorship.account.platform_names.items():
                if platform != sponsorship.account.platform:
                    if name not in users_by_platform[platform]:
                        if not create_missing_users:
                            continue
                        # Create missing user.
                        users_by_platform[platform][name] = User(name=name, platform=platform)
                    user = users_by_platform[platform][name]
                    # Link sponsorship to user.
                    sponsorship.linked_accounts[platform] = user
                    # Link user to sponsorship.
                    if sponsorship not in user.sponsorships:
                        user.sponsorships.append(sponsorship)


@dataclass(kw_only=True, eq=False)
class Issue:
    """An issue."""

    repository: An[str, Doc("The issue repository.")]
    number: An[int, Doc("The issue number.")]
    title: An[str, Doc("The issue title.")]
    created: An[datetime, Doc("The issue creation date.")]
    author: An[User, Doc("The issue author.")]
    upvotes: An[set[User], Doc("The issue upvotes / upvoters.")] = field(default_factory=set)
    labels: An[set[str], Doc("The issue labels.")] = field(default_factory=set)
    pledged: An[int, Doc("The amount pledged.")] = 0
    platform: An[IssuePlatform, Doc("The issue platform.")]

    @property
    def interested_users(self) -> set[User]:
        return {self.author, *self.upvotes}

    @property
    def sponsorships(self) -> set[Sponsorship]:
        return {sponsorship for user in self.interested_users for sponsorship in user.sponsorships}

    @property
    def funding(self) -> int:
        return sum(sponsorship.amount for sponsorship in self.sponsorships)


IssueDict = An[dict[tuple[str, str], Issue], Doc("A dictionary of issues.")]


@dataclass(kw_only=True, eq=False, frozen=True)
class Backlog:
    """Backlog of issues."""

    issues: An[list[Issue], Doc("A list of issues.")] = field(default_factory=list)

    class SortStrategy:
        @staticmethod
        def min_author_sponsorships(amount: int, *, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * (issue.author.tier_sum if issue.author.tier_sum >= amount else 0)

        @staticmethod
        def author_sponsorships(*, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * issue.author.tier_sum

        @staticmethod
        def min_upvoters_sponsorships(amount: int, *, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * (
                total if (total := sum(upvoter.tier_sum for upvoter in issue.upvotes)) >= amount else 0
            )

        @staticmethod
        def upvoters_sponsorships(*, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * sum(upvoter.tier_sum for upvoter in issue.upvotes)

        @staticmethod
        def min_sponsorships(amount: int, *, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * (total if (total := issue.funding) >= amount else 0)

        @staticmethod
        def sponsorships(*, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * issue.funding

        @staticmethod
        def min_pledge(amount: int, *, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * (issue.pledged if issue.pledged >= amount else 0)

        @staticmethod
        def pledge(*, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * issue.pledged

        @staticmethod
        def min_upvotes(amount: int, *, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * (upvotes if (upvotes := len(issue.upvotes)) >= amount else 0)

        @staticmethod
        def upvotes(*, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * len(issue.upvotes)

        @staticmethod
        def created(*, reverse: bool = False) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * int(issue.created.timestamp())

        @staticmethod
        def label(name: str, *, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * (1 if name in issue.labels else 0)

        @staticmethod
        def repository(name: str, *, reverse: bool = True) -> Callable[[Issue], int]:
            factor = -1 if reverse else 1
            return lambda issue: factor * (1 if fnmatch(issue.repository, name) else 0)

    class _Sort:
        def __init__(self, *funcs: Callable[[Issue], Any]):
            self.funcs = list(funcs)

        def __call__(self, issue: Issue) -> tuple:
            return tuple(func(issue) for func in self.funcs)

    def sort(self, *strats: Callable[[Issue], Any]) -> None:
        """Sort the backlog."""
        self.issues.sort(key=self._Sort(*strats))
