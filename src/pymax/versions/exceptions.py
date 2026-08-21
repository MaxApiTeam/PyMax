class VersionNotFoundError(ValueError):
    def __init__(self, version: str) -> None:
        super().__init__(f"Could not found version {version} in registry")


class VersionAlreadyExistsError(ValueError):
    def __init__(self, version: str) -> None:
        super().__init__(f"Version {version} already exists in registry")
