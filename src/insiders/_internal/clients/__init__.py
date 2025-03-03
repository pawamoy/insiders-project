from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated as An

from typing_extensions import Doc, Self

if TYPE_CHECKING:
    from types import TracebackType

    import httpx

    from insiders._internal.models import Sponsors


class _Client:
    name: An[str, Doc("Name of the platform.")]
    http_client: An[httpx.Client, Doc("""An HTTPX client.""")]

    def __enter__(self) -> Self:
        self.http_client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        self.http_client.__exit__(exc_type, exc_value, traceback)

    def get_sponsors(self, *, exclude_private: bool = False) -> Sponsors:
        raise NotImplementedError("Not implemented")
