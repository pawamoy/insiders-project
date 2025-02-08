from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated as An

from rich.console import Console
from rich.table import Table
from typing_extensions import Doc

from insiders._internal.models import Sponsors

if TYPE_CHECKING:
    from insiders._internal.models import Sponsors


def print_sponsors(
    sponsors: An[Sponsors, Doc("The sponsors to print.")],
    min_amount: An[int, Doc("The minimum amount for a sponsor to become an Insiders.")],
    limit: An[int, Doc("The maximum number of issues to print.")] = 0,
    *,
    sponsorships: An[bool, Doc("Whether to print the sponsorships as main column.")] = False,
) -> None:
    """Print the sponsors/sponsorships."""
    if sponsorships:
        table = Table(title=f"Sponsorships ({f'showing {limit} of ' if limit else ''}{len(sponsors.sponsorships)})")
        table.add_column("Platform", no_wrap=True)
        table.add_column("Account", no_wrap=True)
        table.add_column("Created", no_wrap=True)
        table.add_column("Public", no_wrap=True)
        table.add_column("Amount", no_wrap=True)
        table.add_column("Beneficiaries", no_wrap=True)

        for index, sponsorship in enumerate(
            sorted(sponsors.sponsorships, key=lambda s: (s.account.platform, s.account.name.lower())),
            1,
        ):
            account = f"@{sponsorship.account.name}"
            url = f"[link={sponsorship.account.url}]{account}[/link]" if sponsorship.account.url else account
            users = [
                f"- {'🗝️' if benef.grant and benef.user.highest_tier >= min_amount else ' '}  [link={benef.user.url}]{benef.user.name}[/link]"
                for benef in sorted(sponsorship.beneficiaries.values(), key=lambda b: b.user.name.lower())
            ]
            table.add_row(
                sponsorship.account.platform,
                url,
                sponsorship.created.strftime("%Y-%m-%d"),
                "" if sponsorship.private else "👁️",
                f"💲{sponsorship.amount}",
                "\n".join(users),
            )
            if index == limit:
                break

    else:
        beneficiaries = sponsors.beneficiaries
        table = Table(title=f"Sponsors ({f'showing {limit} of ' if limit else ''}{len(beneficiaries)} accounts)")
        table.add_column("User", no_wrap=True)
        table.add_column("Insider", no_wrap=True)
        table.add_column("Power", no_wrap=True)
        table.add_column("Sponsorships", no_wrap=True)

        for index, beneficiary in enumerate(sorted(beneficiaries.values(), key=lambda b: b.user.name.lower()), 1):
            user = beneficiary.user
            insider = beneficiary.grant and user.highest_tier >= min_amount
            url = f"[link={user.url}]{user.name}[/link]" if user.url else user.name
            linked_sponsorships = [
                f"- @{sp.account.name}@{sp.account.platform}: 💲{sp.amount}" for sp in user.sponsorships
            ]
            table.add_row(
                url,
                "🗝️" if insider else "",
                f"💪{user.tier_sum}",
                "\n".join(linked_sponsorships),
            )
            if index == limit:
                break

    console = Console()
    console.print(table)
