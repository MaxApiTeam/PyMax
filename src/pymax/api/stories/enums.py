from enum import Enum


class StoryStatsFilter(int, Enum):
    """Фильтр подробной статистики: просмотры (``0``) или реакции (``1``)."""

    VIEWS = 0
    REACTIONS = 1


class StoryPayloadKey(str, Enum):
    STORIES = "stories"
    PEER_STORIES = "peerStories"
    STORY = "story"
    STORIES_PREVIEWS = "storiesPreviews"
    CURSOR = "cursor"
    STORY_DETAILED_STATS = "storyDetailedStats"
    MARKER = "marker"
    SUCCESS = "success"
