from pydantic import Field

from pymax.api.models import CamelModel
from pymax.api.session.payloads import MobileUserAgentPayload
from pymax.types.domain.sync import DEFAULT_CONFIG_HASH, ConfigHash, SyncState

from .enums import AuthType, TwoFactorAction


class RequestCodePayload(CamelModel):
    phone: str
    type: AuthType = AuthType.START_AUTH
    mode: bytes | None


class SendCodePayload(CamelModel):
    token: str
    verify_code: str

    auth_token_type: AuthType = AuthType.CHECK_CODE


class CheckPasswordChallengePayload(CamelModel):
    track_id: str
    password: str


class Exp(CamelModel):
    chats_count_groups: bytearray = bytearray.fromhex("0a32")


class WebSyncPayload(CamelModel):
    token: str
    chats_count: int = 40
    interactive: bool = True
    chats_sync: int = -1
    contacts_sync: int = -1
    presence_sync: int = -1
    drafts_sync: int = -1

    @classmethod
    def from_sync_state(
        cls,
        token: str,
        sync: SyncState,
    ) -> "WebSyncPayload":
        return cls(
            token=token,
            chats_sync=sync.chats_sync,
            contacts_sync=sync.contacts_sync,
            drafts_sync=sync.drafts_sync,
        )


class SyncPayload(CamelModel):
    user_agent: MobileUserAgentPayload
    token: str
    chat_cache_fingerprint: bytes | None = None
    chats_count: int | None = None
    chats_sync: int = -1
    contacts_sync: int = -1
    drafts_sync: int = -1
    interactive: bool = True
    presence_sync: int = -1
    exp: Exp = Field(default_factory=Exp)
    config_hash: ConfigHash = DEFAULT_CONFIG_HASH

    @classmethod
    def from_sync_state(
        cls,
        user_agent: MobileUserAgentPayload,
        token: str,
        sync: SyncState,
        chat_cache_fingerprint: bytes | None = None,
    ) -> "SyncPayload":
        return cls(
            user_agent=user_agent,
            token=token,
            chat_cache_fingerprint=chat_cache_fingerprint,
            chats_sync=sync.chats_sync,
            contacts_sync=sync.contacts_sync,
            drafts_sync=sync.drafts_sync,
            presence_sync=sync.presence_sync,
            config_hash=sync.config_hash,
        )


class CheckQrPayload(CamelModel):
    track_id: str


class ConfirmQrPayload(CamelModel):
    track_id: str


class CreateAuthTrackPayload(CamelModel):
    type: int = 0


class SetPasswordPayload(CamelModel):
    track_id: str
    password: str


class RequestEmailCodePayload(CamelModel):
    track_id: str
    email: str


class SendEmailCodePayload(CamelModel):
    track_id: str
    verify_code: str


class SetHintPayload(CamelModel):
    track_id: str
    hint: str


class SetTwoFactorPayload(CamelModel):
    expected_capabilities: list[TwoFactorAction]
    track_id: str
    password: str
    hint: str | None = None


class RemoveTwoFactorPayload(CamelModel):
    track_id: str
    remove2fa: bool = Field(default=True, alias="remove2fa")
    expected_capabilities: list[TwoFactorAction] = Field(
        default_factory=lambda: [TwoFactorAction.REMOVE_2FA]
    )


class ApproveQrLoginPayload(CamelModel):
    qr_link: str


class ConfirmRegistrationPayload(CamelModel):
    first_name: str
    last_name: str | None = None
    token: str
    token_type: AuthType = AuthType.REGISTER
