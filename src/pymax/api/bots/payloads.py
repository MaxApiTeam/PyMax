from pymax.api.models import CamelModel
from pymax.types import ButtonType


class RequestInitDataPayload(CamelModel):
    bot_id: int
    chat_id: int | None = None
    start_param: str | None = None


class SendCallbackPayload(CamelModel):
    callback_id: str
    type: ButtonType
    payload: str | None = None
    timestamp: int
