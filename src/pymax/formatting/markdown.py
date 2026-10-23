from pymax.types.domain.element import Element, ElementAttributes


class Formatter:
    # Characters above this value are encoded as surrogate pairs in UTF-16,
    # occupying 2 code units instead of 1.
    BMP_MAX = 0xFFFF

    MARKERS = {
        "```": "CODE",
        "**": "STRONG",
        "__": "UNDERLINE",
        "~~": "STRIKETHROUGH",
        "`": "MONOSPACED",
        "_": "EMPHASIZED",
        "*": "EMPHASIZED",
    }

    MARKER_ORDER = ["```", "**", "__", "~~", "`", "_", "*"]

    @staticmethod
    def _code_units_len(text: str) -> int:
        return len(text.encode("utf-16-le")) // 2

    @staticmethod
    def _parse_link(
        text: str,
        i: int,
        clean_pos: int,
    ) -> tuple[str, str, int] | None:
        if not text.startswith("[", i):
            return None

        label_end = text.find("]", i + 1)
        if label_end == -1:
            return None

        if label_end + 1 >= len(text) or text[label_end + 1] != "(":
            return None

        url_start = label_end + 2
        url_end = text.find(")", url_start)
        if url_end == -1:
            return None

        label = text[i + 1 : label_end]
        url = text[url_start:url_end]

        if not label or not url:
            return None

        return label, url, url_end + 1

    @staticmethod
    def _is_intraword_single_marker(text: str, i: int, marker: str) -> bool:
        if marker != "_":
            return False
        if i == 0 or i + 1 >= len(text):
            return False
        return text[i - 1].isalnum() and text[i + 1].isalnum()

    @staticmethod
    def _find_closing_marker(
        text: str,
        marker: str,
        start: int,
        end: int | None = None,
    ) -> int:
        while True:
            closing_index = text.find(marker, start, len(text) if end is None else end)
            if closing_index == -1:
                return -1
            if not Formatter._is_intraword_single_marker(text, closing_index, marker):
                return closing_index
            start = closing_index + len(marker)

    @staticmethod
    def format_markdown(text: str) -> tuple[str, list[Element]]:
        clean_text = ""
        entities: list[Element] = []

        i = 0
        clean_pos = 0
        active: dict[str, int] = {}

        line_start = True

        while i < len(text):
            handled = False

            # LINK: [text](url)
            parsed_link = Formatter._parse_link(text, i, clean_pos)

            if parsed_link is not None:
                label, url, next_i = parsed_link

                start = clean_pos
                utf16_label_len = Formatter._code_units_len(label)

                clean_text += label
                clean_pos += utf16_label_len

                entities.append(
                    Element(
                        type="LINK",
                        from_=start,
                        length=utf16_label_len,
                        attributes=ElementAttributes(url=url),
                    )
                )

                i = next_i
                line_start = False
                continue

            # HEADING: # Title
            if line_start and text[i] == "#":
                start_i = i

                while i < len(text) and text[i] == "#":
                    i += 1

                if i < len(text) and text[i] == " ":
                    i += 1
                    start = clean_pos

                    while i < len(text) and text[i] != "\n":
                        ch = text[i]
                        clean_text += ch
                        i += 1
                        clean_pos += 2 if ord(ch) > Formatter.BMP_MAX else 1

                    length = clean_pos - start

                    if length > 0:
                        entities.append(
                            Element(
                                type="HEADING",
                                from_=start,
                                length=length,
                            )
                        )

                    line_start = False
                    continue

                i = start_i

            # QUOTE: > text
            if line_start and text[i] == ">":
                i += 1

                if i < len(text) and text[i] == " ":
                    i += 1

                start = clean_pos

                while i < len(text) and text[i] != "\n":
                    ch = text[i]
                    clean_text += ch
                    i += 1
                    clean_pos += 2 if ord(ch) > Formatter.BMP_MAX else 1

                length = clean_pos - start

                if length > 0:
                    entities.append(
                        Element(
                            type="QUOTE",
                            from_=start,
                            length=length,
                        )
                    )

                line_start = False
                continue

            for marker in Formatter.MARKER_ORDER:
                if not text.startswith(marker, i):
                    continue
                if Formatter._is_intraword_single_marker(text, i, marker):
                    continue

                marker_len = len(marker)

                if marker not in active:
                    if marker == "```":
                        closing_index = text.find(marker, i + marker_len)

                        if closing_index == -1 or closing_index == i + marker_len:
                            clean_text += marker
                            clean_pos += marker_len
                            i += marker_len
                            handled = True
                            break

                        active[marker] = clean_pos
                        i += marker_len

                        line_end = text.find("\n", i)
                        if line_end != -1 and line_end < closing_index:
                            i = line_end + 1

                        handled = True
                        break

                    end = text.find("\n", i + marker_len)
                    closing_index = Formatter._find_closing_marker(
                        text,
                        marker,
                        i + marker_len,
                        None if end == -1 else end,
                    )

                    if closing_index == -1 or closing_index == i + marker_len:
                        clean_text += marker
                        clean_pos += marker_len
                        i += marker_len
                        handled = True
                        break

                    active[marker] = clean_pos
                    i += marker_len
                    handled = True
                    break

                start = active[marker]
                length = clean_pos - start

                if length > 0:
                    entities.append(
                        Element(
                            type=Formatter.MARKERS[marker],
                            from_=start,
                            length=length,
                        )
                    )

                del active[marker]
                i += marker_len
                handled = True
                break

            if handled:
                line_start = False
                continue

            ch = text[i]
            clean_text += ch
            line_start = ch == "\n"

            i += 1
            clean_pos += 2 if ord(ch) > Formatter.BMP_MAX else 1

        return clean_text, entities
