from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, PrivateAttr

from .base import CamelModel
from .name import Name

if TYPE_CHECKING:
    from pymax.api.users.service import UserService


class ContactInfo(CamelModel):  # TODO: move to another file
    """Контакт телефонной книги для ``import_contacts``."""

    phone: str
    first_name: str
    last_name: str | None = None


class User(CamelModel):
    """Контакт или пользователь Max.

    :ivar id: ID пользователя.
    :vartype id: int
    :ivar account_status: Статус аккаунта в кодировке Max.
    :vartype account_status: int | None
    :ivar registration_time: Время регистрации в формате Unix time.
    :vartype registration_time: int | None
    :ivar country: Код страны пользователя.
    :vartype country: str | None
    :ivar base_raw_url: Исходный URL аватара.
    :vartype base_raw_url: str | None
    :ivar base_url: URL аватара.
    :vartype base_url: str | None
    :ivar names: Имена пользователя.
    :vartype names: list[Name]
    :ivar options: Дополнительные флаги контакта.
    :vartype options: list[str]
    :ivar photo_id: ID фотографии профиля.
    :vartype photo_id: int | None
    :ivar update_time: Время обновления в формате Unix time.
    :vartype update_time: int | None
    :ivar phone: Телефон пользователя, если возвращен API.
    :vartype phone: int | None
    :ivar status: Статус контакта, если возвращен API.
    :vartype status: str | None
    :ivar description: Описание профиля.
    :vartype description: str | None
    :ivar gender: Пол пользователя.
    :vartype gender: str | int | None
    :ivar link: Ссылка на профиль.
    :vartype link: str | None
    :ivar web_app: Данные связанного web-приложения, если есть.
    :vartype web_app: dict[str, Any] | str | None
    :ivar menu_button: Данные кнопки меню профиля, если есть.
    :vartype menu_button: dict[str, Any] | None
    """

    id: int
    account_status: int | None = None
    registration_time: int | None = None
    country: str | None = None
    base_raw_url: str | None = None
    base_url: str | None = None
    names: list[Name] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    photo_id: int | None = None
    update_time: int | None = None
    phone: int | None = None
    status: str | None = None
    description: str | None = None
    gender: str | int | None = None
    link: str | int | None = None
    web_app: dict[str, Any] | str | None = None
    menu_button: dict[str, Any] | None = None

    _actions: UserService | None = PrivateAttr(default=None)

    def bind(self, actions: UserService) -> "User":
        """Привязывает сервис пользователей к объекту пользователя."""
        self._actions = actions
        return self

    async def add_contact(self) -> "User":
        """Добавляет пользователя в контакты.

        Метод использует ID текущего пользователя и вызывает API через
        привязанный сервис пользователей.

        :raises RuntimeError: Если объект пользователя не привязан к клиенту.
        :return: Обновленный объект пользователя.
        :rtype: User
        """

        actions = self._bound()

        return await actions.add_contact(self.id)

    async def remove_contact(self) -> bool:
        """Удаляет пользователя из контактов.

        Метод использует ID текущего пользователя и вызывает API через
        привязанный сервис пользователей.

        :raises RuntimeError: Если объект пользователя не привязан к клиенту.
        :return: ``True``, если удаление прошло успешно.
        :rtype: bool
        """

        actions = self._bound()

        return await actions.remove_contact(self.id)

    def get_chat_id(self, user_id: int) -> int:
        """Возвращает ID личного чата между двумя пользователями.

        ID чата строится из ID переданного пользователя и ID текущего
        пользователя.

        :param user_id: ID второго пользователя.
        :type user_id: int
        :raises RuntimeError: Если объект пользователя не привязан к клиенту.
        :return: ID личного чата.
        :rtype: int
        """

        actions = self._bound()

        return actions.get_chat_id(user_id, self.id)

    def _bound(self) -> UserService:
        if self._actions is None:
            raise RuntimeError("Class is not bound to a client")

        return self._actions
