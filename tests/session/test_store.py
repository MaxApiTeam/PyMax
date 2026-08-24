from __future__ import annotations

import sqlite3

import pytest

from pymax.session.models import SessionInfo
from pymax.session.store import SessionStore
from pymax.types.domain.sync import SyncState
from tests.conftest import mobile_user_agent


@pytest.mark.asyncio
async def test_session_store_saves_loads_updates_and_deletes_session(
    tmp_path,
) -> None:
    store = SessionStore(str(tmp_path), "test-session.db")
    user_agent = mobile_user_agent()
    session = SessionInfo(
        token="token-1",
        device_id="device-1",
        phone="+79990000000",
        mt_instance_id="mt-1",
        user_agent=user_agent,
        sync=SyncState(
            chats_sync=1,
            contacts_sync=2,
            drafts_sync=3,
            presence_sync=4,
            config_hash="hash-1",
        ),
    )

    await store.save_session(session)

    loaded = await store.load_session()
    by_device = await store.load_session_by_device_id("device-1")
    by_phone = await store.load_session_by_phone("+79990000000")

    assert loaded == session
    assert loaded.user_agent == user_agent
    assert by_device == session
    assert by_phone == session

    await store.update_token("token-1", "token-2")
    loaded_after_update = await store.load_session()
    assert loaded_after_update is not None
    assert loaded_after_update.token == "token-2"

    await store.delete_session("token-2")
    assert await store.load_session() is None

    await store.close()
    assert store.conn is None


@pytest.mark.asyncio
async def test_session_store_deletes_all_sessions(tmp_path) -> None:
    store = SessionStore(str(tmp_path), "test-session.db")
    first = SessionInfo(token="token-1", device_id="device-1", phone="+79990000001")
    second = SessionInfo(token="token-2", device_id="device-2", phone="")

    await store.save_session(first)
    await store.save_session(second)

    await store.delete_all_sessions()

    assert await store.load_session() is None
    assert await store.load_session_by_device_id("device-1") is None
    assert await store.load_session_by_device_id("device-2") is None
    assert await store.load_session_by_phone("+79990000001") is None
    assert await store.load_session_by_phone("") is None

    await store.close()


@pytest.mark.asyncio
async def test_session_store_loads_database_created_before_user_agent(tmp_path) -> None:
    db_path = tmp_path / "legacy-session.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE sessions (
                token TEXT NOT NULL PRIMARY KEY,
                device_id TEXT NOT NULL,
                phone TEXT NOT NULL,
                mt_instance_id TEXT NOT NULL DEFAULT '',
                chats_sync INTEGER NOT NULL DEFAULT -1,
                contacts_sync INTEGER NOT NULL DEFAULT -1,
                drafts_sync INTEGER NOT NULL DEFAULT -1,
                presence_sync INTEGER NOT NULL DEFAULT -1,
                config_hash TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            INSERT INTO sessions (
                token,
                device_id,
                phone,
                mt_instance_id,
                chats_sync,
                contacts_sync,
                drafts_sync,
                presence_sync,
                config_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("legacy-token", "legacy-device", "+79990000000", "legacy-mt", 1, 2, 3, 4, "hash"),
        )

    store = SessionStore(str(tmp_path), db_path.name)

    loaded = await store.load_session()

    assert loaded == SessionInfo(
        token="legacy-token",
        device_id="legacy-device",
        phone="+79990000000",
        mt_instance_id="legacy-mt",
        sync=SyncState(
            chats_sync=1,
            contacts_sync=2,
            drafts_sync=3,
            presence_sync=4,
            config_hash="hash",
        ),
    )
    assert loaded.user_agent is None

    await store.close()
