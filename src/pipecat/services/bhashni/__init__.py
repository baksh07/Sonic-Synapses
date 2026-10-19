import sys 
from pipecat.services import DeprecatedModuleProxy


from .stt import *
from .tts import *

sys.modules[__name__] = DeprecatedModuleProxy(globals(), "bhashini", "bhashini.[stt,tts]")  # type: ignore