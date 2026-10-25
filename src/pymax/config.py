import secrets
from random import choice, randint

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
    (
        "Google Pixel 6a",
        "Android 13",
        "420dpi 420dpi 1080x2400",
        "arm64-v8a",
    ),
    (
        "Google Pixel 7",
        "Android 13",
        "420dpi 420dpi 1080x2400",
        "arm64-v8a",
    ),
    (
        "Google Pixel 7 Pro",
        "Android 13",
        "560dpi 560dpi 1440x3120",
        "arm64-v8a",
    ),
    (
        "Google Pixel 8",
        "Android 14",
        "420dpi 420dpi 1080x2400",
        "arm64-v8a",
    ),
    (
        "samsung SM-G991B",
        "Android 14",
        "xxhdpi 480dpi 1080x2400",
        "arm64-v8a",
    ),
    (
        "samsung SM-S911B",
        "Android 15",
        "xxhdpi 480dpi 1080x2340",
        "arm64-v8a",
    ),
    (
        "Xiaomi 2201117TG",
        "Android 13",
        "440dpi 440dpi 1080x2400",
        "arm64-v8a",
    ),
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


def generate_device_id() -> str:
    return secrets.token_hex(8)


class DeviceConfig(BaseModel):
    mt_instance_id: str
    user_agent: MobileUserAgentPayload
    device_id: str = Field(default_factory=generate_device_id)
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
    persist_session: bool = True

    password_max_attempts: int | None = None
    protocol_version: int = 10
    request_timeout: float = 30.0
    log_level: str = "INFO"
    telemetry: bool = False

    interactive: bool = True
    restore_user_agent_from_session: bool = True

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
        upload_timeout: Общий timeout HTTP-загрузки файлов, видео, голосовых и
            видеосообщений в секундах. По умолчанию ``900``; не применяется к
            фотографиям и 60-секундному ожиданию обработки вложения. ``0`` и
            отрицательные значения отключают общий timeout, но не отдельный
            60-секундный socket/read timeout.
        relogin: Автоматически сбрасывать сессию и повторять авторизацию, если
            Max отозвал login token. По умолчанию ``True``.
        password_max_attempts: Максимальное число попыток ввода пароля 2FA.
            ``None`` означает отсутствие лимита; ``0`` и отрицательные значения
            сразу завершают авторизацию с ``PasswordAttemptsExceededError``.
        persist_session: Сохранять token, device/user-agent и sync-state между
            runtime в SQLite или переданном ``store``. По умолчанию ``True``.
            При ``False`` используется отдельный ``InMemoryStore`` и значение
            ``store`` игнорируется; после пересоздания runtime, в том числе при
            reconnect, сохраненная сессия недоступна.
        device_id: Явный device ID. Если не передан, генерируется строка из
            16 шестнадцатеричных символов.
        device_type: Тип устройства для mobile user-agent.
        user_agent: Полностью заданный user-agent payload. Явное значение имеет
            приоритет над user-agent из сохраненной сессии. Автоматически
            сгенерированный user-agent восстанавливает характеристики устройства
            из сессии, сохраняя версию приложения и build number текущего запуска.
        mt_instance_id: Instance ID устройства. По умолчанию генерируется
            строка из 16 шестнадцатеричных символов.
        request_timeout: Timeout API-запросов в секундах.
        log_level: Уровень логов ``pymax``.
        telemetry: Отправлять telemetry-события Max.
        store: Пользовательское хранилище сессии. Используется только при
            ``persist_session=True``.
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
    password_max_attempts: int | None = None
    persist_session: bool = True

    device_id: str | None = None
    device_type: DeviceType = DeviceType.ANDROID
    user_agent: MobileUserAgentPayload | None = None
    mt_instance_id: str = Field(default_factory=generate_device_id)

    request_timeout: float = 30.0
    log_level: str = "INFO"
    telemetry: bool = True

    store: StoreProtocol | None = None

    sync: SyncOverrides = Field(default_factory=SyncOverrides)

    def generate_user_agent(self, app_version: str, build_number: int) -> MobileUserAgentPayload:
        """Создает mobile user-agent payload для TCP-клиента.

        Args:
            app_version: Версия Android-клиента Max.
            build_number: Build number той же версии из ``VersionCatalog``.

        Returns:
            Случайная конфигурация Android-устройства с переданными версией и
            build number.
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
