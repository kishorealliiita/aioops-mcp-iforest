from enum import Enum


class LogFormat(Enum):
    """Supported log formats."""

    JSON = "json"
    KEY_VALUE = "key_value"
    REGEX = "regex"
    CUSTOM = "custom"
