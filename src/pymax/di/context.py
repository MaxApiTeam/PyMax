from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from pymax.app import App
    from pymax.base import BaseClient
    from pymax.dispatch.mapping import DispatchEvent

ClientT = TypeVar("ClientT", bound="BaseClient")


@dataclass(slots=True)
class DiContext(Generic[ClientT]):
    app: App[ClientT]
    event: DispatchEvent
    client: ClientT
