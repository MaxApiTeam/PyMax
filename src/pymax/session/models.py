from pydantic import BaseModel, Field

from pymax.api.session.payloads import MobileUserAgentPayload
from pymax.types.domain.sync import SyncState


class SessionInfo(BaseModel):
    """Состояние авторизованной сессии, сохраняемое через ``StoreProtocol``.

    Args:
        token: Login token Max.
        device_id: ID устройства, связанный с сессией.
        phone: Номер телефона сессии; для web-сессии может быть пустой строкой.
        mt_instance_id: Instance ID устройства. Пустая строка поддерживается для
            сессий, созданных предыдущими версиями PyMax.
        user_agent: Device/user-agent сессии. ``None`` поддерживается для старых
            или пользовательских store, которые его не сохраняют.
        sync: Последние sync-маркеры login.
    """

    token: str
    device_id: str
    phone: str
    mt_instance_id: str = ""
    user_agent: MobileUserAgentPayload | None = None
    sync: SyncState = Field(default_factory=SyncState)


def resolve_session_user_agent(
    current: MobileUserAgentPayload,
    stored: MobileUserAgentPayload | None,
) -> MobileUserAgentPayload:
    if stored is None or stored.device_type != current.device_type:
        return current

    return stored.model_copy(
        update={
            "app_version": current.app_version,
            "build_number": current.build_number,
        }
    )
