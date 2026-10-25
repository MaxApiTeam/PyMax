from __future__ import annotations

from typing import TYPE_CHECKING

from pymax.logging import get_logger

from .auth import AuthService
from .bots import BotsService
from .chats import ChatService
from .messages import MessageService
from .self import SelfService
from .session import SessionService
from .stories import StoriesService
from .uploads import UploadService
from .users import UserService

if TYPE_CHECKING:
    from pymax.app import App


logger = get_logger(__name__)


class ApiFacade:
    def __init__(self, app: App) -> None:
        self.app = app
        self.messages = MessageService(app)
        self.chats = ChatService(app)
        self.users = UserService(app)
        self.bots = BotsService(app)
        self.account = SelfService(app)
        self.session = SessionService(app)
        self.auth = AuthService(app)
        self.uploads = UploadService(app)
        self.stories = StoriesService(app)
        logger.debug("api facade initialized")
