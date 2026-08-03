from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeAlias

from pymax.api.binding import bind_api_model, bind_api_models
from pymax.api.response import (
    parse_payload_list,
    parse_payload_model,
    payload_item,
    require_payload_item_model,
    require_payload_model,
)
from pymax.api.uploads.payloads import (
    AttachFilePayload,
    AttachPhotoPayload,
    VideoAttachPayload,
)
from pymax.exceptions import UploadError
from pymax.files import File, Photo, Video, VideoNote, Voice
from pymax.formatting.markdown import Formatter
from pymax.logging import get_logger
from pymax.protocol import Opcode
from pymax.types.domain import (
    FileRequest,
    Message,
    Poll,
    ReactionInfo,
    ReadState,
    VideoRequest,
)

from .enums import ItemType, MessagePayloadKey, ReadAction
from .payloads import (
    AddReactionPayload,
    ChatHistoryPayload,
    DeleteMessagePayload,
    EditMessagePayload,
    ForwardLink,
    ForwardMessagePayload,
    ForwardMessagePayloadMessage,
    GetFilePayload,
    GetMessagesPayload,
    GetReactionsPayload,
    GetVideoPayload,
    PinMessagePayload,
    ReactionInfoPayload,
    ReadMessagesPayload,
    RemoveReactionPayload,
    ReplyLink,
    SendMessagePayload,
    SendMessagePayloadMessage,
)

if TYPE_CHECKING:
    from pymax.app import App

SendAttachment: TypeAlias = Photo | File | Video | Poll | Voice | VideoNote
SendAttachments: TypeAlias = Sequence[SendAttachment] | None

logger = get_logger(__name__)


class MessageService:
    def __init__(self, app: App) -> None:
        self.app = app

        self._prev = int(time.time() * 1000)

    def _next_cid(self) -> int:
        now = int(time.time() * 1000)
        e = max(now, self._prev + 1)
        self._prev = e
        logger.debug("generated message cid=%s", e)
        return e

    async def _upload_attachments(
        self, attachments: SendAttachments
    ) -> list[AttachPhotoPayload | VideoAttachPayload | AttachFilePayload | Poll]:
        result: list[AttachPhotoPayload | VideoAttachPayload | AttachFilePayload | Poll] = []
        if not attachments:
            return result

        for attachment in attachments:
            if isinstance(attachment, Voice):
                upload_result = await self.app.api.uploads.upload_voice(attachment)
                if not upload_result:
                    logger.error("Voice uploading failed")
                    raise UploadError("Voice uploading failed")

                result.append(upload_result)

            elif isinstance(attachment, Photo):
                upload_result = await self.app.api.uploads.upload_photo(attachment)
                if not upload_result:
                    logger.error("Photo uploading failed")
                    raise UploadError("Photo uploading failed")

                result.append(upload_result)

            elif isinstance(attachment, Video):
                upload_result = await self.app.api.uploads.upload_video(attachment)
                if not upload_result:
                    logger.error("Video uploading failed")
                    raise UploadError("Video uploading failed")

                result.append(upload_result)

            elif isinstance(attachment, File):
                upload_result = await self.app.api.uploads.upload_file(attachment)
                if not upload_result:
                    logger.error("File uploading failed")
                    raise UploadError("File uploading failed")

                result.append(upload_result)

            elif isinstance(attachment, Poll):
                result.append(attachment)

        return result

    async def send_message(
        self,
        chat_id: int,
        text: str | None = None,
        reply_to: int | None = None,
        attachments: SendAttachments = None,
        *,
        notify: bool = True,
    ) -> Message:
        logger.info("sending message chat_id=%s text_len=%s", chat_id, len(text) if text else 0)

        if not text and not attachments:
            logger.error("send_message failed: no text or attachments provided")
            raise ValueError("Either text or attachments must be provided")

        if text:
            clean_text, elements = Formatter.format_markdown(text)
        else:
            clean_text, elements = None, []

        frame = SendMessagePayload(
            chat_id=chat_id,
            message=SendMessagePayloadMessage(
                text=clean_text,
                cid=self._next_cid(),
                elements=elements,
                attaches=await self._upload_attachments(attachments),
                link=ReplyLink(message_id=reply_to) if reply_to else None,
            ),
            notify=notify,
        )

        response = await self.app.invoke(Opcode.MSG_SEND, frame.to_payload())

        message = bind_api_model(
            self.app,
            require_payload_model(response, Message),
        )
        logger.info("message sent chat_id=%s", chat_id)
        return message

    async def forward_message(
        self,
        chat_id: int,
        message_id: int | str,
        source_chat_id: int | None = None,
        *,
        notify: bool = True,
    ) -> Message:
        source_chat_id = chat_id if source_chat_id is None else source_chat_id
        logger.info(
            "forwarding message source_chat_id=%s chat_id=%s message_id=%s",
            source_chat_id,
            chat_id,
            message_id,
        )

        frame = ForwardMessagePayload(
            chat_id=chat_id,
            message=ForwardMessagePayloadMessage(
                cid=-self._next_cid(),
                link=ForwardLink(
                    message_id=str(message_id),
                    chat_id=source_chat_id,
                ),
            ),
            notify=notify,
        )

        response = await self.app.invoke(Opcode.MSG_SEND, frame.to_payload())
        message = bind_api_model(
            self.app,
            require_payload_model(response, Message),
        )
        logger.info("message forwarded source_chat_id=%s chat_id=%s", source_chat_id, chat_id)
        return message

    async def get_messages(
        self,
        chat_id: int,
        message_ids: list[int],
    ) -> list[Message]:
        frame = GetMessagesPayload(
            chat_id=chat_id,
            message_ids=message_ids,
        )

        response = await self.app.invoke(Opcode.MSG_GET, frame.to_payload())
        messages = parse_payload_list(response, MessagePayloadKey.MESSAGES, Message)
        for message in messages:
            if message.chat_id is None:
                message.chat_id = chat_id

        return bind_api_models(self.app, messages)

    async def get_message(
        self,
        chat_id: int,
        message_id: int,
    ) -> Message | None:
        messages = await self.get_messages(chat_id, [message_id])
        return messages[0] if messages else None

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str | None = None,
        attachments: SendAttachments = None,
    ) -> Message:
        if not text and not attachments:
            logger.error("edit_message failed: no text or attachments provided")
            raise ValueError("Either text or attachments must be provided")

        if text:
            clean_text, elements = Formatter.format_markdown(text)
        else:
            clean_text, elements = None, []

        frame = EditMessagePayload(
            chat_id=chat_id,
            message_id=message_id,
            text=clean_text,
            elements=elements,
            attachments=await self._upload_attachments(attachments),
        )

        response = await self.app.invoke(Opcode.MSG_EDIT, frame.to_payload())
        message = require_payload_item_model(
            response,
            MessagePayloadKey.MESSAGE,
            Message,
        )
        if message.chat_id is None:
            message.chat_id = chat_id

        return bind_api_model(self.app, message)

    async def fetch_history(
        self,
        chat_id: int,
        forward: int = 0,
        backward: int = 40,
        backward_time: int = 0,
        forward_time: int = 0,
        from_: int | None = None,
        item_type: ItemType = ItemType.REGULAR,
        get_chat: bool = False,
        get_messages: bool = True,
        interactive: bool = False,
    ) -> list[Message]:
        frame = ChatHistoryPayload(
            chat_id=chat_id,
            forward=forward,
            backward=backward,
            backward_time=backward_time,
            forward_time=forward_time,
            from_=from_ or int(time.time() * 1000),
            item_type=item_type,
            get_chat=get_chat,
            get_messages=get_messages,
            interactive=interactive,
        )

        response = await self.app.invoke(
            Opcode.CHAT_HISTORY,
            payload=frame.to_payload(),
        )
        messages = bind_api_models(
            self.app,
            parse_payload_list(response, MessagePayloadKey.MESSAGES, Message),
        )
        return messages

    async def delete_message(
        self,
        chat_id: int,
        message_ids: list[int],
        for_me: bool,
    ) -> bool:
        logger.info(
            "deleting messages chat_id=%s ids=%s for_me=%s",
            chat_id,
            message_ids,
            for_me,
        )
        frame = DeleteMessagePayload(
            chat_id=chat_id,
            message_ids=message_ids,
            for_me=for_me,
        )

        await self.app.invoke(Opcode.MSG_DELETE, frame.to_payload())
        logger.info("messages deleted chat_id=%s count=%s", chat_id, len(message_ids))
        return True

    async def pin_message(
        self,
        chat_id: int,
        message_id: int,
        notify_pin: bool,
    ) -> bool:
        logger.info(
            "pinning message chat_id=%s message_id=%s notify_pin=%s",
            chat_id,
            message_id,
            notify_pin,
        )
        frame = PinMessagePayload(
            chat_id=chat_id,
            notify_pin=notify_pin,
            pin_message_id=message_id,
        )

        await self.app.invoke(Opcode.CHAT_UPDATE, frame.to_payload())
        logger.info("message pinned chat_id=%s message_id=%s", chat_id, message_id)
        return True

    async def get_video_by_id(
        self,
        chat_id: int,
        message_id: int | str,
        video_id: int,
    ) -> VideoRequest | None:
        logger.info(
            "getting video chat_id=%s message_id=%s video_id=%s",
            chat_id,
            message_id,
            video_id,
        )
        frame = GetVideoPayload(
            chat_id=chat_id,
            message_id=message_id,
            video_id=video_id,
        )

        response = await self.app.invoke(Opcode.VIDEO_PLAY, frame.to_payload())
        return parse_payload_model(response, VideoRequest)

    async def get_file_by_id(
        self,
        chat_id: int,
        message_id: int | str,
        file_id: int,
    ) -> FileRequest | None:
        logger.info(
            "getting file chat_id=%s message_id=%s file_id=%s",
            chat_id,
            message_id,
            file_id,
        )
        frame = GetFilePayload(
            chat_id=chat_id,
            message_id=message_id,
            file_id=file_id,
        )

        response = await self.app.invoke(Opcode.FILE_DOWNLOAD, frame.to_payload())
        return parse_payload_model(response, FileRequest)

    async def add_reaction(
        self,
        chat_id: int,
        message_id: str,
        reaction: str,
    ) -> ReactionInfo | None:
        logger.info(
            "adding reaction chat_id=%s message_id=%s reaction=%s",
            chat_id,
            message_id,
            reaction,
        )
        frame = AddReactionPayload(
            chat_id=chat_id,
            message_id=message_id,
            reaction=ReactionInfoPayload(id=reaction),
        )

        response = await self.app.invoke(Opcode.MSG_REACTION, frame.to_payload())
        reaction_info = payload_item(response, MessagePayloadKey.REACTION_INFO)
        if reaction_info:
            return ReactionInfo.model_validate(reaction_info)

        return None

    async def get_reactions(
        self,
        chat_id: int,
        message_ids: list[str],
    ) -> dict[str, ReactionInfo] | None:
        logger.info(
            "getting reactions chat_id=%s message_ids=%s",
            chat_id,
            message_ids,
        )
        frame = GetReactionsPayload(chat_id=chat_id, message_ids=message_ids)

        response = await self.app.invoke(
            Opcode.MSG_GET_REACTIONS,
            frame.to_payload(),
        )
        messages_reactions = payload_item(
            response,
            MessagePayloadKey.MESSAGES_REACTIONS,
        )
        if messages_reactions is None:
            return None

        return {
            message_id: ReactionInfo.model_validate(reaction_data)
            for message_id, reaction_data in messages_reactions.items()
        }

    async def remove_reaction(
        self,
        chat_id: int,
        message_id: str,
    ) -> ReactionInfo | None:
        logger.info(
            "removing reaction chat_id=%s message_id=%s",
            chat_id,
            message_id,
        )
        frame = RemoveReactionPayload(chat_id=chat_id, message_id=message_id)

        response = await self.app.invoke(
            Opcode.MSG_CANCEL_REACTION,
            frame.to_payload(),
        )
        reaction_info = payload_item(response, MessagePayloadKey.REACTION_INFO)
        if reaction_info:
            return ReactionInfo.model_validate(reaction_info)

        return None

    async def read_message(self, message_id: int | str, chat_id: int) -> ReadState:
        logger.info(
            "marking message as read chat_id=%s message_id=%s",
            chat_id,
            message_id,
        )
        frame = ReadMessagesPayload(
            type=ReadAction.READ_MESSAGE,
            chat_id=chat_id,
            message_id=message_id,
            mark=int(time.time() * 1000),
        )

        response = await self.app.invoke(Opcode.CHAT_MARK, frame.to_payload())
        return require_payload_model(response, ReadState)
