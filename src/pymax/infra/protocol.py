from typing import Protocol

from pymax.app import App


class IClientProtocol(Protocol):
    """Описывает минимальный клиент, нужный infra-миксинам."""

    @property
    def _app(self) -> App: ...

    @_app.setter
    def _app(self, value: App) -> None: ...
