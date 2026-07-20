from __future__ import annotations

import pytest

from pymax import Voice
from pymax.files import File, Photo
from pymax.formatting.markdown import Formatter


@pytest.mark.asyncio
async def test_file_raw_source_reads_sizes_and_chunks() -> None:
    file = File(raw=b"abcdef", name="data.bin")

    assert await file.read() == b"abcdef"
    assert await file.size() == 6
    assert [chunk async for chunk in file.iter_chunks(2)] == [
        b"ab",
        b"cd",
        b"ef",
    ]

    with pytest.raises(ValueError, match="size must be greater"):
        [chunk async for chunk in file.iter_chunks(0)]


@pytest.mark.asyncio
async def test_file_path_source_reads_sizes_and_chunks(tmp_path) -> None:
    path = tmp_path / "report.txt"
    path.write_bytes(b"report")
    file = File(path=str(path))

    assert file.name == "report.txt"
    assert await file.read() == b"report"
    assert await file.size() == 6
    assert [chunk async for chunk in file.iter_chunks(4)] == [b"repo", b"rt"]


def test_file_and_photo_validation_errors() -> None:
    with pytest.raises(ValueError, match="Path or Url or Raw"):
        File(name="empty.txt")

    with pytest.raises(ValueError, match="Only one"):
        File(raw=b"x", path="x.txt", name="x.txt")

    with pytest.raises(ValueError, match="Invalid photo extension"):
        Photo(raw=b"not image", name="bad.txt").validate_photo()


def test_voice_derives_name_from_path() -> None:
    assert Voice(path="recordings/voice.ogg").name == "voice.ogg"


def test_photo_url_validation_ignores_query_string() -> None:
    photo = Photo(url="https://example.com/image.jpg?quality=95&as=32x20")

    assert photo.validate_photo() == ("jpg", "image/jpeg")


def test_markdown_formatter_extracts_functional_entities() -> None:
    clean, entities = Formatter.format_markdown(
        "# Title\n> Quote\nHello **bold** and [site](https://example.com)"
    )

    assert clean == "Title\nQuote\nHello bold and site"
    assert [(entity.type, entity.from_, entity.length) for entity in entities] == [
        ("HEADING", 0, 5),
        ("QUOTE", 6, 5),
        ("STRONG", 18, 4),
        ("LINK", 27, 4),
    ]
    assert entities[-1].attributes is not None
    assert entities[-1].attributes.url == "https://example.com"
