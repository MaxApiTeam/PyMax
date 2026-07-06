import asyncio
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pymax.api import ApiFacade
from pymax.auth import AuthFlow
from pymax.config import ClientConfig
from pymax.connection import ConnectionManager
from pymax.dispatch import Dispatcher
from pymax.dispatch.router import EventType, Router
from pymax.exceptions import ApiError
from pymax.fingerprint import FingerprintGenerator
from pymax.logging import get_logger
from pymax.protocol import Command, InboundFrame, OutboundFrame
from pymax.protocol.enums import Opcode
from pymax.session import SessionStore
from pymax.session.models import SessionInfo
from pymax.telemetry import TelemetryService
from pymax.types import MaxApiError, Message
from pymax.types.domain import Chat, HandshakeResponse, Profile, User

if TYPE_CHECKING:
    from pymax.base import BaseClient

logger = get_logger(__name__)
ClientT = TypeVar("ClientT", bound="BaseClient")


class App(Generic[ClientT]):
    def __init__(
        self,
        connection: ConnectionManager,
        config: ClientConfig,
        auth_flow: AuthFlow,
        root_router: Router[ClientT] | None = None,
    ) -> None:
        self.connection = connection
        self.dispatcher: Dispatcher[ClientT] = Dispatcher(self, root_router)
        self.api = ApiFacade(self)
        self.config = config
        self.store = self.config.store or SessionStore(config.work_dir, config.session_name)
        self.auth_flow = auth_flow
        self.fingerprint_generator = FingerprintGenerator()

        self.me: Profile | None = None
        self.chats: list[Chat] | None = None
        self.users: dict[int, User] = {}
        self.contacts: list[User | None] = []
        self.messages: dict[int, list[Message]] = {}

        self.session: SessionInfo | None = None
        self.handshake_response: HandshakeResponse | None = None

        self.started = False
        self._ping_task: asyncio.Task[None] | None = None
        self._telemetry = TelemetryService(self) if config.telemetry else None

        self.connection.on_event = self.on_event
        self.connection.on_close = self.on_connection_lost
        logger.debug(
            "app initialized session=%s work_dir=%s auth_flow=%s",
            config.session_name,
            config.work_dir,
            type(self.auth_flow).__name__,
        )

    async def start(self) -> None:
        if self.started:
            logger.warning("start skipped: app already started")
            return

        logger.info("starting pymax client")
        session_data = await self.store.load_session()
        if session_data:
            if session_data.mt_instance_id:
                self.config.device.mt_instance_id = session_data.mt_instance_id
            else:
                session_data.mt_instance_id = self.config.device.mt_instance_id

        try:
            logger.debug("opening connection")
            await self.connection.open()

            handshake_device_id = (
                session_data.device_id if session_data else self.config.device.device_id
            )
            logger.debug("running handshake")
            handshake_response = await self.handshake(handshake_device_id)
        except (ConnectionError, EOFError, OSError, TimeoutError) as e:
            logger.exception("failed to connect or handshake")
            await self.connection.close()
            raise ConnectionError(f"Failed to connect and handshake: {e}") from e

        self.handshake_response = handshake_response

        self._ping_task = asyncio.create_task(self._ping_loop())

        if not session_data:
            logger.info("saved session not found; authentication required")

            if self.config.token:
                await self.store.save_session(
                    session_data := SessionInfo(
                        token=self.config.token,
                        device_id=self.config.device.device_id,
                        phone=self.config.phone or "",
                        mt_instance_id=self.config.device.mt_instance_id,
                    )
                )
            else:
                auth_result = await self.auth_flow.authenticate(self)

                if not auth_result.token:
                    logger.error("authentication finished without token")
                    raise RuntimeError("Authentication failed: no token received")

                await self.store.save_session(
                    session_data := SessionInfo(
                        token=auth_result.token,
                        device_id=self.config.device.device_id,
                        phone=self.config.phone or "",
                        mt_instance_id=self.config.device.mt_instance_id,
                    )
                )
                logger.info("new session saved")
        else:
            logger.debug(
                "loaded saved session device_id=%s phone_set=%s",
                session_data.device_id,
                bool(session_data.phone),
            )

        self.session = session_data

        logger.debug("logging in")

        try:
            response = await self.api.auth.login(
                self.config.device.user_agent,
            )
        except Exception as e:
            handled = False
            if self.dispatcher.client is not None:
                handled = await self.dispatcher.emit_error(
                    e,
                    EventType.ON_START,
                    None,
                    self.dispatcher.root_router,
                    None,
                )
            if not handled:
                raise

            await self.close()
            return

        if response.token is not None and response.token != self.session.token:
            await self.store.update_token(self.session.token, response.token)
            self.session.token = response.token

        self.me = response.profile
        self.chats = response.chats
        self.users[self.me.contact.id] = self.me.contact
        self.contacts = response.contacts
        self.messages = response.messages

        self.started = True
        logger.info(
            "client started profile=%s chats=%s",
            self.me.contact.id,
            len(self.chats or []),
        )

        if self._telemetry:
            self._telemetry.start()

    async def handshake(self, device_id: str) -> HandshakeResponse:
        response = await self.api.session.handshake(
            self.config.device.mt_instance_id,
            self.config.device.user_agent,
            device_id,
        )
        logger.debug("handshake completed device_id=%s", device_id)
        return response

    async def close(self) -> None:
        if self._telemetry:
            await self._telemetry.stop()

        if self._ping_task:
            task = self._ping_task
            self._ping_task = None
            if not task.done():
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.debug("ping task stopped with error", exc_info=True)

        await self.dispatcher.stop_startup_tasks()
        await self.connection.close()
        await self.store.close()

        self.started = False

    async def invoke(
        self,
        opcode: int,
        payload: dict[str, Any],
        cmd: int = Command.REQUEST,
        timeout: float | None = None,
        compress: bool = False,
    ) -> InboundFrame:
        seq = self.connection.next_seq()
        payload_keys = sorted(payload.keys()) if payload else []
        frame = OutboundFrame(
            ver=self.connection.protocol.version,
            opcode=opcode,
            cmd=cmd,
            seq=seq,
            payload=payload,
        )
        logger.debug(
            "request opcode=%s cmd=%s seq=%s timeout=%s compress=%s payload_keys=%s",
            opcode,
            cmd,
            seq,
            timeout,
            compress,
            payload_keys,
        )
        logger.debug("Request data=%s", frame.model_dump())

        request_timeout = self.config.request_timeout if timeout is None else timeout
        response = await self.connection.request(frame, timeout=request_timeout)

        response_keys = sorted(response.payload.keys()) if response.payload else []
        logger.debug(
            "response opcode=%s cmd=%s seq=%s payload_keys=%s",
            response.opcode,
            response.cmd,
            response.seq,
            response_keys,
        )
        if response.cmd == Command.ERROR:
            raise self._build_api_error(response)
        return response

    async def _ping_loop(self) -> None:
        try:
            while True:
                await self.invoke(
                    opcode=Opcode.PING,
                    payload={"interactive": self.config.interactive},
                    timeout=self.config.request_timeout,
                )
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("ping loop failed; closing transport: %s", e)
            await self.connection.fail(ConnectionError(f"Ping failed: {e}"))

    def on_connection_lost(self, exc: Exception | None = None) -> None:
        if self.started:
            logger.warning("connection lost; marking app as stopped: %s", exc)

        self.started = False

        task = self._ping_task
        if task is None or task.done():
            return

        current_task = asyncio.current_task()
        if task is not current_task:
            task.cancel()

    def _build_api_error(self, response: InboundFrame) -> ApiError:
        try:
            error = MaxApiError.model_validate(response.payload)
        except Exception as e:
            logger.exception("failed to validate API error")
            error = MaxApiError(
                error="unknown_error",
                title="Unknown error",
                message=str(e),
                localized_message=str(e),
            )

        exc = ApiError(
            opcode=response.opcode,
            error=error.error,
            title=error.title,
            message=error.message,
            localized_message=error.localized_message,
            payload=response.payload,
        )
        logger.error(
            "api error opcode=%s seq=%s error=%s title=%s message=%s localized_message=%s",
            response.opcode,
            response.seq,
            error.error,
            error.title,
            error.message,
            error.localized_message,
        )
        return exc

    async def on_event(self, frame: InboundFrame) -> None:
        logger.debug(
            "event received opcode=%s cmd=%s seq=%s",
            frame.opcode,
            frame.cmd,
            frame.seq,
        )
        logger.debug("Event data=%s", frame.payload)
        try:
            await self.dispatcher.dispatch(frame)
        except Exception as e:
            logger.exception("failed to dispatch inbound frame")
            raise RuntimeError(f"Failed to dispatch inbound frame: {e}") from e
