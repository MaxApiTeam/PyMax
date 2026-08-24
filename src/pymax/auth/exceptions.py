class PasswordAttemptsExceededError(Exception):
    """Исчерпан лимит попыток ввода пароля 2FA.

    Наследуется напрямую от ``Exception`` и не перехватывается как
    ``PyMaxError``.
    """

    def __init__(self) -> None:
        super().__init__("2FA password attempts exhausted")
