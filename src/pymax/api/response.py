from enum import Enum
from typing import Any, TypeVar, cast, overload

from pydantic import BaseModel

from pymax.exceptions import PyMaxError
from pymax.protocol import InboundFrame

T = TypeVar("T", bound=BaseModel)
V = TypeVar("V")

PayloadKey = str | Enum


def _key_value(key: PayloadKey) -> str:
    value = key.value if isinstance(key, Enum) else key
    return str(value)


def payload_dict(response: InboundFrame) -> dict[Any, Any]:
    return response.payload or {}


def payload_keys(response: InboundFrame) -> list[Any]:
    return sorted(payload_dict(response))


def require_payload_dict(response: InboundFrame) -> dict[Any, Any]:
    if not isinstance(response.payload, dict):
        raise PyMaxError("Invalid response payload")

    return response.payload


@overload
def payload_item(
    response: InboundFrame,
    key: PayloadKey,
) -> Any | None: ...


@overload
def payload_item(
    response: InboundFrame,
    key: PayloadKey,
    validation_type: type[V],
) -> V | None: ...


def payload_item(
    response: InboundFrame,
    key: PayloadKey,
    validation_type: type[V] | None = None,
) -> V | Any | None:
    data = payload_dict(response).get(_key_value(key))

    if data is None:
        return None

    if validation_type is None:
        return data

    return cast("Any", validation_type)(data)


def require_payload_item(
    response: InboundFrame,
    key: PayloadKey,
) -> Any:
    item = payload_item(response, key)
    if item is None:
        raise PyMaxError(f"Missing `{_key_value(key)}` in response")

    return item


def parse_payload_model(
    response: InboundFrame,
    model: type[T],
) -> T | None:
    if response.payload:
        return model.model_validate(response.payload)

    return None


def require_payload_model(
    response: InboundFrame,
    model: type[T],
) -> T:
    if not response.payload:
        raise PyMaxError("Missing payload in response")

    return model.model_validate(response.payload)


def parse_payload_item_model(
    response: InboundFrame,
    key: PayloadKey,
    model: type[T],
) -> T | None:
    item = payload_item(response, key)
    if item:
        return model.model_validate(item)

    return None


def require_payload_item_model(
    response: InboundFrame,
    key: PayloadKey,
    model: type[T],
) -> T:
    return model.model_validate(require_payload_item(response, key))


def parse_payload_list(
    response: InboundFrame,
    key: PayloadKey,
    model: type[T],
) -> list[T]:
    items = payload_item(response, key) or []
    return [model.model_validate(item) for item in items]
