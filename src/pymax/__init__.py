__version__ = "2.3.1"


from .auth import (
    AuthFlow,
    ConsolePasswordProvider,
    ConsoleQrHandler,
    ConsoleSmsCodeProvider,
    PasswordProvider,
    QrAuthFlow,
    QrHandler,
    SmsAuthFlow,
    SmsCodeProvider,
)
from .client import Client
from .client_web import WebClient
from .config import ExtraConfig, RegistrationConfig
from .dispatch import EventType, Router
from .exceptions import ApiError, PyMaxError, UploadError
from .files import File, Photo, Video, VideoNote, Voice
from .logging import configure_logging
from .routers import ClientRouter, WebRouter
from .types import (
    Chat,
    Message,
    MessageDeleteEvent,
    MessageReadEvent,
    PresenceEvent,
    Profile,
    ReactionUpdateEvent,
    TypingEvent,
    User,
)
from .types.domain.sync import SyncOverrides, SyncState

__all__ = (
    "ApiError",
    "AuthFlow",
    "Chat",
    "Client",
    "ClientRouter",
    "ConsolePasswordProvider",
    "ConsoleQrHandler",
    "ConsoleSmsCodeProvider",
    "EventType",
    "ExtraConfig",
    "File",
    "Message",
    "MessageDeleteEvent",
    "MessageReadEvent",
    "PasswordProvider",
    "Photo",
    "PresenceEvent",
    "Profile",
    "PyMaxError",
    "QrAuthFlow",
    "QrHandler",
    "ReactionUpdateEvent",
    "RegistrationConfig",
    "Router",
    "SmsAuthFlow",
    "SmsCodeProvider",
    "SyncOverrides",
    "SyncState",
    "TypingEvent",
    "UploadError",
    "User",
    "Video",
    "VideoNote",
    "Voice",
    "WebClient",
    "WebRouter",
    "__version__",
    "configure_logging",
)
