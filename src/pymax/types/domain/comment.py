from .base import CamelModel


class CommentsInfo(CamelModel):
    """Счетчики комментариев поста.

    :ivar total_count: Общее количество комментариев.
    :vartype total_count: int
    """

    total_count: int = 0


class CommentsInfoUpdate(CamelModel):
    """Обновление счетчиков комментариев поста.

    :ivar post_id: ID поста.
    :vartype post_id: int
    :ivar comments_info: Счетчики комментариев поста.
    :vartype comments_info: CommentsInfo
    """

    post_id: int
    comments_info: CommentsInfo | None
