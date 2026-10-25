from pymax.api.stories import StoryStatsFilter
from pymax.files import Photo, Video
from pymax.types.domain import Story, StoryDetailedStats, StoryPreview

from .protocol import IClientProtocol


class StoriesMixin(IClientProtocol):
    """Методы клиента для публикации, чтения и удаления сторис."""

    async def send_story(
        self,
        media: Photo | Video,
        *,
        duration: int | None = None,
        link: str | None = None,
    ) -> Story:
        """Публикует фото или видео в сторис на 48 часов.

        Args:
            media: Фото или видео. Принимает локальный файл, URL или байты
                через ``Photo`` или ``Video``.
            duration: Положительная длительность видео в миллисекундах.
                Обязательна для ``Video``; автоматически не определяется.
            link: Необязательная ссылка в нижней части кадра.

        Returns:
            Опубликованная сторис.

        Raises:
            ValueError: Если длительность видео не задана или неположительна.
            TypeError: Если передан неподдерживаемый тип медиа.
        """
        return await self._app.api.stories.send_story(
            media=media,
            duration=duration,
            link=link,
        )

    async def get_stories(self, owner_id: int, owner_type: int = 0) -> list[Story]:
        """Возвращает сторис указанного владельца.

        Args:
            owner_id: ID владельца, чьи сторис нужно получить.
            owner_type: Тип из ``StoryPreview.owner.type``. ``0`` — пользователь.

        Returns:
            Список сторис. Если сторис нет, возвращается пустой список.
        """
        return await self._app.api.stories.get_stories(owner_id=owner_id, owner_type=owner_type)

    async def delete_story(self, story_id: int) -> bool:
        """Удаляет сторис по ее ID.

        Args:
            story_id: ID удаляемой сторис.

        Returns:
            ``True``, если запрос завершился без API-ошибки.
        """
        return await self._app.api.stories.delete_story(story_id=story_id)

    async def get_stories_feed(
        self,
        cursor: str = "0",
        count: int = 15,
    ) -> tuple[list[StoryPreview], str]:
        """Возвращает страницу превью владельцев сторис.

        Превью не содержит ID отдельных сторис. Для их получения используйте
        ``get_stories(preview.owner.owner_id, preview.owner.type)``.

        Args:
            cursor: Курсор страницы. ``"0"`` запрашивает первую страницу.
            count: Количество превью в запрашиваемой странице.

        Returns:
            ``(previews, next_cursor)``. Передайте ``next_cursor`` в следующий
            вызов. Пустая строка означает, что дальше страниц нет.
        """
        return await self._app.api.stories.get_stories_feed(cursor=cursor, count=count)

    async def get_stories_by_id(
        self,
        owner_id: int,
        story_ids: list[int],
        owner_type: int = 0,
    ) -> list[Story]:
        """Возвращает конкретные сторис владельца по их ID.

        Args:
            owner_id: ID владельца сторис.
            story_ids: ID запрашиваемых сторис.
            owner_type: Тип из ``StoryPreview.owner.type``. ``0`` — пользователь.

        Returns:
            Список найденных сторис.
        """
        return await self._app.api.stories.get_stories_by_id(
            owner_id=owner_id,
            story_ids=story_ids,
            owner_type=owner_type,
        )

    async def get_story_detailed_stats(
        self,
        story_id: int,
        filter: StoryStatsFilter,
        marker: int = 0,
    ) -> tuple[list[StoryDetailedStats], int]:
        """Возвращает страницу подробной статистики сторис.

        Args:
            story_id: ID сторис.
            filter: ``StoryStatsFilter.VIEWS`` — просмотры,
                ``StoryStatsFilter.REACTIONS`` — реакции.
            marker: Маркер страницы. ``0`` запрашивает первую страницу.

        Returns:
            ``(stats, next_marker)``. Нулевой маркер означает конец списка.
        """
        return await self._app.api.stories.get_story_detailed_stats(
            story_id=story_id,
            filter=filter,
            marker=marker,
        )

    async def read_story(self, story_id: int, owner_id: int, owner_type: int = 0) -> bool:
        """Отмечает сторис просмотренной.

        Args:
            story_id: ID просмотренной сторис.
            owner_id: ID владельца сторис.
            owner_type: Тип из ``StoryPreview.owner.type``. ``0`` — пользователь.

        Returns:
            ``True``, если запрос завершился без API-ошибки.
        """
        return await self._app.api.stories.read_story(
            story_id=story_id,
            owner_id=owner_id,
            owner_type=owner_type,
        )

    async def edit_story(self, story_id: int, settings: int) -> Story:
        """Меняет настройки опубликованной сторис.

        Args:
            story_id: ID редактируемой сторис.
            settings: Битовая маска настроек в формате Max.

        Returns:
            Обновленная сторис.
        """
        return await self._app.api.stories.edit_story(story_id=story_id, settings=settings)

    async def add_story_reaction(
        self,
        owner_id: int,
        story_id: int,
        reaction: str,
        reaction_type: int = 0,
        owner_type: int = 0,
    ) -> bool:
        """Добавляет или заменяет свою реакцию на сторис.

        Args:
            owner_id: ID владельца сторис.
            story_id: ID сторис.
            reaction: Эмодзи или строковый ID реакции.
            reaction_type: ``0`` для эмодзи, ``1`` для реакции по ID.
            owner_type: Тип из ``StoryPreview.owner.type``. ``0`` — пользователь.

        Returns:
            Значение ``success`` из ответа Max.
        """
        return await self._app.api.stories.add_story_reaction(
            owner_id=owner_id,
            story_id=story_id,
            reaction=reaction,
            reaction_type=reaction_type,
            owner_type=owner_type,
        )

    async def remove_story_reaction(
        self,
        owner_id: int,
        story_id: int,
        owner_type: int = 0,
    ) -> bool:
        """Снимает свою реакцию со сторис.

        Args:
            owner_id: ID владельца сторис.
            story_id: ID сторис.
            owner_type: Тип из ``StoryPreview.owner.type``. ``0`` — пользователь.

        Returns:
            Значение ``success`` из ответа Max.
        """
        return await self._app.api.stories.remove_story_reaction(
            owner_id=owner_id,
            story_id=story_id,
            owner_type=owner_type,
        )
