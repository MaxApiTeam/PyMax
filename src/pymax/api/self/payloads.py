from typing import Any

from pydantic import BaseModel, Field

from pymax.api.models import CamelModel

from .enums import AvatarType, PrivacyAccess


class UploadPayload(CamelModel):
    count: int = 1
    profile: bool = False


class ChangeProfilePayload(CamelModel):
    first_name: str
    last_name: str | None = None
    description: str | None = None
    photo_token: str | None = None
    avatar_type: AvatarType = AvatarType.USER_AVATAR


class CreateFolderPayload(CamelModel):
    id: str
    title: str
    include: list[int]
    filters: list[Any]


class GetFolderPayload(CamelModel):
    folder_sync: int = 0


class UpdateFolderPayload(CamelModel):
    id: str
    title: str
    include: list[int]
    filters: list[Any]
    options: list[Any]


class DeleteFolderPayload(CamelModel):
    folder_ids: list[str]


class PrivacySettingsUpdate(BaseModel):
    """Изменяемые настройки приватности аккаунта.

    Все поля необязательны: в запрос попадают только переданные настройки.

    Args:
        search_by_phone: Кто может найти аккаунт по номеру телефона.
        incoming_calls: Кто может звонить аккаунту.
        chat_invites: Кто может добавлять аккаунт в чаты.
        phone_number_visibility: Кто может видеть номер телефона.
        hide_online_status: Скрывать ли статус присутствия.
        safe_content_only: Показывать только безопасный контент.
    """

    search_by_phone: PrivacyAccess | None = Field(
        default=None, serialization_alias="SEARCH_BY_PHONE"
    )
    incoming_calls: PrivacyAccess | None = Field(default=None, serialization_alias="INCOMING_CALL")
    chat_invites: PrivacyAccess | None = Field(default=None, serialization_alias="CHATS_INVITE")
    phone_number_visibility: PrivacyAccess | None = Field(
        default=None, serialization_alias="PHONE_NUMBER_PRIVACY"
    )

    hide_online_status: bool | None = Field(default=None, serialization_alias="HIDDEN")
    safe_content_only: bool | None = Field(
        default=None, serialization_alias="CONTENT_LEVEL_ACCESS"
    )


class ChangeProfileSettings(CamelModel):
    user: PrivacySettingsUpdate


class ChangeProfileSettingsPayload(CamelModel):
    settings: ChangeProfileSettings
