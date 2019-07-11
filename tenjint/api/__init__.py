from enum import Enum
import platform
import logging

_arch = platform.machine()

class Arch(Enum):
    UNSUPPORTED = 0
    X86_64 = 1
    AARCH64 = 2

from .api import *
if _arch == "x86_64":
    arch = Arch.X86_64
    from .api_x86_64 import *
elif _arch == "aarch64":
    arch = Arch.AARCH64
    from .api_aarch64 import *
else:
    raise RuntimeError("Unrecognized Architecture")

try:
    from .tenjintapi import *
except ImportError as e:
    initialized = False
    logging.warning("Unable to import tenjintapi ({})".format(e))
else:
    initialized = True
    if _arch == "x86_64":
        from .tenjintapi_x86_64 import *
    elif _arch == "aarch64":
        from .tenjintapi_aarch64 import *
    else:
        raise RuntimeError("Unrecognized Architecture")
