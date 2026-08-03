from pydantic import Field

from .base import CamelModel


class HandshakeResponse(CamelModel):
    """Результат рукопожатия.

    :ivar calls_seed: Сид для генерации хэшей вызовов.
    :vartype calls_seed: int
    """

    calls_seed: int | None = None
    app_update_type: int | None = Field(
        alias="app-update-type", default=None
    )  # very bizarre casing
