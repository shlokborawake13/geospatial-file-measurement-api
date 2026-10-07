import logging
import sys
from app.core.config import settings

# Third-party libraries that produce verbose / credential-leaking output at DEBUG
_NOISY_LOGGERS = (
    "httpcore",
    "httpcore.http11",
    "httpcore.http2",
    "httpcore.connection",
    "httpx",
    "hpack",
    "hpack.hpack",
    "hpack.table",
    "uvicorn.access",
    "uvicorn.error",
    "postgrest",
    "gotrue",
    "realtime",
    "storage3",
    "multipart",
    "multipart.multipart",
)


def setup_logging() -> None:
    """Configure application-wide structured logging."""
    # Application logs: DEBUG in development, INFO in production
    app_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(app_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Force noisy / credential-leaking third-party loggers to WARNING regardless
    # of the application log level.  This prevents httpcore/hpack from printing
    # raw HTTP headers (including apikey / authorization) to stdout.
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
