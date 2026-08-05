from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pymax.api.response import require_payload_model
from pymax.logging import get_logger
from pymax.protocol import Opcode
from pymax.types import ButtonType, CallbackResponse
from pymax.types.domain import InitData

from .payloads import RequestInitDataPayload, SendCallbackPayload

if TYPE_CHECKING:
    from pymax.app import App


logger = get_logger(__name__)


class BotsService:
    def __init__(self, app: App) -> None:
        self.app = app

    async def get_init_data(
        self,
        bot_id: int,
        chat_id: int | None = None,
        start_param: str | None = None,
    ) -> InitData:
        frame = RequestInitDataPayload(bot_id=bot_id, chat_id=chat_id, start_param=start_param)
        response = await self.app.invoke(Opcode.WEB_APP_INIT_DATA, frame.to_payload())
        return require_payload_model(response, InitData)

    async def send_callback(
        self, callback_id: str, type: ButtonType, payload: str | None = None
    ) -> CallbackResponse:
        frame = SendCallbackPayload(
            callback_id=callback_id, type=type, payload=payload, timestamp=int(time.time() * 1000)
        )
        response = await self.app.invoke(Opcode.MSG_SEND_CALLBACK, frame.to_payload())
        return require_payload_model(response, CallbackResponse)
