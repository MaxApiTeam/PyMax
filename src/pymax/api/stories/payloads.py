from pydantic import Field

from pymax.api.models import CamelModel
from pymax.api.uploads.payloads import AttachPhotoPayload, StoryVideoAttachPayload
from pymax.types.domain.story import StoryLayer, StoryOwner

from .enums import StoryStatsFilter


class SendStoryPayloadStory(CamelModel):
    cid: int
    media: AttachPhotoPayload | StoryVideoAttachPayload
    settings: int = 1
    expiration: int = 172_800_000
    layers: list[StoryLayer] = Field(default_factory=list)


class SendStoryPayload(CamelModel):
    stories: list[SendStoryPayloadStory]


class GetStoriesPayload(CamelModel):
    owners: list[StoryOwner]


class DeleteStoryPayload(CamelModel):
    story_ids: list[int]


class StoriesListPayload(CamelModel):
    cursor: str = "0"
    count: int = 15


class GetStoriesByIdPayload(CamelModel):
    owner: StoryOwner
    story_ids: list[int]


class GetStoryDetailedStatsPayload(CamelModel):
    story_id: int
    marker: int = 0
    filter: StoryStatsFilter


class MarkStoryPayload(CamelModel):
    owner: StoryOwner
    story_id: int


class EditStoryPayload(CamelModel):
    story_id: int
    settings: int


class StoryReactionPayload(CamelModel):
    reaction_type: int = 0
    id: str


class ReactStoryPayload(CamelModel):
    owner: StoryOwner
    story_id: int
    reaction: StoryReactionPayload | None = None
