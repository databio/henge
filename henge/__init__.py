# Project configuration, particularly for logging.

import logmuse
from ._version import __version__
from .henge import *

__classes__ = ["Henge"]
__all__ = __classes__ + ["connect_mongo"]

logmuse.init_logger("henge")
