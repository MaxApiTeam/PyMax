from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pymax.api.response import parse_payload_list, payload_item, require_payload_item_model
from pymax.api.uploads.payloads import AttachPhotoPayload, StoryVideoAttachPayload
from pymax.exceptions import PyMaxError
from pymax.files import Photo, Video
from pymax.logging import get_logger
from pymax.protocol import Opcode
from pymax.types.domain.story import (
    Story,
    StoryClickableLink,
    StoryCoordinates,
    StoryDetailedStats,
    StoryLayer,
    StoryOwner,
    StoryPreview,
)

from .enums import StoryPayloadKey, StoryStatsFilter
from .payloads import (
    DeleteStoryPayload,
    EditStoryPayload,
    GetStoriesByIdPayload,
    GetStoriesPayload,
    GetStoryDetailedStatsPayload,
    MarkStoryPayload,
    ReactStoryPayload,
    SendStoryPayload,
    SendStoryPayloadStory,
    StoriesListPayload,
    StoryReactionPayload,
)

if TYPE_CHECKING:
    from pymax.app import App


logger = get_logger(__name__)


class StoriesService:
    def __init__(self, app: App) -> None:
        self.app = app
        self._prev = int(time.time() * 1000)

    def _next_cid(self) -> int:
        now = int(time.time() * 1000)
        cid = max(now, self._prev + 1)
        self._prev = cid
        return cid

    async def send_story(
        self,
        media: Photo | Video,
        *,
        duration: int | None = None,
        link: str | None = None,
    ) -> Story:
        logger.info("sending story media_type=%s", type(media).__name__)

        attachment: AttachPhotoPayload | StoryVideoAttachPayload
        if isinstance(media, Photo):
            attachment = await self.app.api.uploads.upload_photo(media, upload_type=1)
        elif isinstance(media, Video):
            if duration is None or duration <= 0:
                raise ValueError("Video story duration must be greater than zero")
            attachment = await self.app.api.uploads.upload_story_video(media, duration)
        else:
            raise TypeError("Story media must be Photo or Video")

        layers: list[StoryLayer] = []
        if link is not None:
            layers.append(
                StoryLayer(
                    coordinates=StoryCoordinates(x=0.5, y=0.9, w=0.78, h=0.055),
                    clickable_link=StoryClickableLink(url=link),
                )
            )

        frame = SendStoryPayload(
            stories=[
                SendStoryPayloadStory(
                    cid=self._next_cid(),
                    media=attachment,
                    layers=layers,
                )
            ]
        )
        response = await self.app.invoke(Opcode.STORIES_SEND, frame.to_payload())
        stories = parse_payload_list(response, StoryPayloadKey.STORIES, Story)
        if not stories:
            raise PyMaxError("Story response does not contain a story")
        return stories[0]

    async def get_stories(self, owner_id: int, owner_type: int = 0) -> list[Story]:
        logger.info("getting stories owner_id=%s", owner_id)
        frame = GetStoriesPayload(owners=[StoryOwner(owner_id=owner_id, type=owner_type)])
        response = await self.app.invoke(Opcode.STORIES_GET_BY_OWNER_ID, frame.to_payload())
        peers = payload_item(response, StoryPayloadKey.PEER_STORIES) or []
        return [
            Story.model_validate(story) for peer in peers for story in peer.get("stories") or []
        ]

    async def delete_story(self, story_id: int) -> bool:
        logger.info("deleting story story_id=%s", story_id)
        frame = DeleteStoryPayload(story_ids=[story_id])
        await self.app.invoke(Opcode.STORIES_DELETE, frame.to_payload())
        return True

    async def get_stories_feed(
        self,
        cursor: str = "0",
        count: int = 15,
    ) -> tuple[list[StoryPreview], str]:
        logger.info("getting stories feed cursor=%s count=%s", cursor, count)
        frame = StoriesListPayload(cursor=cursor, count=count)
        response = await self.app.invoke(Opcode.STORIES_LIST, frame.to_payload())
        previews = parse_payload_list(response, StoryPayloadKey.STORIES_PREVIEWS, StoryPreview)
        next_cursor = payload_item(response, StoryPayloadKey.CURSOR, str) or ""
        return previews, next_cursor

    async def get_stories_by_id(
        self,
        owner_id: int,
        story_ids: list[int],
        owner_type: int = 0,
    ) -> list[Story]:
        logger.info("getting stories by id owner_id=%s count=%s", owner_id, len(story_ids))
        frame = GetStoriesByIdPayload(
            owner=StoryOwner(owner_id=owner_id, type=owner_type),
            story_ids=story_ids,
        )
        response = await self.app.invoke(Opcode.STORIES_GET_BY_STORY_ID, frame.to_payload())
        return parse_payload_list(response, StoryPayloadKey.STORIES, Story)

    async def get_story_detailed_stats(
        self,
        story_id: int,
        filter: StoryStatsFilter,
        marker: int = 0,
    ) -> tuple[list[StoryDetailedStats], int]:
        logger.info("getting story detailed stats story_id=%s marker=%s", story_id, marker)
        frame = GetStoryDetailedStatsPayload(story_id=story_id, filter=filter, marker=marker)
        response = await self.app.invoke(Opcode.STORIES_GET_DETAILED_STATS, frame.to_payload())
        stats = parse_payload_list(
            response, StoryPayloadKey.STORY_DETAILED_STATS, StoryDetailedStats
        )
        next_marker = payload_item(response, StoryPayloadKey.MARKER, int) or 0
        return stats, next_marker

    async def read_story(self, story_id: int, owner_id: int, owner_type: int = 0) -> bool:
        logger.info("marking story as read story_id=%s owner_id=%s", story_id, owner_id)
        frame = MarkStoryPayload(
            owner=StoryOwner(owner_id=owner_id, type=owner_type),
            story_id=story_id,
        )
        await self.app.invoke(Opcode.STORIES_MARK, frame.to_payload())
        return True

    async def edit_story(self, story_id: int, settings: int) -> Story:
        logger.info("editing story settings story_id=%s", story_id)
        frame = EditStoryPayload(story_id=story_id, settings=settings)
        response = await self.app.invoke(Opcode.STORIES_EDIT, frame.to_payload())
        return require_payload_item_model(response, StoryPayloadKey.STORY, Story)

    async def add_story_reaction(
        self,
        owner_id: int,
        story_id: int,
        reaction: str,
        reaction_type: int = 0,
        owner_type: int = 0,
    ) -> bool:
        logger.info("adding story reaction owner_id=%s story_id=%s", owner_id, story_id)
        frame = ReactStoryPayload(
            owner=StoryOwner(owner_id=owner_id, type=owner_type),
            story_id=story_id,
            reaction=StoryReactionPayload(reaction_type=reaction_type, id=reaction),
        )
        response = await self.app.invoke(Opcode.STORIES_REACT, frame.to_payload())
        return bool(payload_item(response, StoryPayloadKey.SUCCESS, bool))

    async def remove_story_reaction(
        self,
        owner_id: int,
        story_id: int,
        owner_type: int = 0,
    ) -> bool:
        logger.info("removing story reaction owner_id=%s story_id=%s", owner_id, story_id)
        frame = ReactStoryPayload(
            owner=StoryOwner(owner_id=owner_id, type=owner_type),
            story_id=story_id,
        )
        response = await self.app.invoke(Opcode.STORIES_REACT, frame.to_payload())
        return bool(payload_item(response, StoryPayloadKey.SUCCESS, bool))
