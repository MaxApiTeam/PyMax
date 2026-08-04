from pydantic import Field

from pymax.types.domain.sync import ConfigHash, SyncState

from .base import CamelModel
from .chat import Chat
from .message import Message
from .profile import Profile
from .user import User


class LoginConfig(CamelModel):
    hash: ConfigHash | None = None


class Login2Flags(CamelModel):
    config_enabled: bool = False
    contact_enabled: bool = False
    profile_enabled: bool = False

    @property
    def enabled(self) -> bool:
        return self.config_enabled or self.contact_enabled or self.profile_enabled


class LoginResponse(CamelModel):
    chats: list[Chat] = Field(default_factory=list)
    profile: Profile | None = None
    messages: dict[int, list[Message]] = Field(default_factory=dict)  # chat_id -> [message]
    contacts: list[User | None] = Field(default_factory=list)
    token: str | None = None
    time: int | None = None
    config: LoginConfig | None = None
    updates: int | None = None
    login2_flags: Login2Flags | None = None

    def update_sync_state(self, current: SyncState) -> SyncState:
        sync_time = self.time
        config_hash = self.config.hash if self.config is not None else None

        return SyncState(
            chats_sync=(sync_time if sync_time is not None else current.chats_sync),
            contacts_sync=(sync_time if sync_time is not None else current.contacts_sync),
            drafts_sync=(sync_time if sync_time is not None else current.drafts_sync),
            presence_sync=(sync_time if sync_time is not None else current.presence_sync),
            config_hash=(config_hash if config_hash is not None else current.config_hash),
        )


class Login2Response(CamelModel):
    profile: Profile | None = None
    contacts: list[User | None] = Field(default_factory=list, alias="contactInfos")
    config: LoginConfig | None = None

    def update_sync_state(self, current: SyncState) -> SyncState:
        config_hash = self.config.hash if self.config is not None else None

        return SyncState(
            chats_sync=current.chats_sync,
            contacts_sync=current.contacts_sync,
            drafts_sync=current.drafts_sync,
            presence_sync=current.presence_sync,
            config_hash=(config_hash if config_hash is not None else current.config_hash),
        )
