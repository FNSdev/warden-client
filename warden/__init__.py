import logging.config

from .log import LOGGING
from .warden import Warden

logging.config.dictConfig(LOGGING)

__all__ = [
    'Warden'
]
