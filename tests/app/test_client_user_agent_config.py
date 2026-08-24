from __future__ import annotations

import pytest

from pymax import Client, ExtraConfig, WebClient
from pymax.api.session.enums import DeviceType
from tests.conftest import mobile_user_agent


@pytest.mark.asyncio
async def test_client_config_restores_only_generated_user_agent_from_session() -> None:
    generated_client = Client(phone="+79990000000", app_version="26.14.1")
    explicit_user_agent = mobile_user_agent()
    explicit_client = Client(
        phone="+79990000000",
        app_version="26.14.1",
        extra_config=ExtraConfig(user_agent=explicit_user_agent),
    )

    generated_config = await generated_client._prepare_config()
    explicit_config = await explicit_client._prepare_config()

    assert generated_config.restore_user_agent_from_session is True
    assert explicit_config.restore_user_agent_from_session is False


@pytest.mark.asyncio
async def test_web_client_config_restores_only_generated_user_agent_from_session() -> None:
    generated_client = WebClient()
    explicit_user_agent = mobile_user_agent(DeviceType.WEB)
    explicit_client = WebClient(extra_config=ExtraConfig(user_agent=explicit_user_agent))

    generated_config = await generated_client._prepare_config()
    explicit_config = await explicit_client._prepare_config()

    assert generated_config.restore_user_agent_from_session is True
    assert explicit_config.restore_user_agent_from_session is False
