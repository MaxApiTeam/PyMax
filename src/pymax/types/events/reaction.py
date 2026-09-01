from pymax.types.domain.base import CamelModel
from pymax.types.domain.message import ReactionCounter


class ReactionUpdateEvent(CamelModel):
    """Событие обновления реакций сообщения.

    :ivar message_id: ID сообщения.
    :vartype message_id: int
    :ivar chat_id: ID чата.
    :vartype chat_id: int
    :ivar counters: Счетчики реакций по типам.
    :vartype counters: list[ReactionCounter]
    :ivar total_count: Общее количество реакций.
    :vartype total_count: int
    """

    message_id: int
    chat_id: int
    counters: list[ReactionCounter] | None = None
    total_count: int = 0
