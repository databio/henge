# Project configuration, particularly for logging.

import logmuse
from ._version import __version__
from .henge import *

__classes__ = ["Henge", "MongoDict"]
__all__ = __classes__ + []

logmuse.init_logger("henge")
