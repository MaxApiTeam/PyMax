from pymax.types import Chat, Message

from .containers import ChatContainer, MessageContainer


class MagicFilter:
    @property
    def message(self) -> MessageContainer:
        return MessageContainer(Message)

    @property
    def chat(self) -> ChatContainer:
        return ChatContainer(Chat)
