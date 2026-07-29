from .base import CamelModel


class HandshakeResponse(CamelModel):
    """Результат рукопожатия.

    :ivar calls_seed: Сид для генерации хэшей вызовов.
    :vartype calls_seed: int
    """

    calls_seed: int | None = None
