# PyMax

Python-библиотека для Max API.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Package](https://img.shields.io/badge/package-maxapi--python-orange.svg)](https://pypi.org/project/maxapi-python/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/maxapi-python?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/maxapi-python)

> [!WARNING]
> PyMax использует неофициальный внутренний API Max. API может измениться без
> предупреждения, а использование библиотеки может нарушать условия сервиса.
> Вы используете PyMax на свой риск; авторы и контрибьюторы не несут
> ответственности за блокировки аккаунтов, потерю данных или другие последствия.

## Что это

**PyMax** - асинхронная Python-библиотека для внутреннего API Max. Она умеет
авторизоваться в аккаунте, слушать события, отправлять сообщения, работать с
чатами, пользователями, файлами, сессиями и доменными типами Max через TCP или
WebSocket.

## Возможности

- Авторизация по телефону и SMS-коду через `Client`.
- QR-авторизация web-клиента через `WebClient`.
- Роутеры, фильтры, `on_start`, raw-события и typed events.
- Сообщения: отправка и планирование, ответы, реакции, pin, read, delete и история.
- Чаты, группы, участники, invite-ссылки и настройки групп.
- Пользователи, контакты, профиль, папки, активные сессии и 2FA.
- Вложения: `Photo`, `File`, `Video`, `Voice`, `VideoNote`.
- Выбор версии mobile-клиента с локальным или обновляемым каталогом fingerprints.
- SQLite-сессии, sync-state, reconnect и debug-логи.
- Pydantic-модели и удобные domain-объекты.

## Установка

Требуется Python 3.10 или новее.

```bash
pip install -U maxapi-python
```

Через `uv`:

```bash
uv add -U maxapi-python
```

Напрямую из репозитория:

```bash
pip install git+https://github.com/MaxApiTeam/PyMax.git
```

## Быстрый старт

`Client` использует TCP-соединение. При первом запуске PyMax попросит SMS-код
и сохранит сессию в SQLite-файл; дальше этот файл используется автоматически.

```python
import asyncio

from pymax import Client, Message

client = Client(
    phone="+79990000000",
    work_dir="cache",
    session_name="main.db",
)


@client.on_start()
async def on_start(client: Client) -> None:
    print("Клиент запущен")
    print("Ваш ID:", client.me.contact.id if client.me else "unknown")


@client.on_message()
async def on_message(message: Message, client: Client) -> None:
    print(message.chat_id, message.sender, message.text)

    if message.chat_id is not None and message.text:
        await message.answer("Привет от PyMax")


async def main() -> None:
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
```

## WebClient

`WebClient` использует WebSocket и QR-авторизацию:

```python
import asyncio

from pymax import WebClient

client = WebClient(work_dir="cache", session_name="web.db")


@client.on_start()
async def on_start(client: WebClient) -> None:
    print("Web-клиент запущен")


asyncio.run(client.start())
```

## Роутеры

Обработчики можно регистрировать на клиенте или вынести в отдельный роутер.
Handler всегда принимает событие и клиента: `(event, client)`.

```python
from pymax import Client, ClientRouter, Message

router = ClientRouter()


def is_start(message: Message) -> bool:
    return message.text == "/start"


@router.on_message(is_start)
async def start(message: Message, client: Client) -> None:
    await message.answer("Готово")


client = Client(phone="+79990000000", work_dir="cache")
client.include_router(router)
```

## Куда дальше

- [Getting Started](docs/getting-started.rst) - первый запуск и сессии.
- [Client](docs/client.rst) - жизненный цикл клиента, reconnect и sync-state.
- [Router](docs/router.rst) - роутеры, фильтры и raw events.
- [Messages](docs/messages.rst) - сообщения, реакции, история и вложения.
- [Files](docs/files.rst) - отправка и скачивание файлов.
- [FAQ](docs/faq.rst) и [Troubleshooting](docs/troubleshooting.rst) - частые
  проблемы.

Опубликованная документация:

- [docs.pymax.org](https://docs.pymax.org/)
- [DeepWiki](https://deepwiki.com/MaxApiTeam/PyMax)

## Разработка

```bash
uv sync --all-groups
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest
uv run python -c "import pymax; print(pymax.__all__)"
uv run sphinx-build -b html docs docs/_build/html
```

## Ссылки

- [GitHub](https://github.com/MaxApiTeam/PyMax)
- [PyPI](https://pypi.org/project/maxapi-python/)
- [Telegram](https://t.me/pymax_news)

## Лицензия

Проект распространяется под лицензией MIT. Подробности см. в [LICENSE](LICENSE).

## Авторы

- [ink](https://github.com/ink-developer) - основной разработчик, исследование
  API и документация.
- [noxzion](https://github.com/noxzion) - оригинальный автор проекта.
