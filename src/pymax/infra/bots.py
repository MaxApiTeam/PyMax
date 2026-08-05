from pymax.types import ButtonType, CallbackResponse
from pymax.types.domain import InitData

from .protocol import IClientProtocol


class BotsMixin(IClientProtocol):
    """Методы клиента для взаимодействия с ботами."""

    async def get_bot_init_data(
        self,
        bot_id: int,
        chat_id: int | None = None,
        start_param: str | None = None,
    ) -> InitData:
        """Получает начальные данные для запуска бота.

        Args:
            bot_id: Идентификатор бота.
            chat_id: Необязательный ID чата, в котором бот будет использоваться.
            start_param: Необязательный параметр, передаваемый при запуске
                бота.

        Returns:
            Объект с начальными данными для бота.

        Raises:
            RuntimeError: Если получение данных не удалось.
        """
        return await self._app.api.bots.get_init_data(
            bot_id=bot_id,
            chat_id=chat_id,
            start_param=start_param,
        )

    async def send_callback(
        self,
        callback_id: str,
        type: ButtonType,
        payload: str | None = None,
    ) -> CallbackResponse:
        return await self._app.api.bots.send_callback(callback_id, type, payload)
