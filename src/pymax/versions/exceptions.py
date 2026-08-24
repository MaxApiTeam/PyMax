class VersionNotFoundError(ValueError):
    """Выбранная версия приложения отсутствует в каталоге fingerprints."""

    def __init__(self, version: str) -> None:
        super().__init__(f"Could not find version {version} in registry")


class VersionAlreadyExistsError(ValueError):
    def __init__(self, version: str) -> None:
        super().__init__(f"Version {version} already exists in registry")
