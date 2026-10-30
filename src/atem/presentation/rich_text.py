"""Safe formatting for rich-text content blocks (block type ``rich_text``).

The practice owner writes a tiny Markdown subset (toolbar in the inline editor). The source
is HTML-escaped **first**, so the only tags that can reach the page are the ones produced here:

* ``**fett**`` → ``<strong>``, ``*kursiv*`` → ``<em>``, ``__unterstrichen__`` → ``<u>``
* ``[Text](https://…)`` → external link (``https`` only, new tab, ``rel="noopener noreferrer"``)
* lines starting with ``- `` or ``• `` → bullet list
* blank line → new paragraph, single line break → ``<br>``
"""

import re

from markupsafe import Markup, escape

_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_UNDERLINE = re.compile(r"__(?=\S)(.+?)(?<=\S)__")
_ITALIC = re.compile(r"\*(?=\S)(.+?)(?<=\S)\*")
_BULLET = re.compile(r"^[-•]\s+")
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n")
# Matched on the raw source: the URL must be https and must not contain characters that could
# leave the attribute or the markup (quotes, angle brackets, brackets, whitespace, backslash).
_LINK = re.compile(r"\[([^\[\]\n]+)\]\((https://[^\s()<>\"'\\\[\]]+)\)")


def _format(text: str) -> str:
    html = str(escape(text))
    html = _BOLD.sub(r"<strong>\1</strong>", html)
    html = _UNDERLINE.sub(r"<u>\1</u>", html)
    return _ITALIC.sub(r"<em>\1</em>", html)


def _inline(text: str) -> str:
    """Format one line; links are split off first so ``_``/``*`` in URLs stay untouched."""
    html: list[str] = []
    position = 0
    for link in _LINK.finditer(text):
        html.append(_format(text[position : link.start()]))
        html.append(
            f'<a href="{escape(link.group(2))}" target="_blank" rel="noopener noreferrer">'
            f"{_format(link.group(1))}</a>"
        )
        position = link.end()
    html.append(_format(text[position:]))
    return "".join(html)


def _render_block(block: str) -> str:
    """One paragraph block: plain lines become a <p> (with <br>), bullet lines a <ul>."""
    html: list[str] = []
    lines: list[str] = []
    items: list[str] = []

    def flush() -> None:
        if lines:
            html.append("<p>" + "<br>".join(lines) + "</p>")
            lines.clear()
        if items:
            html.append("<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>")
            items.clear()

    for raw in block.split("\n"):
        line = raw.strip()
        if not line:
            continue
        bullet = _BULLET.match(line)
        if bullet:
            if lines:
                flush()
            items.append(_inline(line[bullet.end() :]))
        else:
            if items:
                flush()
            lines.append(_inline(line))
    flush()
    return "".join(html)


def render_rich_text(source: str | None) -> Markup:
    """Convert the formatting markup to HTML (everything else is escaped)."""
    if not source or not source.strip():
        return Markup("")
    text = source.replace("\r\n", "\n").replace("\r", "\n").strip()
    html = "".join(_render_block(block) for block in _PARAGRAPH_BREAK.split(text))
    return Markup(html)  # nosec B704 - every text fragment is escaped in _inline()


_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def nl2br(source: str | None) -> Markup:
    """Plain text with line breaks for ``text``/``textarea`` blocks (TDR-0011).

    Escapes everything first and only then turns each line break into ``<br>``, so a stored
    value can never inject markup. Leading/trailing breaks are dropped.
    """
    if not source:
        return Markup("")
    # Markup.join escapes every line itself; only the literal "<br>" is trusted markup.
    return Markup("<br>").join(_LINE_BREAK.split(source.strip("\r\n")))
