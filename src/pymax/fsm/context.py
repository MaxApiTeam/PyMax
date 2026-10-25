from dataclasses import dataclass

from .protocol import FSMStorage


@dataclass(frozen=True, slots=True)
class FSMKey:
    client_id: int
    user_id: int
    chat_id: int


class FSMContext:
    """Контекст состояния пользователя в текущем чате.

    PyMax передает его в обязательный параметр обработчика сообщения
    с аннотацией ``FSMContext``. Состояние и данные доступны через ``storage``.

    Attributes:
        storage: Хранилище состояния и данных текущего контекста.
        key: Ключ контекста для текущих клиента, пользователя и чата.
    """

    def __init__(
        self,
        storage: FSMStorage,
        key: FSMKey,
    ) -> None:
        self.storage = storage
        self.key = key
