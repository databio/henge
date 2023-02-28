# Project configuration, particularly for logging.

import logmuse
from ._version import __version__
from .henge import *

__classes__ = ["Henge"]
__all__ = __classes__ + ["connect_mongo", "split_schema", "NotFoundException", "canonical_str"]

logmuse.init_logger("henge", propagate=True)
