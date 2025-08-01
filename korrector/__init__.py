"""Korrector package: tools for Komga database and ComicInfo.xml correction."""

__all__ = ["__version__", "setup_logging"]

import logging
from importlib.metadata import version

from colorlog import ColoredFormatter

__version__ = version("korrector")


# TODO(mpickle): add a log file named korrector.log somewhere
# https://github.com/pickled-dev/korrector/issues/2
def setup_logging() -> None:
    """Set up logging for the korrector package."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        ColoredFormatter(
            "%(log_color)s%(levelname)s:%(name)s:%(message)s",
            datefmt=None,
            reset=True,
        ),
    )
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
