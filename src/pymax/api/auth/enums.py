from enum import Enum


class AuthType(str, Enum):
    START_AUTH = "START_AUTH"
    CHECK_CODE = "CHECK_CODE"
    REGISTER = "REGISTER"
    RESEND = "RESEND"
    LOGIN = "LOGIN"


class ProfileOptions(int, Enum):
    """Битовые/числовые признаки профиля, связанные с 2FA."""

    ESIA_VERIFIED_FLAG = 1
    SECOND_FACTOR_PASSWORD_ENABLED = 2
    SECOND_FACTOR_HAS_EMAIL = 3
    SECOND_FACTOR_HAS_HINT = 4


class TwoFactorAction(int, Enum):
    """Действия 2FA, передаваемые в expectedCapabilities."""

    SET_PASSWORD = 0
    UPDATE_PASSWORD = 1
    RESTORE_PASSWORD = 2
    HINT = 3
    EMAIL = 4
    REMOVE_2FA = 5
