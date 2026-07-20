from typing import Literal

from pydantic import Field

from pymax.types.domain.base import CamelModel

from .enums import AttachmentType, PollFlags


class PollAnswer(CamelModel):
    """Вариант ответа в опросе.

    :ivar text: Текст варианта ответа.
    :vartype text: str
    :ivar answer_id: ID варианта, назначенный Max.
    :vartype answer_id: int | None
    """

    text: str
    answer_id: int | None = None


class PollVote(CamelModel):
    """Голос пользователя за один вариант ответа.

    :ivar timestamp: Время голосования в формате Unix time.
    :vartype timestamp: int
    :ivar user_id: ID проголосовавшего пользователя.
    :vartype user_id: int
    """

    timestamp: int
    user_id: int


class PollResult(CamelModel):
    """Результат голосования по одному варианту ответа.

    :ivar answer_id: ID варианта ответа.
    :vartype answer_id: int
    :ivar vote_count: Количество голосов.
    :vartype vote_count: int
    :ivar votes: Голоса пользователей, доступные текущему аккаунту.
    :vartype votes: list[PollVote]
    :ivar rate: Доля голосов в формате, возвращаемом Max.
    :vartype rate: int
    :ivar options: Дополнительные параметры результата от Max.
    :vartype options: int
    """

    answer_id: int
    vote_count: int
    votes: list[PollVote]
    rate: int
    options: int


class PollState(CamelModel):
    """Текущее состояние голосования.

    :ivar total: Общее количество голосов.
    :vartype total: int
    :ivar result: Результаты по вариантам ответа.
    :vartype result: list[PollResult] | None
    :ivar voter_preview_ids: ID пользователей для предпросмотра списка
        проголосовавших.
    :vartype voter_preview_ids: list[int]
    """

    total: int = 0
    result: list[PollResult] | None = None
    voter_preview_ids: list[int]


class Poll(CamelModel):
    """Опрос для отправки в сообщении.

    :ivar title: Вопрос или заголовок опроса.
    :vartype title: str
    :ivar answers: Варианты ответа.
    :vartype answers: list[PollAnswer]
    :ivar settings: Настройки опроса. Несколько ``PollFlags`` объединяются
        оператором ``|``.
    :vartype settings: PollFlags
    :ivar type: Тип вложения.
    :vartype type: Literal[AttachmentType.POLL]
    """

    title: str
    answers: list[PollAnswer]
    settings: PollFlags
    type: Literal[AttachmentType.POLL] = Field(alias="_type", default=AttachmentType.POLL)


class PollAttachment(Poll):
    """Опрос, полученный как вложение сообщения.

    Помимо параметров опроса содержит назначенный Max ID, версию и текущее
    состояние голосования.

    :ivar poll_id: ID опроса.
    :vartype poll_id: int
    :ivar version: Версия данных опроса.
    :vartype version: int
    :ivar state: Текущее состояние голосования.
    :vartype state: PollState
    """

    poll_id: int
    version: int
    state: PollState
