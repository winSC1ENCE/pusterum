"""Unit tests for the rich-text markup renderer (presentation/rich_text.py)."""

import pytest

from atem.presentation.rich_text import nl2br, render_rich_text


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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, ""),
        ("", ""),
        ("Eine Zeile", "Eine Zeile"),
        ("Atem\nRaum", "Atem<br>Raum"),
        ("A\r\nB\rC", "A<br>B<br>C"),
        ("\nnur innen\n", "nur innen"),
        ("Leer\n\nzeile", "Leer<br><br>zeile"),
    ],
)
def test_nl2br(source: str | None, expected: str) -> None:
    assert str(nl2br(source)) == expected


def test_nl2br_escapes_before_adding_breaks() -> None:
    html = str(nl2br('<script>alert(1)</script>\n<b onclick="x">fett</b>'))
    assert "<script>" not in html and "<b " not in html
    assert html == (
        "&lt;script&gt;alert(1)&lt;/script&gt;<br>&lt;b onclick=&#34;x&#34;&gt;fett&lt;/b&gt;"
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "Ausbildung am [IKP](https://www.ikp-therapien.com/)",
            '<p>Ausbildung am <a href="https://www.ikp-therapien.com/" target="_blank"'
            ' rel="noopener noreferrer">IKP</a></p>',
        ),
        (
            "[**fett**](https://a.ch/x_y_z*1*) und __u__",
            '<p><a href="https://a.ch/x_y_z*1*" target="_blank" rel="noopener noreferrer">'
            "<strong>fett</strong></a> und <u>u</u></p>",
        ),
        (
            "- [A&B](https://a.ch/?a=1&b=2)",
            '<ul><li><a href="https://a.ch/?a=1&amp;b=2" target="_blank"'
            ' rel="noopener noreferrer">A&amp;B</a></li></ul>',
        ),
    ],
)
def test_links(source: str, expected: str) -> None:
    assert str(render_rich_text(source)) == expected


@pytest.mark.parametrize(
    "source",
    [
        "[x](http://a.ch)",
        "[x](javascript:alert(1))",
        '[x](https://a.ch" onmouseover="alert(1))',
        "[x](https://a.ch/<script>)",
        "[x](https://a b)",
        "[x](https:)",
    ],
)
def test_unsafe_links_stay_text(source: str) -> None:
    html = str(render_rich_text(source))
    assert "<a " not in html
    assert "<script>" not in html
