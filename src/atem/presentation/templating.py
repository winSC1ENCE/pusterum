"""Jinja environment customisation: cache-busting asset versions and helper filters."""

import hashlib
from pathlib import Path
from typing import Any

from litestar.plugins.jinja import JinjaTemplateEngine

from atem.infrastructure.database.seed.content_defaults import content_default, count_numbered_keys
from atem.presentation.rich_text import render_rich_text

STATIC_DIR = Path(__file__).parent / "static"
_VERSIONED_ASSETS = ("css", "js")


def compute_asset_version(static_dir: Path = STATIC_DIR) -> str:
    """Hash of all CSS/JS files – identical in every worker, changes with each deployment."""
    digest = hashlib.sha256()
    for folder in _VERSIONED_ASSETS:
        for file in sorted((static_dir / folder).rglob("*")):
            if file.is_file():
                digest.update(file.name.encode())
                digest.update(file.read_bytes())
    return digest.hexdigest()[:12]


def content_hash(value: Any) -> str:
    """Short hash of a string (e.g. the theme CSS) for cache-busting query parameters."""
    if not value:
        return "0"
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def content_value(content_blocks: dict[str, Any] | None, key: str) -> str:
    """Current text of a content block (DB) with the seed default as fallback."""
    block = (content_blocks or {}).get(key)
    return str(block.current_content) if block else content_default(key)


def numbered_content(
    content_blocks: dict[str, Any] | None, prefix: str, *fields: str
) -> list[dict[str, str]]:
    """Numbered entries ``<prefix><n>.<field>`` as dicts, e.g. ``kids.variant_1.title``."""
    count = count_numbered_keys(prefix, f".{fields[0]}")
    return [
        {field: content_value(content_blocks, f"{prefix}{n}.{field}") for field in fields}
        for n in range(1, count + 1)
    ]


def configure_jinja(engine: JinjaTemplateEngine) -> None:
    """Register globals and filters on the Jinja environment."""
    engine.engine.globals["asset_version"] = compute_asset_version()
    engine.engine.globals["content_default"] = content_default
    engine.engine.globals["count_numbered_keys"] = count_numbered_keys
    engine.engine.globals["content_value"] = content_value
    engine.engine.globals["numbered_content"] = numbered_content
    engine.engine.filters["content_hash"] = content_hash
    engine.engine.filters["rich_text"] = render_rich_text
