from .base import CamelModel
from .chat import Chat
from .message import Message


class CallbackResponse(CamelModel):
    """Результат нажатия inline-кнопки бота.

    ``success`` показывает результат операции. Необязательные ``message`` и
    ``chat`` содержат дополнительные данные ответа Max и поддерживают методы
    действий, если ответ получен через клиент.
    """

    success: bool
    unread: int
    mark: int
    message: Message | None = None
    chat: Chat | None = None
    chat_access_token: str | None = None
