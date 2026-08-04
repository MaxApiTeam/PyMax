from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pymax.api.binding import bind_api_model
from pymax.api.response import (
    payload_item,
    require_payload_item,
    require_payload_item_model,
    require_payload_model,
)
from pymax.files import Photo
from pymax.logging import get_logger
from pymax.protocol import Opcode
from pymax.types.domain import FolderList, FolderUpdate, Profile

from .enums import SelfPayloadKey
from .payloads import (
    ChangeProfilePayload,
    ChangeProfileSettings,
    ChangeProfileSettingsPayload,
    CreateFolderPayload,
    DeleteFolderPayload,
    GetFolderPayload,
    PrivacySettingsUpdate,
    UpdateFolderPayload,
    UploadPayload,
)

if TYPE_CHECKING:
    from pymax.app import App


logger = get_logger(__name__)


class SelfService:
    def __init__(self, app: App) -> None:
        self.app = app

    async def request_profile_photo_upload_url(self) -> str:
        logger.info("requesting profile photo upload url")
        frame = UploadPayload(profile=True)
        response = await self.app.invoke(Opcode.PHOTO_UPLOAD, frame.to_payload())
        return str(require_payload_item(response, SelfPayloadKey.URL))

    async def change_profile(
        self,
        first_name: str,
        last_name: str | None = None,
        description: str | None = None,
        photo: Photo | None = None,
        *,
        photo_token: str | None = None,
    ) -> bool:
        if photo is not None:
            attach = await self.app.api.uploads.upload_photo(photo, profile=True)
            if photo_token:
                logger.warning(
                    "photo_token argument was provided but will be overridden by "
                    "the uploaded photo token"
                )

            photo_token = attach.photo_token

        frame = ChangeProfilePayload(
            first_name=first_name,
            last_name=last_name,
            description=description,
            photo_token=photo_token,
        )
        response = await self.app.invoke(Opcode.PROFILE, frame.to_payload())
        profile = bind_api_model(
            self.app,
            require_payload_item_model(
                response,
                SelfPayloadKey.PROFILE,
                Profile,
            ),
        )
        self.app.me = profile
        self.app.users[profile.contact.id] = profile.contact
        return True

    async def create_folder(
        self,
        title: str,
        chat_include: list[int],
        filters: list[Any] | None = None,
    ) -> FolderUpdate:
        logger.info("creating folder")
        frame = CreateFolderPayload(
            id=str(uuid4()),
            title=title,
            include=chat_include,
            filters=filters or [],
        )
        response = await self.app.invoke(Opcode.FOLDERS_UPDATE, frame.to_payload())
        return require_payload_model(response, FolderUpdate)

    async def get_folders(self, folder_sync: int = 0) -> FolderList:
        logger.info("fetching folders")
        frame = GetFolderPayload(folder_sync=folder_sync)
        response = await self.app.invoke(Opcode.FOLDERS_GET, frame.to_payload())
        return require_payload_model(response, FolderList)

    async def update_folder(
        self,
        folder_id: str,
        title: str,
        chat_include: list[int] | None = None,
        filters: list[Any] | None = None,
        options: list[Any] | None = None,
    ) -> FolderUpdate:
        logger.info("updating folder")
        frame = UpdateFolderPayload(
            id=folder_id,
            title=title,
            include=chat_include or [],
            filters=filters or [],
            options=options or [],
        )
        response = await self.app.invoke(Opcode.FOLDERS_UPDATE, frame.to_payload())
        return require_payload_model(response, FolderUpdate)

    async def delete_folder(self, folder_id: str) -> FolderUpdate:
        logger.info("deleting folder")
        frame = DeleteFolderPayload(folder_ids=[folder_id])
        response = await self.app.invoke(Opcode.FOLDERS_DELETE, frame.to_payload())
        return require_payload_model(response, FolderUpdate)

    async def close_all_sessions(self) -> bool:
        logger.info("closing all other sessions")

        if not self.app.session:
            logger.warning("no session found, skipping closing sessions")
            return False

        response = await self.app.invoke(Opcode.SESSIONS_CLOSE, {})
        token = payload_item(response, SelfPayloadKey.TOKEN, str)

        if not token:
            logger.warning("no token received after closing sessions, skipping token update")
            return False

        await self.app.store.update_token(self.app.session.token, token)
        self.app.session.token = token

        return True

    async def logout(self) -> bool:
        logger.info("logging out")
        await self.app.invoke(Opcode.LOGOUT, {})
        return True

    def set_presence(self, online: bool) -> None:
        logger.info("setting presence to %s", "online" if online else "offline")
        self.app.config.interactive = online

    async def change_profile_settings(self, settings: PrivacySettingsUpdate) -> bool:
        logger.info("changing profile settings")

        frame = ChangeProfileSettingsPayload(settings=ChangeProfileSettings(user=settings))

        response = await self.app.invoke(
            Opcode.CONFIG,
            frame.to_payload(),
        )
        session = self.app.session

        if not session:
            logger.warning("no session found, skipping sync update")
            return True

        sync = session.sync.model_copy(
            update={"config_hash": require_payload_item(response, SelfPayloadKey.HASH)}
        )

        updated = session.model_copy(
            update={
                "mt_instance_id": self.app.config.device.mt_instance_id,
                "sync": sync,
            },
        )
        self.app.session = updated
        await self.app.store.save_session(updated)

        return True
