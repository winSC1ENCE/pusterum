"""Unit tests for the rich-text markup renderer (presentation/rich_text.py)."""

import pytest

from atem.presentation.rich_text import render_rich_text


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, ""),
        ("   ", ""),
        (
            "**fett** *kursiv* __unten__",
            "<p><strong>fett</strong> <em>kursiv</em> <u>unten</u></p>",
        ),
        ("Zeile 1\nZeile 2", "<p>Zeile 1<br>Zeile 2</p>"),
        ("Absatz 1\n\nAbsatz 2", "<p>Absatz 1</p><p>Absatz 2</p>"),
        (
            "Intro\n- eins\n• zwei\nSchluss",
            "<p>Intro</p><ul><li>eins</li><li>zwei</li></ul><p>Schluss</p>",
        ),
        ("2 * 3 * 4", "<p>2 * 3 * 4</p>"),
        ("a\r\n\r\nb", "<p>a</p><p>b</p>"),
    ],
)
def test_render_rich_text(source: str | None, expected: str) -> None:
    assert str(render_rich_text(source)) == expected


def test_html_is_escaped_before_formatting() -> None:
    html = str(render_rich_text('**<img src=x onerror="alert(1)">**'))
    assert html == "<p><strong>&lt;img src=x onerror=&#34;alert(1)&#34;&gt;</strong></p>"
