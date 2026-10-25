from typing import Final, TypeAlias

from typing_extensions import override


class MissingType:
    __slots__ = ()

    @override
    def __repr__(self) -> str:
        return "MISSING"


MISSING: Final = MissingType()

Missing: TypeAlias = MissingType
