import json
from importlib import resources
from typing import Any

import aiohttp

from pymax.fingerprint.models import ApkBuildFingerprint

from .exceptions import VersionAlreadyExistsError, VersionNotFoundError


class VersionCatalog:
    """Каталог fingerprints Android-клиента Max.

    Встроенные версии загружаются при создании объекта. При ``remote=True``
    вызов :meth:`load` дополнительно получает каталог с
    ``DEFAULT_REMOTE_URL`` и объединяет его со встроенным. Ошибки сети, HTTP и
    валидации удаленного ответа не подавляются.

    Args:
        remote: Загружать ли удаленные версии при :meth:`load`.
    """

    RECOMMENDED_APP_VERSION: str = "26.25.0"
    DEFAULT_REMOTE_URL: str = "https://hashes.pymax.org/versions.json"

    def __init__(self, remote: bool = False) -> None:
        self.path = resources.files("pymax._data") / "apk_fingerprints.json"
        self.remote = remote
        self._data = self._load_fingerprints()
        self.versions = self._convert_data()

    @staticmethod
    def recommended() -> str:
        """Возвращает версию, используемую ``Client`` по умолчанию."""
        return VersionCatalog.RECOMMENDED_APP_VERSION

    async def load(self) -> "VersionCatalog":
        """Загружает удаленные версии, если включен ``remote``.

        Returns:
            Этот же каталог с добавленными удаленными версиями.
        """
        if not self.remote:
            return self

        versions = await self._fetch()
        self.versions.update(versions)

        return self

    def add(self, version: str, fingerprint: ApkBuildFingerprint, override: bool = False) -> None:
        """Добавляет fingerprint версии в текущий каталог.

        Args:
            version: Строка версии Android-клиента.
            fingerprint: Fingerprint и build number этой версии.
            override: Заменить существующую запись. По умолчанию ``False``.

        Raises:
            ValueError: Если версия уже существует и ``override=False``.
        """
        if self.versions.get(version) is not None and override is False:
            raise VersionAlreadyExistsError(version)

        self.versions[version] = fingerprint

    def resolve(self, version: str) -> ApkBuildFingerprint:
        """Возвращает fingerprint версии.

        Raises:
            VersionNotFoundError: Если версии нет в каталоге.
        """
        try:
            return self.versions[version]
        except KeyError as e:
            raise VersionNotFoundError(version) from e

    async def _fetch(self) -> dict[str, ApkBuildFingerprint]:
        async with (
            aiohttp.ClientSession() as session,
            session.get(self.DEFAULT_REMOTE_URL) as response,
        ):
            data = await response.json()
            response.raise_for_status()

            if not isinstance(data, dict):
                raise ValueError  # TODO: msg

            versions: dict[str, ApkBuildFingerprint] = {}
            for k, v in data.items():
                versions[k] = ApkBuildFingerprint.model_validate(v)

            return versions

    def _load_fingerprints(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _convert_data(self) -> dict[str, ApkBuildFingerprint]:
        versions: dict[str, ApkBuildFingerprint] = {}
        for k, v in self._data.items():
            versions[k] = ApkBuildFingerprint.model_validate(v)
        return versions
