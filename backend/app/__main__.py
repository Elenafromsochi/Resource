from __future__ import annotations

import logging
import os

from colorlog import ColoredFormatter
import uvicorn


def configure_logging() -> None:
    log_level_name = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_level = getattr(logging, log_level_name, logging.DEBUG)

    color_handler = logging.StreamHandler()
    color_handler.setLevel(log_level)
    color_handler.setFormatter(
        ColoredFormatter(
            "%(log_color)s%(asctime)s.%(msecs)03d [%(levelname).1s] "
            "(%(name)s.%(funcName)s:%(lineno)d): %(message)s",
            log_colors={
                "DEBUG": "light_blue",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
            datefmt="%Y-%m-%d %H:%M:%S",
        ),
    )

    logging.basicConfig(level=log_level, handlers=[color_handler])
    logging.getLogger("telethon").setLevel(logging.INFO)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).setLevel(log_level)


def main() -> None:
    configure_logging()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "debug").lower()
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
