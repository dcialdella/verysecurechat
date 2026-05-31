import logging
import sys
from typing import Optional

_LOG_INITIALIZED: bool = False


def setup_logging(
    name: str = "VerySecureChat",
    debug: bool = False,
    log_file: Optional[str] = None,
) -> logging.Logger:
    global _LOG_INITIALIZED
    if _LOG_INITIALIZED:
        return logging.getLogger(name)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    _LOG_INITIALIZED = True
    return logging.getLogger(name)
