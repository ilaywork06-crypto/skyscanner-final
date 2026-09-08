"""
Logging bootstrap shared by the services, emitting a single structured line per record with UTC timestamps.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import logging
import sys
import time

# ----- CONSTS ----- #

LOG_FORMAT: str = "%(asctime)s.%(msecs)03dZ | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S"

# ----- FUNCTIONS ----- #


def configure_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """
    Install a single stream handler on the root logger and hand back the logger of the calling service.

    :param service_name: Name the service logs under.
    :param level: Lowest severity that is emitted.
    :return: The logger dedicated to the calling service.
    """
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    formatter.converter = time.gmtime
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())

    return logging.getLogger(service_name)


def get_logger(name: str) -> logging.Logger:
    """
    Fetch a named logger that inherits the handler installed by the bootstrap.

    :param name: Name of the module asking for a logger.
    :return: The logger registered under the given name.
    """
    return logging.getLogger(name)
