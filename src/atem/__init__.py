"""Atemtherapie Webapplikation."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Single source of truth: [project].version in pyproject.toml (TDR-0009).
    __version__ = version("atem")
except PackageNotFoundError:  # pragma: no cover - only when running from an uninstalled tree
    __version__ = "0.0.0"
