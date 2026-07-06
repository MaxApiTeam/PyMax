from typing import Any

from pymax.types import FolderList, FolderUpdate

from .protocol import IClientProtocol


class SelfMixin(IClientProtocol):
    async def request_profile_photo_upload_url(self) -> str:
        """Запрашивает временный URL для загрузки фотографии профиля.

        Returns:
            URL, на который можно загрузить фото профиля.
        """
        return await self._app.api.account.request_profile_photo_upload_url()

    async def change_profile(
        self,
        first_name: str,
        last_name: str | None = None,
        description: str | None = None,
        photo: Any | None = None,
        *,
        photo_token: str | None = None,
    ) -> bool:
        """Обновляет профиль текущего аккаунта.

        Args:
            first_name: Имя профиля.
            last_name: Фамилия профиля.
            description: Описание профиля.
            photo: Файл или объект фото, который нужно загрузить как новую
                фотографию профиля.
            photo_token: Токен фотографии, уже загруженной через API Max.

        Returns:
            ``True`` после успешного обновления. Клиент также обновит
            ``client.me`` и кеш текущего контакта.
        """
        return await self._app.api.account.change_profile(
            first_name=first_name,
            last_name=last_name,
            description=description,
            photo=photo,
            photo_token=photo_token,
        )

    async def create_folder(
        self,
        title: str,
        chat_include: list[int],
        filters: list[Any] | None = None,
    ) -> FolderUpdate:
        """Создает папку чатов.

        Args:
            title: Название папки.
            chat_include: ID чатов, которые попадут в папку.
            filters: Дополнительные фильтры Max для папки.

        Returns:
            Обновленное состояние папок.
        """
        return await self._app.api.account.create_folder(
            title=title,
            chat_include=chat_include,
            filters=filters,
        )

    async def get_folders(self, folder_sync: int = 0) -> FolderList:
        """Возвращает папки текущего аккаунта.

        Args:
            folder_sync: Маркер синхронизации. Для первой загрузки оставьте
                ``0``.

        Returns:
            Список папок и актуальный маркер синхронизации.
        """
        return await self._app.api.account.get_folders(folder_sync=folder_sync)

    async def update_folder(
        self,
        folder_id: str,
        title: str,
        chat_include: list[int] | None = None,
        filters: list[Any] | None = None,
        options: list[Any] | None = None,
    ) -> FolderUpdate:
        """Обновляет папку чатов.

        Args:
            folder_id: ID папки.
            title: Новое название.
            chat_include: Новый список ID включенных чатов.
            filters: Новый список фильтров.
            options: Новый список опций.

        Returns:
            Обновленное состояние папок.
        """
        return await self._app.api.account.update_folder(
            folder_id=folder_id,
            title=title,
            chat_include=chat_include,
            filters=filters,
            options=options,
        )

    async def delete_folder(self, folder_id: str) -> FolderUpdate:
        """Удаляет папку чатов.

        Args:
            folder_id: ID папки.

        Returns:
            Обновленное состояние папок.
        """
        return await self._app.api.account.delete_folder(folder_id)

    async def close_all_sessions(self) -> bool:
        """Закрывает остальные активные сессии аккаунта.

        Returns:
            ``True``, если сервер принял запрос.
        """
        return await self._app.api.account.close_all_sessions()

    async def logout(self) -> bool:
        """Завершает текущую сессию клиента.

        Returns:
            ``True``, если сервер принял запрос на выход.
        """
        return await self._app.api.account.logout()

    def set_presence(self, online: bool) -> None:
        """Устанавливает статус присутствия текущего аккаунта. (Статус применяется не мгновенно, а при следущем login/ping)

        Args:
            online: ``True``, если нужно установить статус "в сети", иначе
                ``False``.
        """
        self._app.api.account.set_presence(online)
