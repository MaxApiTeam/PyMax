from __future__ import annotations

import asyncio
import base64
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, quote, urlparse

import aiohttp
from pydantic import ValidationError

from pymax.api.response import payload_item
from pymax.dispatch.enums import EventType
from pymax.exceptions import UploadError
from pymax.files import File, Photo, Video, VideoNote, Voice
from pymax.logging import get_logger
from pymax.protocol import Opcode
from pymax.types import AttachmentType, AudioUploadSignal

from .models import (
    FileUploadResponse,
    PhotoUploadResponse,
    VideoUploadResponse,
)
from .payloads import (
    AttachFilePayload,
    AttachPhotoPayload,
    UploadPayload,
    VideoAttachPayload,
)

if TYPE_CHECKING:
    from pymax import Client
    from pymax.app import App
    from pymax.types.events import FileUploadSignal, VideoUploadSignal

logger = get_logger(__name__)


class UploadService:
    def __init__(self, app: App) -> None:
        self.app = app
        self.video_upload_waiters: dict[int, asyncio.Future[VideoUploadSignal]] = {}
        self.file_upload_waiters: dict[int, asyncio.Future[FileUploadSignal]] = {}
        self.voice_upload_waiters: dict[int, asyncio.Future[AudioUploadSignal]] = {}
        self.app.dispatcher.on_internal(EventType.VIDEO_READY)(self.on_video_attach)
        self.app.dispatcher.on_internal(EventType.FILE_READY)(self.on_file_attach)
        self.app.dispatcher.on_internal(EventType.VOICE_READY)(self.on_voice_attach)

    async def upload_photo(self, photo: Photo, profile: bool = False) -> AttachPhotoPayload:
        logger.info("Uploading photo")
        logger.debug("Preparing photo upload payload")

        payload = UploadPayload(profile=profile).to_payload()

        try:
            data = await self.app.invoke(
                Opcode.PHOTO_UPLOAD,
                payload=payload,
            )
        except Exception as e:
            logger.exception("Failed to request photo upload URL")
            raise UploadError("Failed to request photo upload URL") from e

        try:
            url = payload_item(data, "url", str)  # TODO: ENUM!!!!
        except Exception as e:
            logger.exception("Failed to parse photo upload URL from response")
            raise UploadError("Failed to parse photo upload URL from response") from e

        if not url:
            logger.error("No upload URL received")
            logger.debug(
                "Photo upload URL response payload=%r",
                getattr(data, "payload", None),
            )
            raise UploadError("No upload URL received")

        logger.debug("Photo upload URL received")

        try:
            parsed_url = urlparse(url)
            photo_id = str(parse_qs(parsed_url.query)["photoIds"][0])
        except (KeyError, IndexError) as e:
            logger.exception("Photo upload URL does not contain photoIds")
            logger.debug("Invalid photo upload URL=%s", url)
            raise UploadError("Photo upload URL does not contain photoIds") from e
        except Exception as e:
            logger.exception("Failed to parse photo id from upload URL")
            logger.debug("Invalid photo upload URL=%s", url)
            raise UploadError("Failed to parse photo id from upload URL") from e

        logger.debug("Photo upload id parsed photo_id=%s", photo_id)

        try:
            photo_data = photo.validate_photo()
        except Exception as e:
            logger.exception("Photo validation crashed")
            raise UploadError("Photo validation crashed") from e

        if not photo_data:
            logger.error("Photo validation failed")
            raise UploadError("Photo validation failed")

        logger.debug(
            "Photo validated extension=%s content_type=%s",
            photo_data[0],
            photo_data[1],
        )

        try:
            photo_bytes = await photo.read()
        except Exception as e:
            logger.exception("Failed to read photo bytes")
            raise UploadError("Failed to read photo bytes") from e

        logger.debug("Photo read complete size=%s", len(photo_bytes))

        form = aiohttp.FormData()
        form.add_field(
            name="file",
            value=photo_bytes,
            filename=f"image.{quote(photo_data[0])}",
            content_type=photo_data[1],
        )

        try:
            async with (
                aiohttp.ClientSession(proxy=self.app.config.proxy) as session,
                session.post(
                    url=url,
                    data=form,
                ) as response,
            ):
                logger.debug("Photo upload HTTP response status=%s", response.status)

                if response.status != HTTPStatus.OK:
                    logger.error("Photo upload failed with status %s", response.status)
                    raise UploadError(f"Photo upload failed with status {response.status}")

                try:
                    result = await response.json()
                except Exception as e:
                    logger.exception("Failed to decode photo upload response JSON")
                    raise UploadError("Failed to decode photo upload response JSON") from e

        except UploadError:
            raise
        except aiohttp.ClientError as e:
            logger.exception("HTTP error during photo upload")
            raise UploadError("HTTP error during photo upload") from e
        except asyncio.TimeoutError as e:
            logger.exception("Timed out during photo upload")
            raise UploadError("Timed out during photo upload") from e
        except Exception as e:
            logger.exception("Unexpected error during photo upload")
            raise UploadError("Unexpected error during photo upload") from e

        try:
            model = PhotoUploadResponse.model_validate(result)
        except ValidationError as e:
            logger.exception("Invalid photo upload response model")
            logger.debug("Invalid photo upload response=%r", result)
            raise UploadError("Invalid photo upload response model") from e

        try:
            token = model.photos[photo_id].token
        except KeyError as e:
            logger.exception(
                "Photo upload response does not contain token for photo_id=%s",
                photo_id,
            )
            logger.debug("Photo upload model=%r", model)
            raise UploadError(
                f"Photo upload response does not contain token for photo_id={photo_id}"
            ) from e
        except Exception as e:
            logger.exception("Failed to extract photo token")
            logger.debug("Photo upload model=%r", model)
            raise UploadError("Failed to extract photo token") from e

        logger.debug("Photo upload complete photo_id=%s", photo_id)
        return AttachPhotoPayload(photo_token=token)

    async def upload_voice(self, voice: Voice) -> VideoAttachPayload:
        logger.info("Uploading voice")

        payload = UploadPayload(
            type=2,
            uploader_type=1,
        ).to_payload()

        try:
            data = await self.app.invoke(
                Opcode.VIDEO_UPLOAD,
                payload=payload,
            )
        except Exception as e:
            logger.exception("Failed to request voice upload URL")
            raise UploadError("Failed to request voice upload URL") from e

        try:
            response = VideoUploadResponse.model_validate(data.payload)
        except ValidationError as e:
            logger.exception("Invalid voice upload response model")
            logger.debug("Invalid voice upload payload=%r", data.payload)
            raise UploadError("Invalid voice upload response model") from e
        except Exception as e:
            logger.exception("Failed to parse voice upload response")
            logger.debug("Invalid voice upload payload=%r", data.payload)
            raise UploadError("Failed to parse voice upload response") from e

        try:
            upload_info = response.info[0]
        except IndexError as e:
            logger.error("voice upload response info is empty")
            logger.debug("voice upload response=%r", response)
            raise UploadError("voice upload response info is empty") from e
        except Exception as e:
            logger.exception("Failed to get voice upload info")
            logger.debug("voice upload response=%r", response)
            raise UploadError("Failed to get voice upload info") from e

        try:
            file_size = await voice.size()
        except Exception as e:
            logger.exception("Failed to get voice size")
            raise UploadError("Failed to get voice size") from e

        headers = {
            "Content-Disposition": f"attachment; filename={quote(voice.name)}",
            "Content-Range": f"0-{file_size - 1}/{file_size}",
            "Content-Length": str(file_size),
            "Connection": "keep-alive",
            "Content-Type": "application/octet-stream",
        }

        logger.debug(
            "Voice upload headers prepared content_range=%s",
            headers["Content-Range"],
        )

        loop = asyncio.get_running_loop()
        future: asyncio.Future[AudioUploadSignal] = loop.create_future()

        timeout = aiohttp.ClientTimeout(total=900, sock_read=60)

        video_id = upload_info.video_id
        token = upload_info.token

        self.voice_upload_waiters[video_id] = future
        logger.debug("Voice upload waiter registered voice_id=%s", video_id)

        try:
            async with aiohttp.ClientSession(
                timeout=timeout, proxy=self.app.config.proxy
            ) as session:
                logger.debug("Starting voice upload HTTP request voice_id=%s", video_id)

                async with session.post(
                    url=upload_info.url,
                    headers=headers,
                    data=voice.iter_chunks(1024 * 1024),
                ) as response:
                    logger.debug(
                        "Voice upload HTTP response status=%s voice_id=%s",
                        response.status,
                        video_id,
                    )

                    if response.status != HTTPStatus.OK:
                        logger.error(
                            "Voice upload failed with status %s video_id=%s",
                            response.status,
                            video_id,
                        )
                        raise UploadError(
                            "Voice upload failed with status "
                            f"{response.status} voice_id={video_id}"
                        )

                    try:
                        logger.debug(
                            "Waiting for voice processing notification voice_id=%s",
                            video_id,
                        )
                        await asyncio.wait_for(future, 60)
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Timed out waiting for voice processing notification voice_id=%s",
                            video_id,
                        )
                        raise UploadError(
                            f"Timed out waiting for voice processing voice_id={video_id}"
                        )

                    logger.debug("Voice upload complete voice_id=%s", video_id)
                    return VideoAttachPayload(
                        type=AttachmentType.AUDIO, video_id=video_id, token=token
                    )

        except UploadError:
            raise
        except aiohttp.ClientError as e:
            logger.exception("HTTP error during voice upload voice_id=%s", video_id)
            raise UploadError(f"HTTP error during voice upload voice_id={video_id}") from e
        except asyncio.TimeoutError as e:
            logger.exception("Timed out during voice upload voice_id=%s", video_id)
            raise UploadError(f"Timed out during voice upload voice_id={video_id}") from e
        except Exception as e:
            logger.exception("Unexpected error during voice upload voice_id=%s", video_id)
            raise UploadError(f"Unexpected error during voice upload voice_id={video_id}") from e
        finally:
            self.voice_upload_waiters.pop(video_id, None)
            logger.debug("Voice upload waiter removed voice_id=%s", video_id)

    async def upload_video(self, uploadable_video: Video | VideoNote) -> VideoAttachPayload:
        logger.info("Uploading video")
        logger.debug("Preparing video upload payload")

        if isinstance(uploadable_video, VideoNote):
            payload = UploadPayload(type=1, uploader_type=1).to_payload()
        else:
            payload = UploadPayload().to_payload()

        try:
            data = await self.app.invoke(
                Opcode.VIDEO_UPLOAD,
                payload=payload,
            )
        except Exception as e:
            logger.exception("Failed to request video upload URL")
            raise UploadError("Failed to request video upload URL") from e

        try:
            response = VideoUploadResponse.model_validate(data.payload)
        except ValidationError as e:
            logger.exception("Invalid video upload response model")
            logger.debug("Invalid video upload payload=%r", data.payload)
            raise UploadError("Invalid video upload response model") from e
        except Exception as e:
            logger.exception("Failed to parse video upload response")
            logger.debug("Invalid video upload payload=%r", data.payload)
            raise UploadError("Failed to parse video upload response") from e

        try:
            upload_info = response.info[0]
        except IndexError as e:
            logger.error("Video upload response info is empty")
            logger.debug("Video upload response=%r", response)
            raise UploadError("Video upload response info is empty") from e
        except Exception as e:
            logger.exception("Failed to get video upload info")
            logger.debug("Video upload response=%r", response)
            raise UploadError("Failed to get video upload info") from e

        try:
            file_size = await uploadable_video.size()
        except Exception as e:
            logger.exception("Failed to get video size")
            raise UploadError("Failed to get video size") from e

        logger.debug(
            "Video upload info received video_id=%s file_size=%s",
            upload_info.video_id,
            file_size,
        )

        timeout = aiohttp.ClientTimeout(total=900, sock_read=60)

        headers = {
            "Content-Disposition": f"attachment; filename={quote(uploadable_video.name)}",
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
            "Content-Length": str(file_size),
            "Connection": "keep-alive",
        }

        logger.debug(
            "Video upload headers prepared content_range=%s",
            headers["Content-Range"],
        )

        loop = asyncio.get_running_loop()
        future: asyncio.Future[VideoUploadSignal] = loop.create_future()

        video_id = upload_info.video_id
        token = upload_info.token

        self.video_upload_waiters[video_id] = future
        logger.debug("Video upload waiter registered video_id=%s", video_id)

        try:
            async with aiohttp.ClientSession(
                timeout=timeout, proxy=self.app.config.proxy
            ) as session:
                logger.debug("Starting video upload HTTP request video_id=%s", video_id)

                async with session.post(
                    url=upload_info.url,
                    headers=headers,
                    data=uploadable_video.iter_chunks(1024 * 1024),
                ) as response:
                    logger.debug(
                        "Video upload HTTP response status=%s video_id=%s",
                        response.status,
                        video_id,
                    )

                    if response.status != HTTPStatus.OK:
                        logger.error(
                            "Video upload failed with status %s video_id=%s",
                            response.status,
                            video_id,
                        )
                        raise UploadError(
                            "Video upload failed with status "
                            f"{response.status} video_id={video_id}"
                        )

                    try:
                        if isinstance(uploadable_video, VideoNote):
                            data = await response.json(content_type=None)

                            thumbhash = data.get("thumbhash")
                            if thumbhash:
                                thumbhash += "=" * (-len(thumbhash) % 4)
                                thumbhash = base64.b64decode(thumbhash)

                            return VideoAttachPayload(
                                video_id=video_id,
                                token=token,
                                video_type=1,
                                thumbhash=thumbhash,
                                duration=await uploadable_video.get_duration(),
                            )
                        else:
                            logger.debug(
                                "Waiting for video processing notification video_id=%s",
                                video_id,
                            )
                            await asyncio.wait_for(future, 60)
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Timed out waiting for video processing notification video_id=%s",
                            video_id,
                        )
                        raise UploadError(
                            f"Timed out waiting for video processing video_id={video_id}"
                        )

                    logger.debug("Video upload complete video_id=%s", video_id)

                    return VideoAttachPayload(video_id=video_id, token=token)

        except UploadError:
            raise
        except aiohttp.ClientError as e:
            logger.exception("HTTP error during video upload video_id=%s", video_id)
            raise UploadError(f"HTTP error during video upload video_id={video_id}") from e
        except asyncio.TimeoutError as e:
            logger.exception("Timed out during video upload video_id=%s", video_id)
            raise UploadError(f"Timed out during video upload video_id={video_id}") from e
        except Exception as e:
            logger.exception("Unexpected error during video upload video_id=%s", video_id)
            raise UploadError(f"Unexpected error during video upload video_id={video_id}") from e
        finally:
            self.video_upload_waiters.pop(video_id, None)
            logger.debug("Video upload waiter removed video_id=%s", video_id)

    async def upload_file(self, file: File) -> AttachFilePayload:
        logger.info("Uploading file")

        payload = UploadPayload().to_payload()

        try:
            data = await self.app.invoke(
                Opcode.FILE_UPLOAD,
                payload=payload,
            )
        except Exception as e:
            logger.exception("Failed to request file upload URL")
            raise UploadError("Failed to request file upload URL") from e

        try:
            response = FileUploadResponse.model_validate(data.payload)
        except ValidationError as e:
            logger.exception("Invalid file upload response model")
            logger.debug("Invalid file upload payload=%r", data.payload)
            raise UploadError("Invalid file upload response model") from e
        except Exception as e:
            logger.exception("Failed to parse file upload response")
            logger.debug("Invalid File upload payload=%r", data.payload)
            raise UploadError("Failed to parse file upload response") from e

        try:
            upload_info = response.info[0]
        except IndexError as e:
            logger.error("File upload response info is empty")
            logger.debug("File upload response=%r", response)
            raise UploadError("File upload response info is empty") from e
        except Exception as e:
            logger.exception("Failed to get file upload info")
            logger.debug("File upload response=%r", response)
            raise UploadError("Failed to get file upload info") from e

        try:
            file_size = await file.size()
        except Exception as e:
            logger.exception("Failed to get file size")
            raise UploadError("Failed to get file size") from e

        headers = {
            "Content-Disposition": f"attachment; filename={quote(file.name)}",
            "Content-Length": str(file_size),
            "Content-Range": f"0-{file_size - 1}/{file_size}",
        }

        logger.debug(
            "File upload headers prepared content_range=%s",
            headers["Content-Range"],
        )

        loop = asyncio.get_running_loop()
        future: asyncio.Future[FileUploadSignal] = loop.create_future()

        file_id = upload_info.file_id

        self.file_upload_waiters[file_id] = future
        logger.debug("File upload waiter registered file_id=%s", file_id)

        try:
            async with aiohttp.ClientSession(
                proxy=self.app.config.proxy,
            ) as session:
                async with session.post(
                    url=upload_info.url,
                    headers=headers,
                    data=file.iter_chunks(1024 * 1024),
                ) as response:
                    logger.debug(
                        "File upload HTTP response status=%s file_id=%s",
                        response.status,
                        file_id,
                    )

                    if response.status != HTTPStatus.OK:
                        logger.error(
                            "File upload failed with status %s file_id=%s",
                            response.status,
                            file_id,
                        )
                        raise UploadError(
                            f"File upload failed with status {response.status} file_id={file_id}"
                        )

                    try:
                        logger.debug(
                            "Waiting for file processing notification file_id=%s",
                            file_id,
                        )
                        await asyncio.wait_for(future, 60)
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Timed out waiting for file processing notification file_id=%s",
                            file_id,
                        )
                        raise UploadError(
                            f"Timed out waiting for file processing file_id={file_id}"
                        )

                    logger.debug("File upload complete file_id=%s", file_id)
                    return AttachFilePayload(file_id=file_id)

        except UploadError:
            raise
        except aiohttp.ClientError as e:
            logger.exception("HTTP error during file upload file_id=%s", file_id)
            raise UploadError(f"HTTP error during file upload file_id={file_id}") from e
        except asyncio.TimeoutError as e:
            logger.exception("Timed out during file upload file_id=%s", file_id)
            raise UploadError(f"Timed out during file upload file_id={file_id}") from e
        except Exception as e:
            logger.exception("Unexpected error during file upload file_id=%s", file_id)
            raise UploadError(f"Unexpected error during file upload file_id={file_id}") from e
        finally:
            self.file_upload_waiters.pop(file_id, None)
            logger.debug("File upload waiter removed file=%s", file_id)

    async def on_voice_attach(self, attach: AudioUploadSignal, _: Client) -> None:
        future = self.voice_upload_waiters.pop(attach.audio_id, None)

        if not future:
            logger.debug("No voice upload waiter found voice_id=%s", attach.audio_id)
            return

        if future.done():
            logger.debug("Voice upload waiter already done voice_id=%s", attach.audio_id)
            return

        future.set_result(attach)
        logger.debug("Voice upload waiter resolved voice_id=%s", attach.audio_id)

    async def on_video_attach(self, attach: VideoUploadSignal, _: Client) -> None:
        logger.debug("Received attach event video_id=%s", attach.video_id)

        future = self.video_upload_waiters.pop(attach.video_id, None)

        if not future:
            logger.debug("No video upload waiter found video_id=%s", attach.video_id)
            return

        if future.done():
            logger.debug("Video upload waiter already done video_id=%s", attach.video_id)
            return

        future.set_result(attach)
        logger.debug("Video upload waiter resolved video_id=%s", attach.video_id)

    async def on_file_attach(self, attach: FileUploadSignal, _: Client) -> None:
        logger.debug("Received attach event file_id=%s", attach.file_id)
        future = self.file_upload_waiters.pop(attach.file_id, None)

        if not future:
            logger.debug("No file upload waiter found file_id=%s", attach.file_id)
            return

        if future.done():
            logger.debug("File upload waiter already done file_id=%s", attach.file_id)
            return

        future.set_result(attach)
        logger.debug("File upload waiter resolved file_id=%s", attach.file_id)
