from __future__ import annotations

import time
from functools import reduce
from operator import or_
from typing import TYPE_CHECKING
from datetime import datetime, timedelta

from pymax.api.messages import DateTimeUnion

from pymax.api.binding import bind_api_model
from pymax.api.response import (
    parse_payload_item_model,
    parse_payload_list,
    payload_item,
    require_payload_item_model,
    require_payload_model,
)
from pymax.exceptions import PyMaxError
from pymax.files import Photo
from pymax.logging import get_logger
from pymax.protocol import Opcode
from pymax.types.domain import Chat, Member, Message

from .enums import ChannelPermissions, ChatLinkPrefix, ChatMemberOperation, ChatPayloadKey
from .payloads import (
    AddAdminPayload,
    ChangeGroupProfilePayload,
    ChangeGroupSettingsOptions,
    ChangeGroupSettingsPayload,
    CreateGroupAttach,
    CreateGroupMessage,
    CreateGroupPayload,
    DeleteChatPayload,
    FetchChatsPayload,
    FetchJoinRequests,
    GetChatInfoPayload,
    GetChatMembersPayload,
    InviteUsersPayload,
    JoinChatPayload,
    JoinRequestActionPayload,
    LeaveChatPayload,
    LinkInfoPayload,
    RemoveUsersPayload,
    ReworkInviteLinkPayload,
)

if TYPE_CHECKING:
    from pymax.app import App


logger = get_logger(__name__)


class ChatService:
    def __init__(self, app: App) -> None:
        self.app = app

    def _bind_chat(self, chat: Chat) -> Chat:
        return bind_api_model(self.app, chat)

    def _cache_chat(self, chat: Chat) -> Chat:
        chat = self._bind_chat(chat)
        if self.app.chats is None:
            self.app.chats = [chat]
            return chat

        for index, cached in enumerate(self.app.chats):
            if cached.id == chat.id:
                self.app.chats[index] = chat
                return chat

        self.app.chats.append(chat)
        return chat

    def _get_cached_chat(self, chat_id: int) -> Chat | None:
        for chat in self.app.chats or []:
            if chat.id == chat_id:
                return chat
        return None

    def _remove_cached_chat(self, chat_id: int) -> None:
        if self.app.chats is None:
            return

        self.app.chats = [chat for chat in self.app.chats if chat.id != chat_id]

    def _convert_period(self, period: DateTimeUnion) -> int:
        if isinstance(period, timedelta):
            return int(period.total_seconds())
        if isinstance(period, datetime):
            raise ValueError("Period cannot be a datetime")
        return int(period)

    def _convert_time(self, time_: DateTimeUnion) -> int:
        if isinstance(time_, datetime):
            return int(time_.timestamp() * 1000)
        if isinstance(time_, timedelta):
            return int((datetime.now() + time_).timestamp() * 1000)
        
    @staticmethod
    def _process_chat_join_link(link: str) -> str | None:
        idx = link.find(ChatLinkPrefix.JOIN)
        return link[idx:] if idx != -1 else None

    async def _join_chat(self, link: str) -> Chat:
        frame = JoinChatPayload(link=link)
        response = await self.app.invoke(Opcode.CHAT_JOIN, frame.to_payload())
        chat = require_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        return self._cache_chat(chat)

    async def create_group(
        self,
        name: str,
        participant_ids: list[int] | None = None,
        notify: bool = True,
    ) -> tuple[Chat, Message] | None:
        logger.info(
            "creating group name_len=%s participants=%s notify=%s",
            len(name),
            len(participant_ids or []),
            notify,
        )
        frame = CreateGroupPayload(
            message=CreateGroupMessage(
                cid=int(time.time() * 1000),
                attaches=[
                    CreateGroupAttach(
                        title=name,
                        user_ids=participant_ids or [],
                    )
                ],
            ),
            notify=notify,
        )

        response = await self.app.invoke(Opcode.MSG_SEND, frame.to_payload())
        chat = parse_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        if chat is None:
            return None

        chat = self._cache_chat(chat)
        message = bind_api_model(
            self.app,
            require_payload_model(response, Message),
        )
        return chat, message

    async def invite_users_to_group(
        self,
        chat_id: int,
        user_ids: list[int],
        show_history: bool = True,
    ) -> Chat | None:
        frame = InviteUsersPayload(
            chat_id=chat_id,
            user_ids=user_ids,
            show_history=show_history,
        )

        response = await self.app.invoke(
            Opcode.CHAT_MEMBERS_UPDATE,
            frame.to_payload(),
        )
        chat = parse_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        if chat:
            return self._cache_chat(chat)

        return None

    async def invite_users_to_channel(
        self,
        chat_id: int,
        user_ids: list[int],
        show_history: bool = True,
    ) -> Chat | None:
        return await self.invite_users_to_group(chat_id, user_ids, show_history)

    async def remove_users_from_group(
        self,
        chat_id: int,
        user_ids: list[int],
        clean_msg_period: DateTimeUnion,
    ) -> bool:
        frame = RemoveUsersPayload(
            chat_id=chat_id,
            user_ids=user_ids,
            clean_msg_period=self._convert_period(clean_msg_period),
        )

        response = await self.app.invoke(
            Opcode.CHAT_MEMBERS_UPDATE,
            frame.to_payload(),
        )
        chat = parse_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        if chat:
            self._cache_chat(chat)

        return True

    async def change_group_settings(
        self,
        chat_id: int,
        all_can_pin_message: bool | None = None,
        only_owner_can_change_icon_title: bool | None = None,
        only_admin_can_add_member: bool | None = None,
        only_admin_can_call: bool | None = None,
        members_can_see_private_link: bool | None = None,
    ) -> None:
        frame = ChangeGroupSettingsPayload(
            chat_id=chat_id,
            options=ChangeGroupSettingsOptions(
                all_can_pin_message=all_can_pin_message,
                only_owner_can_change_icon_title=only_owner_can_change_icon_title,
                only_admin_can_add_member=only_admin_can_add_member,
                only_admin_can_call=only_admin_can_call,
                members_can_see_private_link=members_can_see_private_link,
            ),
        )

        response = await self.app.invoke(Opcode.CHAT_UPDATE, frame.to_payload())
        chat = parse_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        if chat:
            self._cache_chat(chat)

    async def change_group_profile(
        self,
        chat_id: int,
        name: str | None,
        description: str | None = None,
        photo: Photo | None = None,
    ) -> None:

        frame = ChangeGroupProfilePayload(
            chat_id=chat_id,
            theme=name,
            description=description,
        )

        if photo:
            photo_payload = await self.app.api.uploads.upload_photo(photo)
            frame.photo_token = photo_payload.photo_token

        response = await self.app.invoke(Opcode.CHAT_UPDATE, frame.to_payload())
        chat = parse_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        if chat:
            self._cache_chat(chat)

    async def join_group(self, link: str) -> Chat:
        proceed_link = self._process_chat_join_link(link)
        if proceed_link is None:
            raise ValueError("Invalid group link")

        return await self._join_chat(proceed_link)

    async def join_channel(self, link: str) -> Chat:
        proceed_link = self._process_chat_join_link(link)

        return await self._join_chat(proceed_link or link)

    async def resolve_group_by_link(self, link: str) -> Chat | None:
        proceed_link = self._process_chat_join_link(link)
        if proceed_link is None:
            raise ValueError("Invalid group link")

        frame = LinkInfoPayload(link=proceed_link)
        response = await self.app.invoke(Opcode.LINK_INFO, frame.to_payload())
        chat = parse_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        if chat:
            return self._bind_chat(chat)

        return None

    async def rework_invite_link(self, chat_id: int) -> Chat:
        frame = ReworkInviteLinkPayload(chat_id=chat_id)
        response = await self.app.invoke(Opcode.CHAT_UPDATE, frame.to_payload())
        chat = require_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        return self._cache_chat(chat)

    async def get_chats(self, chat_ids: list[int]) -> list[Chat]:
        cached = {
            chat_id: chat
            for chat_id in chat_ids
            if (chat := self._get_cached_chat(chat_id)) is not None
        }
        missed_chat_ids = [chat_id for chat_id in chat_ids if chat_id not in cached]

        if missed_chat_ids:
            frame = GetChatInfoPayload(chat_ids=missed_chat_ids)
            response = await self.app.invoke(Opcode.CHAT_INFO, frame.to_payload())
            for chat in parse_payload_list(response, ChatPayloadKey.CHATS, Chat):
                chat = self._cache_chat(chat)
                cached[chat.id] = chat

        return [cached[chat_id] for chat_id in chat_ids if chat_id in cached]

    async def get_chat_members(
        self,
        chat_id: int,
        marker: int | None = None,
        count: int = 50,
    ) -> tuple[list[Member], int]:
        frame = GetChatMembersPayload(chat_id=chat_id, marker=marker or 0, count=count)
        response = await self.app.invoke(Opcode.CHAT_MEMBERS, frame.to_payload())

        members = bind_api_model(
            self.app,
            parse_payload_list(response, ChatPayloadKey.MEMBERS, Member),
        )
        next_marker = payload_item(response, ChatPayloadKey.MARKER, int) or 0
        return members, next_marker

    async def get_chat(self, chat_id: int) -> Chat:
        chats = await self.get_chats([chat_id])
        if not chats:
            raise PyMaxError("Chat not found in response")

        return chats[0]

    async def leave_group(self, chat_id: int) -> None:
        frame = LeaveChatPayload(chat_id=chat_id)
        await self.app.invoke(Opcode.CHAT_LEAVE, frame.to_payload())
        self._remove_cached_chat(chat_id)

    async def leave_channel(self, chat_id: int) -> None:
        await self.leave_group(chat_id)

    async def fetch_chats(self, marker: DateTimeUnion | None = None) -> list[Chat]:
        frame = FetchChatsPayload(
            marker=(
                self._convert_time(marker)
                if isinstance(marker, (datetime, timedelta))
                # Если marker=0, он будет перезаписан текущим временем (т.к. 0 расценивается как False). 
                # Чтобы это исправить, можно заменить на: else (int(marker) if marker is not None else int(time.time() * 1000))
                else (marker or int(time.time() * 1000))
            )
        )
        response = await self.app.invoke(Opcode.CHATS_LIST, frame.to_payload())

        chats = [
            self._cache_chat(chat)
            for chat in parse_payload_list(response, ChatPayloadKey.CHATS, Chat)
        ]
        return chats

    async def get_join_requests(self, chat_id: int, count: int = 100) -> list[Member]:
        frame = FetchJoinRequests(chat_id=chat_id, count=count)

        response = await self.app.invoke(Opcode.CHAT_MEMBERS, frame.to_payload())

        return bind_api_model(
            self.app,
            parse_payload_list(response, ChatPayloadKey.MEMBERS, Member),
        )

    async def confirm_join_requests(
        self,
        chat_id: int,
        user_ids: list[int],
        show_history: bool = True,
    ) -> Chat | None:
        frame = JoinRequestActionPayload(
            chat_id=chat_id,
            user_ids=user_ids,
            show_history=show_history,
            operation=ChatMemberOperation.ADD,
        )

        response = await self.app.invoke(Opcode.CHAT_MEMBERS_UPDATE, frame.to_payload())

        chat = parse_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        if chat:
            return self._cache_chat(chat)

        return None

    async def confirm_join_request(
        self,
        chat_id: int,
        user_id: int,
        show_history: bool = True,
    ) -> Chat | None:
        return await self.confirm_join_requests(
            chat_id=chat_id,
            user_ids=[user_id],
            show_history=show_history,
        )

    async def decline_join_requests(
        self,
        chat_id: int,
        user_ids: list[int],
    ) -> Chat | None:
        frame = JoinRequestActionPayload(
            chat_id=chat_id,
            user_ids=user_ids,
            show_history=None,
            operation=ChatMemberOperation.REMOVE,
        )

        response = await self.app.invoke(Opcode.CHAT_MEMBERS_UPDATE, frame.to_payload())

        chat = parse_payload_item_model(response, ChatPayloadKey.CHAT, Chat)
        if chat:
            return self._cache_chat(chat)

        return None

    async def decline_join_request(
        self,
        chat_id: int,
        user_id: int,
    ) -> Chat | None:
        return await self.decline_join_requests(
            chat_id=chat_id,
            user_ids=[user_id],
        )

    async def delete_chat(
        self,
        chat_id: int,
        last_event_time: DateTimeUnion | None = None,
        for_all: bool = True,
    ) -> None:
        frame = DeleteChatPayload(
            chat_id=chat_id,
            last_event_time=(
                self._convert_time(last_event_time)
                if isinstance(last_event_time, (datetime, timedelta))
                else (int(last_event_time) if last_event_time is not None else int(time.time() * 1000))
            ),
            for_all=for_all,
        )

        await self.app.invoke(Opcode.CHAT_DELETE, frame.to_payload())
        self._remove_cached_chat(chat_id)

    async def add_admin(
        self,
        chat_id: int,
        user_id: int,
        permissions: list[ChannelPermissions],
    ) -> None:
        frame = AddAdminPayload(
            chat_id=chat_id,
            user_ids=[user_id],
            permissions=reduce(or_, permissions),
        )

        await self.app.invoke(Opcode.CHAT_MEMBERS_UPDATE, frame.to_payload())
