from typing import Literal

from pydantic import Field

from pymax.api.models import CamelModel
from pymax.types.domain.attachments.enums import AttachmentType
from pymax.types.domain.enums import ChatType

from .enums import ChatMemberOperation, ChatOption, ControlEvent


class CreateGroupAttach(CamelModel):
    type: Literal[AttachmentType.CONTROL] = Field(
        default=AttachmentType.CONTROL,
        alias="_type",
    )
    event: ControlEvent = ControlEvent.NEW
    chat_type: Literal[ChatType.CHAT] = ChatType.CHAT
    title: str
    user_ids: list[int]


class CreateGroupMessage(CamelModel):
    cid: int
    attaches: list[CreateGroupAttach]


class CreateGroupPayload(CamelModel):
    message: CreateGroupMessage
    notify: bool = True


class InviteUsersPayload(CamelModel):
    chat_id: int
    user_ids: list[int]
    show_history: bool
    operation: ChatMemberOperation = ChatMemberOperation.ADD


class RemoveUsersPayload(CamelModel):
    chat_id: int
    user_ids: list[int]
    operation: ChatMemberOperation = ChatMemberOperation.REMOVE
    clean_msg_period: int


class ChangeGroupSettingsOptions(CamelModel):
    only_owner_can_change_icon_title: bool | None = Field(
        default=None,
        serialization_alias=ChatOption.ONLY_OWNER_CAN_CHANGE_ICON_TITLE.value,
    )
    all_can_pin_message: bool | None = Field(
        default=None,
        serialization_alias=ChatOption.ALL_CAN_PIN_MESSAGE.value,
    )
    only_admin_can_add_member: bool | None = Field(
        default=None,
        serialization_alias=ChatOption.ONLY_ADMIN_CAN_ADD_MEMBER.value,
    )
    only_admin_can_call: bool | None = Field(
        default=None,
        serialization_alias=ChatOption.ONLY_ADMIN_CAN_CALL.value,
    )
    members_can_see_private_link: bool | None = Field(
        default=None,
        serialization_alias=ChatOption.MEMBERS_CAN_SEE_PRIVATE_LINK.value,
    )


class ChangeGroupSettingsPayload(CamelModel):
    chat_id: int
    options: ChangeGroupSettingsOptions


class ChangeGroupProfilePayload(CamelModel):
    chat_id: int
    theme: str | None
    description: str | None = None


class JoinChatPayload(CamelModel):
    link: str


class LinkInfoPayload(CamelModel):
    link: str


class ReworkInviteLinkPayload(CamelModel):
    revoke_private_link: bool = True
    chat_id: int


class GetChatInfoPayload(CamelModel):
    chat_ids: list[int]


class GetChatMembersPayload(CamelModel):
    type: str = "MEMBER"  # TODO: ENUMM!!!
    chat_id: int
    marker: int
    count: int = 50


class LeaveChatPayload(CamelModel):
    chat_id: int


class FetchChatsPayload(CamelModel):
    marker: int


class FetchJoinRequests(CamelModel):
    chat_id: int
    type: str = "JOIN_REQUEST"  # ENUM!!!!!
    count: int = 100


class JoinRequestActionPayload(CamelModel):
    chat_id: int
    user_ids: list[int]
    type: str = "JOIN_REQUEST"  # TODO: ENUMM!!!
    show_history: bool | None = True
    operation: ChatMemberOperation


class DeleteChatPayload(CamelModel):
    chat_id: int
    last_event_time: int
    for_all: bool = True
