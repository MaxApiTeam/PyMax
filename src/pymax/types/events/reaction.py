from pydantic import Field

from pymax.types.domain.base import CamelModel
from pymax.types.domain.message import ReactionCounter


class ReactionUpdateEvent(CamelModel):
    """Событие обновления реакций сообщения.

    :ivar message_id: ID сообщения.
    :vartype message_id: str
    :ivar chat_id: ID чата.
    :vartype chat_id: int
    :ivar counters: Счетчики реакций по типам. Пусто, когда реакцию сняли —
        сервер шлёт ``NOTIF_MSG_REACTIONS_CHANGED`` (OP155) без ``counters``.
    :vartype counters: list[ReactionCounter]
    :ivar total_count: Общее количество реакций (0 при снятии последней).
    :vartype total_count: int
    """

    message_id: str
    chat_id: int
    counters: list[ReactionCounter] = Field(default_factory=list)
    total_count: int = 0
