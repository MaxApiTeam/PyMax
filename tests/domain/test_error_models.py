from __future__ import annotations

from pymax.types.domain import MaxApiError


def test_max_api_error_without_message_keeps_error_code() -> None:
    """Сервер иногда возвращает ошибочный кадр без поля ``message``
    (например ``service.unavailable`` при временном сбое). Такой кадр
    обязан разобраться — иначе реальный код ошибки подменяется
    ``unknown_error`` в ``App._build_api_error``."""
    error = MaxApiError.model_validate({"error": "service.unavailable"})

    assert error.error == "service.unavailable"
    assert error.message is None
    assert error.title is None
    assert error.localized_message is None


def test_max_api_error_partial_message_fields() -> None:
    error = MaxApiError.model_validate(
        {"error": "user.not.found", "title": "Не найдено"}
    )

    assert error.error == "user.not.found"
    assert error.title == "Не найдено"
    assert error.message is None


def test_max_api_error_full_payload_unchanged() -> None:
    error = MaxApiError.model_validate(
        {
            "error": "user.not.found",
            "message": "user missing",
            "title": "Not found",
            "localizedMessage": "Пользователь не найден",
        }
    )

    assert error.error == "user.not.found"
    assert error.message == "user missing"
    assert error.title == "Not found"
    assert error.localized_message == "Пользователь не найден"
