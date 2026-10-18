"""Structured Logging Configuration using structlog."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, TextIO

import structlog

if TYPE_CHECKING:
    from structlog.types import Processor


def setup_logging(is_dev: bool = True, stream: TextIO | None = None) -> None:
    """Configure structlog and standard logging (to ``stream``, default stdout)."""
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # structlog only *prepares* the event dict; the stdlib ProcessorFormatter renders it
    # exactly once (JSON in production, coloured console locally) – also for foreign logs
    # (granian, alembic, litestar).
    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer: Processor = (
        structlog.dev.ConsoleRenderer(colors=True)
        if is_dev
        else structlog.processors.JSONRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *([] if is_dev else [structlog.processors.dict_tracebacks]),
            renderer,
        ],
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if is_dev else logging.INFO)

    # Suppress verbose loggers
    for noisy in ["sqlalchemy.engine", "httpcore", "httpx"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
