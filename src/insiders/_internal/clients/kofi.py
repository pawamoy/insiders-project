from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated as An

import httpx
from typing_extensions import Doc

from insiders._internal.clients import Client

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from insiders._internal.models import Sponsors


class KoFi(Client):
    """Ko-fi client."""

    name = "Ko-fi"

    # NOTE: Ko-fi doesn't seem to provide an HTTP API, only webhooks...
    def __init__(self, token: An[str, Doc("A KoFi token.")]) -> None:  # noqa: ARG002
        """Initialize KoFi API client."""
        self.http_client = httpx.Client()

    def get_sponsors(
        self,
        org_members_map: Mapping[str, Iterable[str]] | None = None,
        *,
        exclude_private: bool = False,
    ) -> An[Sponsors, Doc("Sponsors data.")]:
        """Get Ko-fi sponsors."""
        raise NotImplementedError("Ko-fi support is not implemented yet")
