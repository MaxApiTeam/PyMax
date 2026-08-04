from enum import Enum


class AvatarType(str, Enum):
    USER_AVATAR = "USER_AVATAR"


class SelfPayloadKey(str, Enum):
    PROFILE = "profile"
    URL = "url"
    TOKEN = "token"
    HASH = "hash"


class PrivacyAccess(str, Enum):
    """Уровень доступа к данным и действиям аккаунта."""

    ALL = "ALL"
    CONTACTS = "CONTACTS"
    NOBODY = "_NONE_"
