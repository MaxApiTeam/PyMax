import asyncio
import getpass
from typing import Protocol

import qrcode


class SmsCodeProvider(Protocol):
    """Протокол получения SMS-кода.

    Реализуйте его, если код приходит не из консоли: из UI, очереди, callback
    или внешнего сервиса.
    """

    async def get_code(self, phone: str) -> str:
        """Возвращает SMS-код для указанного телефона."""
        ...


class ConsoleSmsCodeProvider:
    """Консольный provider SMS-кода.

    При авторизации печатает prompt и читает код через ``input``.
    """

    async def get_code(self, phone: str) -> str:
        """Запрашивает SMS-код в консоли.

        Args:
            phone: Телефон, для которого запрошен код.

        Returns:
            Введенный пользователем код.
        """
        prompt = f"Enter SMS code for {phone}: "
        return (await asyncio.to_thread(input, prompt)).strip()


class PasswordProvider(Protocol):
    """Протокол получения пароля 2FA.

    Вызывается только если Max потребовал дополнительный пароль после SMS-кода.
    """

    async def get_password(self, hint: str | None = None) -> str:
        """Возвращает пароль 2FA с учетом подсказки, если она есть."""
        ...


class ConsolePasswordProvider:
    """Консольный provider пароля 2FA.

    Читает пароль через ``getpass`` и не выводит его на экран.
    """

    async def get_password(self, hint: str | None = None) -> str:
        """Запрашивает пароль 2FA в консоли.

        Args:
            hint: Подсказка пароля от Max, если сервер ее прислал.

        Returns:
            Введенный пароль.
        """
        prompt = "Enter 2FA password"
        if hint:
            prompt += f" (hint: {hint})"
        prompt += ": "
        return (await asyncio.to_thread(getpass.getpass, prompt)).strip()


class QrHandler(Protocol):
    """Протокол показа QR-ссылки пользователю.

    Handler должен только показать ``qr_url``. Подтверждение и polling делает
    ``QrAuthFlow``.
    """

    async def show_qr(self, qr_url: str) -> None:
        """Показывает пользователю QR-ссылку для подтверждения входа."""
        ...


#    async def on_confirmed(self) -> None: ...


class ConsoleQrHandler:
    """Консольный QR handler.

    Печатает QR-код ASCII-графикой в терминал.
    """

    async def show_qr(self, qr_url: str) -> None:
        """Показывает QR-ссылку в терминале.

        Args:
            qr_url: Ссылка, которую нужно открыть или отсканировать.

        Returns:
            ``None``.
        """
        qr = qrcode.QRCode()
        qr.add_data(qr_url)
        qr.print_ascii()


class EmailCodeProvider(Protocol):
    """Протокол получения кода подтверждения email для настройки 2FA."""

    async def get_code(self, email: str) -> str:
        """Возвращает код подтверждения, отправленный на email."""
        ...


class ConsoleEmailCodeProvider:
    """Консольный provider кода подтверждения email для 2FA.

    Блокирующий ``input()`` выполняется в worker thread и не останавливает
    asyncio event loop.
    """

    async def get_code(self, email: str) -> str:
        """Запрашивает email-код в консоли.

        Args:
            email: Адрес, на который Max отправил код подтверждения.

        Returns:
            Введенный пользователем код.
        """
        return (await asyncio.to_thread(input, f"Enter 2FA email code for {email}: ")).strip()
