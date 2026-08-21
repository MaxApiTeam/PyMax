from random import choice, randint
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from pymax.api.session.enums import DeviceType
from pymax.api.session.payloads import (
    DEFAULT_WEB_HEADER_USER_AGENT,
    MobileUserAgentPayload,
)
from pymax.fingerprint.models import ApkBuildFingerprint
from pymax.session import StoreProtocol
from pymax.types.domain.sync import SyncOverrides
from pymax.versions.catalog import VersionCatalog

MIN_PREFERRED_BUILD = 6712
APP_VERSIONS: tuple[tuple[str, int], ...] = (
    ("26.25.0", 6790),
    ("26.24.0", 6784),
    ("26.23.2", 6779),
    ("26.23.1", 6778),
    ("26.23.0", 6777),
    ("26.22.2", 6773),
    ("26.22.1", 6772),
    ("26.22.0", 6770),
    ("26.21.1", 6763),
    ("26.20.2", 6758),
    ("26.20.1", 6740),
    ("26.19.3", 6734),
    ("26.19.2", 6732),
    ("26.19.1", 6729),
    ("26.19.0", 6727),
    ("26.18.4", 6724),
    ("26.18.2", 6720),
    ("26.18.1", 6716),
    ("26.18.0", 6715),
    ("26.17.1", 6712),
    ("26.16.4", 6704),
    ("26.16.3", 6702),
    ("26.16.2", 6701),
    ("26.16.1", 6700),
    ("26.16.0", 6698),
    ("26.15.3", 6695),
    ("26.15.1", 6690),
    ("26.15.0", 6689),
    ("26.14.1", 6686),
    ("26.14.0", 6685),
    ("26.13.0", 6683),
    ("26.12.2", 6681),
    ("26.12.1", 6679),
    ("26.12.0", 6676),
    # ("26.11.3", 6670), # Not supported TODO: delete maybe
    # ("26.11.2", 6669),
    # ("26.11.1", 6665),
    # ("26.10.1", 6653),
    # ("26.10.0", 6648),
    # ("26.9.1", 6643),
)
ANDROID_DEVICES: tuple[tuple[str, str, str, str], ...] = (
    ("Samsung SM-A525F", "Android 13", "405dpi 405dpi 1080x2400", "arm64-v8a"),
    ("Samsung SM-A536B", "Android 14", "405dpi 405dpi 1080x2400", "arm64-v8a"),
    ("Samsung SM-A546E", "Android 14", "405dpi 405dpi 1080x2340", "arm64-v8a"),
    ("Samsung SM-G991B", "Android 14", "421dpi 421dpi 1080x2400", "arm64-v8a"),
    ("Samsung SM-G998B", "Android 13", "515dpi 515dpi 1440x3200", "arm64-v8a"),
    ("Samsung SM-S901B", "Android 14", "425dpi 425dpi 1080x2340", "arm64-v8a"),
    ("Samsung SM-S911B", "Android 14", "425dpi 425dpi 1080x2340", "arm64-v8a"),
    ("Xiaomi 2109119DG", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("Xiaomi 2201117TG", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("Xiaomi 2201123G", "Android 14", "526dpi 526dpi 1440x3200", "arm64-v8a"),
    ("Xiaomi 2210132G", "Android 14", "446dpi 446dpi 1220x2712", "arm64-v8a"),
    (
        "Xiaomi 23049PCD8G",
        "Android 14",
        "446dpi 446dpi 1220x2712",
        "arm64-v8a",
    ),
    ("Redmi 2201116TG", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("Redmi 22101316G", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("Redmi 23021RAA2Y", "Android 14", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("POCO 22011211G", "Android 13", "395dpi 395dpi 1080x2400", "arm64-v8a"),
    ("POCO 23049PCD8G", "Android 14", "446dpi 446dpi 1220x2712", "arm64-v8a"),
    ("Pixel 6", "Android 14", "411dpi 411dpi 1080x2400", "arm64-v8a"),
    ("Pixel 6a", "Android 14", "429dpi 429dpi 1080x2400", "arm64-v8a"),
    ("Pixel 7", "Android 14", "416dpi 416dpi 1080x2400", "arm64-v8a"),
    ("Pixel 7 Pro", "Android 14", "512dpi 512dpi 1440x3120", "arm64-v8a"),
    ("Pixel 8", "Android 14", "428dpi 428dpi 1080x2400", "arm64-v8a"),
    ("OnePlus NE2213", "Android 14", "525dpi 525dpi 1440x3216", "arm64-v8a"),
    ("OnePlus CPH2449", "Android 14", "451dpi 451dpi 1240x2772", "arm64-v8a"),
    ("realme RMX3085", "Android 13", "409dpi 409dpi 1080x2400", "arm64-v8a"),
    ("realme RMX3370", "Android 13", "409dpi 409dpi 1080x2400", "arm64-v8a"),
    ("realme RMX3630", "Android 13", "400dpi 400dpi 1080x2412", "arm64-v8a"),
    ("HUAWEI ELS-NX9", "Android 12", "441dpi 441dpi 1080x2340", "arm64-v8a"),
    ("HUAWEI VOG-L29", "Android 12", "398dpi 398dpi 1080x2340", "arm64-v8a"),
    ("HONOR RMO-NX1", "Android 13", "391dpi 391dpi 1080x2388", "arm64-v8a"),
    ("HONOR REA-NX9", "Android 13", "435dpi 435dpi 1200x2664", "arm64-v8a"),
)
LOCALE_TIMEZONES: tuple[tuple[str, str], ...] = (
    ("ru", "Europe/Moscow"),
    ("ru", "Europe/Kaliningrad"),
    ("ru", "Europe/Samara"),
    ("ru", "Asia/Yekaterinburg"),
    ("ru", "Asia/Omsk"),
    ("ru", "Asia/Novosibirsk"),
    ("ru", "Asia/Krasnoyarsk"),
    ("ru", "Asia/Irkutsk"),
    ("ru", "Asia/Yakutsk"),
    ("ru", "Asia/Vladivostok"),
)
WEB_APP_VERSION = "26.8.4"
WEB_SCREEN = "1080x1920 1.0x"

PREFERRED_VERSION = [version for version in APP_VERSIONS if version[1] >= MIN_PREFERRED_BUILD]
LEGACY_VERSIONS = [version for version in APP_VERSIONS if version[1] < MIN_PREFERRED_BUILD]


class DeviceConfig(BaseModel):
    mt_instance_id: str
    user_agent: MobileUserAgentPayload
    device_id: str = Field(default_factory=lambda: str(uuid4()))
    client_session_id: int = Field(default_factory=lambda: randint(1, 70))


class RegistrationConfig(BaseModel):
    """Данные профиля для регистрации нового аккаунта по SMS.

    Передайте объект через ``ExtraConfig.registration_config``. Он используется
    только если после подтверждения SMS-кода Max вернул токен регистрации.

    Args:
        first_name: Имя нового пользователя.
        last_name: Фамилия нового пользователя.
    """

    first_name: str
    last_name: str | None = None


class ClientConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_version: str | None = VersionCatalog.RECOMMENDED_APP_VERSION
    fingering: ApkBuildFingerprint | None

    phone: str | None = None
    work_dir: str = "."
    session_name: str = "session.db"
    device: DeviceConfig
    token: str | None = None
    proxy: str | None = None
    registration_config: RegistrationConfig | None = None
    upload_timeout: int = 900
    relogin: bool = True
    host: str = "api2.oneme.ru"
    port: int = 443
    use_ssl: bool = True

    protocol_version: int = 10
    request_timeout: float = 30.0
    log_level: str = "INFO"
    telemetry: bool = False

    interactive: bool = True

    store: StoreProtocol | None = None

    sync: SyncOverrides = Field(default_factory=SyncOverrides)

    def ensure_config(self) -> None:
        if not self.phone:
            raise ValueError("Phone must be provided when no saved session exists.")


class ExtraConfig(BaseModel):
    """Дополнительные настройки ``Client`` и ``WebClient``.

    Используйте ``ExtraConfig`` для token-логина, debug-логов, reconnect,
    пользовательского device/user-agent и переопределения sync-state.

    Args:
        token: Готовый token для создания сессии без SMS/QR.
        registration_config: Имя и фамилия для автоматического завершения
            регистрации нового аккаунта по SMS.
        host: TCP host Max API.
        port: TCP port Max API.
        url: WebSocket URL для ``WebClient``.
        use_ssl: Использовать TLS для TCP.
        proxy: Proxy URL для TCP- или WebSocket-транспорта.
        reconnect: Переподключаться после сетевых ошибок.
        reconnect_delay: Пауза перед reconnect.
        upload_timeout: Timeout загрузки файлов в секундах.
        device_id: Явный device ID. Если не передан, генерируется UUID.
        device_type: Тип устройства для mobile user-agent.
        user_agent: Полностью заданный user-agent payload.
        mt_instance_id: Instance ID устройства.
        request_timeout: Timeout API-запросов в секундах.
        log_level: Уровень логов ``pymax``.
        telemetry: Отправлять telemetry-события Max.
        sync: Переопределения sync-маркеров для login.

    Example:
        .. code-block:: python

           from pymax import Client, ExtraConfig, SyncOverrides

           client = Client(
               phone="+79990000000",
               extra_config=ExtraConfig(
                   log_level="DEBUG",
                   reconnect=False,
                   sync=SyncOverrides(chats_sync=-1),
               ),
           )
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    token: str | None = None
    registration_config: RegistrationConfig | None = None

    host: str = "api2.oneme.ru"
    port: int = 443
    url: str = "wss://api.oneme.ru/websocket"
    use_ssl: bool = True
    proxy: str | None = None
    reconnect: bool = True
    reconnect_delay: float = 1.0
    upload_timeout: int = 900
    relogin: bool = True

    device_id: str | None = None
    device_type: DeviceType = DeviceType.ANDROID
    user_agent: MobileUserAgentPayload | None = None
    mt_instance_id: str = Field(default_factory=lambda: str(uuid4()))

    request_timeout: float = 30.0
    log_level: str = "INFO"
    telemetry: bool = True

    store: StoreProtocol | None = None

    sync: SyncOverrides = Field(default_factory=SyncOverrides)

    def generate_user_agent(self, app_version: str, build_number: int) -> MobileUserAgentPayload:
        """Создает mobile user-agent payload для TCP-клиента.

        Returns:
            Случайная, но правдоподобная конфигурация Android-клиента Max.
        """
        device_name, os_version, screen, arch = choice(ANDROID_DEVICES)
        locale, timezone = choice(LOCALE_TIMEZONES)

        return MobileUserAgentPayload(
            device_type=self.device_type,
            app_version=app_version,
            os_version=os_version,
            timezone=timezone,
            screen=screen,
            push_device_type="GCM",
            arch=arch,
            locale=locale,
            build_number=build_number,
            device_name=device_name,
            device_locale=locale,
        )

    def generate_web_user_agent(self) -> MobileUserAgentPayload:
        """Создает web user-agent payload для ``WebClient``.

        Returns:
            Конфигурация web-клиента Max с ``DeviceType.WEB``.
        """
        locale, timezone = choice(LOCALE_TIMEZONES)

        return MobileUserAgentPayload(
            device_type=DeviceType.WEB,
            app_version=WEB_APP_VERSION,
            os_version="Linux",
            timezone=timezone,
            screen=WEB_SCREEN,
            locale=locale,
            device_name="Chrome",
            device_locale=locale,
            header_user_agent=DEFAULT_WEB_HEADER_USER_AGENT,
        )


# ignore. for future upd

# class TcpOptions(BaseModel):
#     host: str = "api.oneme.ru"
#     port: int = 443
#     use_ssl: bool = True
#     proxy: str | None = None


# class RuntimeOptions(BaseModel):
#     request_timeout: float = 30.0
#     reconnect: bool = True
#     reconnect_delay: float = 1.0


# class DeviceOptions(BaseModel):
#     device_id: str | None = None
#     device_type: DeviceType = DeviceType.ANDROID
#     user_agent: MobileUserAgentPayload | None = None
#     mt_instance_id: str = Field(default_factory=lambda: str(uuid4()))
