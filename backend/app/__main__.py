from __future__ import annotations

import logging
import os
import sys

import uvicorn


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\x1b[36m",
        logging.INFO: "\x1b[32m",
        logging.WARNING: "\x1b[33m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[35m",
    }
    RESET = "\x1b[0m"

    def __init__(self, use_color: bool) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        original_level = record.levelname
        if self.use_color:
            color = self.COLORS.get(record.levelno)
            if color:
                record.levelname = f"{color}{record.levelname}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original_level


def configure_logging() -> None:
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    use_color = sys.stdout.isatty() and os.getenv("NO_COLOR") is None

    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter(use_color=use_color))

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)
    root.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.propagate = True
        logger.setLevel(log_level)


def main() -> None:
    configure_logging()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        access_log=True,
        log_config=None,
    )


if __name__ == "__main__":
    main()
