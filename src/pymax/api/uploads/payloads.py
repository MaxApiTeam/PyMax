from pydantic import Field

from pymax.api.models import CamelModel
from pymax.types import AttachmentType


class AttachPhotoPayload(CamelModel):
    type: AttachmentType = Field(default=AttachmentType.PHOTO, serialization_alias="_type")
    photo_token: str


class VideoAttachPayload(CamelModel):
    type: AttachmentType = Field(default=AttachmentType.VIDEO, serialization_alias="_type")
    video_id: int
    token: str


class AttachFilePayload(CamelModel):
    type: AttachmentType = Field(default=AttachmentType.FILE, serialization_alias="_type")
    file_id: int


class UploadPayload(CamelModel):
    count: int = 1
    type: int = 0
    uploader_type: int = 0
    profile: bool = False
