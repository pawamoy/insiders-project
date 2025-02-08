from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated as An

from typing_extensions import Doc

if TYPE_CHECKING:
    from insiders._internal.models import Sponsorship


def update_numbers_file(
    sponsorships: An[list[Sponsorship], Doc("List of sponsorships.")],
    filepath: An[Path, Doc("File-path to update.")] = Path("numbers.json"),
) -> None:
    """Update the file storing sponsorship numbers."""
    with filepath.open("w") as f:
        json.dump(
            {
                "total": sum(sponsorship.amount for sponsorship in sponsorships),
                "count": len(sponsorships),
            },
            f,
            indent=2,
        )


def update_sponsors_file(
    sponsorships: An[list[Sponsorship], Doc("List of sponsorships.")],
    filepath: An[Path, Doc("File-path to update.")] = Path("sponsors.json"),
    *,
    exclude_private: An[bool, Doc("Whether to exclude private members.")] = True,
) -> None:
    """Update the file storing sponsors info."""
    with filepath.open("w") as f:
        json.dump(
            [
                {
                    "name": sponsorship.account.name,
                    "image": sponsorship.account.image,
                    "url": sponsorship.account.url,
                    "org": sponsorship.account.is_org,
                }
                for sponsorship in sponsorships
                if not sponsorship.private or not exclude_private
            ],
            f,
            indent=2,
        )
