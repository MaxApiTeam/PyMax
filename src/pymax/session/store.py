from pathlib import Path

import aiosqlite

from pymax.api.session.payloads import MobileUserAgentPayload
from pymax.logging import get_logger
from pymax.types.domain.sync import DEFAULT_CONFIG_HASH, SyncState

from .models import SessionInfo
from .protocol import StoreProtocol

logger = get_logger(__name__)

SESSION_COLUMNS = """
    token,
    device_id,
    phone,
    mt_instance_id,
    chats_sync,
    contacts_sync,
    drafts_sync,
    presence_sync,
    config_hash,
    user_agent
"""


class InMemoryStore(StoreProtocol):
    """Хранилище одной сессии в памяти текущего runtime.

    Данные не записываются на диск и становятся недоступны после пересоздания
    ``App``. Обычно этот store выбирается автоматически при
    ``ExtraConfig(persist_session=False)``.
    """

    def __init__(
        self,
    ) -> None:
        self._session: SessionInfo | None = None

    async def save_session(self, session_info: SessionInfo) -> None:
        self._session = session_info

    async def update_token(self, _: str, new_token: str) -> None:
        if not self._session:
            return
        self._session.token = new_token

    async def load_session(self) -> SessionInfo | None:
        return self._session

    async def load_session_by_device_id(self, device_id: str) -> SessionInfo | None:
        if self._session and self._session.device_id != device_id:
            return None

        return self._session

    async def load_session_by_phone(self, phone: str) -> SessionInfo | None:
        if self._session and self._session.phone != phone:
            return None

        return self._session

    async def delete_session(self, _: str) -> None:
        self._session = None

    async def close(self) -> None:
        return None


class SessionStore(StoreProtocol):
    """SQLite-хранилище сессий, используемое по умолчанию.

    Args:
        work_dir: Директория файла базы данных; создается автоматически.
        db_name: Имя файла базы данных. По умолчанию ``session.db``.

    Схема существующего файла автоматически дополняется недостающими колонками.
    """

    def __init__(self, work_dir: str, db_name: str = "session.db") -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.work_dir / db_name)
        self.conn: aiosqlite.Connection | None = None
        logger.debug("session store initialized db=%s", self.db_path)

    async def _get_connection(self) -> aiosqlite.Connection:
        if self.conn is None:
            logger.debug("opening session database db=%s", self.db_path)
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row
            await self._initialize_db(self.conn)
        return self.conn

    async def _initialize_db(self, conn: aiosqlite.Connection) -> None:
        logger.debug("initializing session database")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT NOT NULL PRIMARY KEY,
                device_id TEXT NOT NULL,
                phone TEXT NOT NULL,
                mt_instance_id TEXT NOT NULL DEFAULT '',
                chats_sync INTEGER NOT NULL DEFAULT -1,
                contacts_sync INTEGER NOT NULL DEFAULT -1,
                drafts_sync INTEGER NOT NULL DEFAULT -1,
                presence_sync INTEGER NOT NULL DEFAULT -1,
                config_hash TEXT NOT NULL DEFAULT '',
                user_agent TEXT
            )
            """
        )
        await self._ensure_column(conn, "mt_instance_id", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column(conn, "chats_sync", "INTEGER NOT NULL DEFAULT -1")
        await self._ensure_column(conn, "contacts_sync", "INTEGER NOT NULL DEFAULT -1")
        await self._ensure_column(conn, "drafts_sync", "INTEGER NOT NULL DEFAULT -1")
        await self._ensure_column(conn, "presence_sync", "INTEGER NOT NULL DEFAULT -1")
        await self._ensure_column(conn, "config_hash", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column(conn, "user_agent", "TEXT")
        await conn.execute(
            """
            UPDATE sessions
            SET config_hash = ?
            WHERE config_hash = ''
            """,
            (DEFAULT_CONFIG_HASH,),
        )
        await conn.commit()

    async def _ensure_column(
        self,
        conn: aiosqlite.Connection,
        name: str,
        definition: str,
    ) -> None:
        async with conn.execute("PRAGMA table_info(sessions)") as cursor:
            columns = {row["name"] for row in await cursor.fetchall()}

        if name not in columns:
            await conn.execute(f"ALTER TABLE sessions ADD COLUMN {name} {definition}")

    async def save_session(self, session_info: SessionInfo) -> None:
        conn = await self._get_connection()
        logger.debug(
            "saving session device_id=%s phone_set=%s mt_instance_id_set=%s",
            session_info.device_id,
            bool(session_info.phone),
            bool(session_info.mt_instance_id),
        )
        await conn.execute(
            """
            INSERT OR REPLACE INTO sessions (
                token,
                device_id,
                phone,
                mt_instance_id,
                chats_sync,
                contacts_sync,
                drafts_sync,
                presence_sync,
                config_hash,
                user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_info.token,
                session_info.device_id,
                session_info.phone,
                session_info.mt_instance_id,
                session_info.sync.chats_sync,
                session_info.sync.contacts_sync,
                session_info.sync.drafts_sync,
                session_info.sync.presence_sync,
                session_info.sync.config_hash,
                (
                    session_info.user_agent.model_dump_json(by_alias=True, exclude_none=True)
                    if session_info.user_agent is not None
                    else None
                ),
            ),
        )
        await conn.commit()
        logger.info("session saved")

    async def load_session(self) -> SessionInfo | None:
        conn = await self._get_connection()
        logger.debug("loading first session")
        async with conn.execute(
            f"""
            SELECT {SESSION_COLUMNS}
            FROM sessions
            LIMIT 1
            """,
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            logger.debug("session not found")
            return None

        logger.debug(
            "session loaded device_id=%s phone_set=%s",
            row["device_id"],
            bool(row["phone"]),
        )
        return self._row_to_session(row)

    async def load_session_by_device_id(self, device_id: str) -> SessionInfo | None:
        conn = await self._get_connection()
        logger.debug("loading session by device_id=%s", device_id)
        async with conn.execute(
            f"""
            SELECT {SESSION_COLUMNS}
            FROM sessions
            WHERE device_id = ?
            """,
            (device_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            logger.debug("session not found by device_id=%s", device_id)
            return None

        return self._row_to_session(row)

    async def load_session_by_phone(self, phone: str) -> SessionInfo | None:
        conn = await self._get_connection()
        logger.debug("loading session by phone_set=%s", bool(phone))
        async with conn.execute(
            f"""
            SELECT {SESSION_COLUMNS}
            FROM sessions
            WHERE phone = ?
            """,
            (phone,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            logger.debug("session not found by phone_set=%s", bool(phone))
            return None

        return self._row_to_session(row)

    async def delete_session(self, token: str) -> None:
        conn = await self._get_connection()
        logger.warning("deleting session token_set=%s", bool(token))
        await conn.execute(
            """
            DELETE FROM sessions WHERE token = ?
            """,
            (token,),
        )
        await conn.commit()
        logger.info("session deleted")

    async def delete_all_sessions(self) -> None:
        conn = await self._get_connection()
        logger.warning("deleting all sessions")
        await conn.execute(
            """
            DELETE FROM sessions
            """
        )
        await conn.commit()
        logger.info("all sessions deleted")

    async def update_token(self, old_token: str, new_token: str) -> None:
        conn = await self._get_connection()
        logger.debug(
            "updating session token old_token_set=%s new_token_set=%s",
            bool(old_token),
            bool(new_token),
        )
        await conn.execute(
            """
            UPDATE sessions SET token = ? WHERE token = ?
            """,
            (new_token, old_token),
        )
        await conn.commit()
        logger.info("session token updated")

    async def close(self) -> None:
        if self.conn is not None:
            logger.debug("closing session database")
            await self.conn.close()
            self.conn = None

    def _row_to_session(self, row: aiosqlite.Row) -> SessionInfo:
        return SessionInfo(
            token=row["token"],
            device_id=row["device_id"],
            phone=row["phone"],
            mt_instance_id=row["mt_instance_id"] or "",
            user_agent=(
                MobileUserAgentPayload.model_validate_json(row["user_agent"])
                if row["user_agent"] is not None
                else None
            ),
            sync=SyncState(
                chats_sync=row["chats_sync"],
                contacts_sync=row["contacts_sync"],
                drafts_sync=row["drafts_sync"],
                presence_sync=row["presence_sync"],
                config_hash=row["config_hash"] or DEFAULT_CONFIG_HASH,
            ),
        )
