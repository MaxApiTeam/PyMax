from typing import Any

from pydantic import Field, SerializerFunctionWrapHandler, model_serializer

from pymax.api.models import CamelModel
from pymax.types import AttachmentType


class AttachPhotoPayload(CamelModel):
    type: AttachmentType = Field(default=AttachmentType.PHOTO, serialization_alias="_type")
    photo_token: str


class VideoAttachPayload(CamelModel):
    type: AttachmentType = Field(default=AttachmentType.VIDEO, serialization_alias="_type")
    video_id: int
    token: str
    video_type: int = 0
    thumbhash: bytes | None = None
    duration: int | None = None
    wave: bytes | None = None

    @model_serializer(mode="wrap")
    def serialize_attachment(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        payload = handler(self)

        if self.type == AttachmentType.AUDIO:
            payload.pop("videoId", None)
            payload.pop("videoType", None)
            if not self.token:
                payload.pop("token", None)
                payload["audioId"] = self.video_id
        elif self.video_type == 1:
            if self.token:
                payload.pop("videoId", None)
            else:
                payload.pop("token", None)
                payload["videoId"] = self.video_id

        return payload


class VoiceAttachPayload(VideoAttachPayload):
    type: AttachmentType = Field(default=AttachmentType.AUDIO, serialization_alias="_type")
    video_id: int = Field(exclude=True)
    video_type: int = Field(default=0, exclude=True)


class VideoNoteAttachPayload(VideoAttachPayload):
    video_id: int = Field(exclude=True)
    video_type: int = 1


class AttachFilePayload(CamelModel):
    type: AttachmentType = Field(default=AttachmentType.FILE, serialization_alias="_type")
    file_id: int


class UploadPayload(CamelModel):
    count: int = 1
    type: int = 0
    uploader_type: int = 0
    profile: bool = False
