from .base import Filter
from .magic import MagicFilter
from .presets import Command, Forwarded, FromMe, HasAttachment, Reply

F = MagicFilter()

__all__ = ("Command", "Filter", "Forwarded", "FromMe", "HasAttachment", "MagicFilter", "Reply")
