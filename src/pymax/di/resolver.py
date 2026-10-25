from __future__ import annotations

from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any, TypeAlias

from pymax.fsm import FSMContext
from pymax.types import Message

from .context import DiContext

logger = getLogger()


async def resolve_fsm(ctx: DiContext) -> FSMContext | None:
    if not isinstance(ctx.event, Message):
        raise ValueError("Fsm is not currently working for non-message handlers.")

    if not ctx.event.chat_id or not ctx.event.sender:
        logger.warning("Not enough data in message event. Skipping fsm")
        return None

    return ctx.app.fsm_storage.get_context(ctx.client, ctx.event)


Resolver: TypeAlias = Callable[[DiContext], Awaitable[Any]]

DI_MAP: dict[type, Resolver] = {FSMContext: resolve_fsm}


class DiResolver:
    async def resolve(self, annotation: Any, ctx: DiContext) -> None | Any:
        resolver = DI_MAP.get(annotation)

        if resolver is None:
            return None

        return await resolver(ctx)
