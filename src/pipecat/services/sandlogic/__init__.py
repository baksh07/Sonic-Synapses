import sys

from pipecat.services import DeprecatedModuleProxy

from .tts import *
from .stt import *

sys.modules[__name__] = DeprecatedModuleProxy(globals(), "sandlogic", "sandlogic[stt,tts]")
