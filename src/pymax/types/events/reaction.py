from typing import Any

from pydantic import model_validator

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
    :ivar your_reaction: Реакция текущего пользователя, если она есть.
    :vartype your_reaction: str | None
    """

    message_id: int
    chat_id: int
    counters: list[ReactionCounter] | None = None
    total_count: int = 0
    your_reaction: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _unwrap_reaction_info(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        reaction_info = value.get("reactionInfo")
        if not isinstance(reaction_info, dict):
            return value

        data = value.copy()
        for field in ("counters", "totalCount", "yourReaction"):
            if field in reaction_info:
                data[field] = reaction_info[field]

        return data
