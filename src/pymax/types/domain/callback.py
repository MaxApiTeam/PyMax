from .base import CamelModel
from .chat import Chat
from .message import Message


class CallbackResponse(CamelModel):
    success: bool
    unread: int
    mark: int
    message: Message | None = None
    chat: Chat | None = None
    chat_access_token: str | None = None
