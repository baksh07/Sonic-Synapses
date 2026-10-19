import os
import io
import time

from colorama import Fore
import numpy as np
import torch
from pydub import AudioSegment

import asyncio
from enum import Enum
from typing import AsyncGenerator, Optional

import numpy as np
from loguru import logger
from typing_extensions import TYPE_CHECKING, override

from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601
from pipecat.utils.tracing.service_decorators import traced_stt


if TYPE_CHECKING:
    try:
        from nemo.collections.asr.models import EncDecRNNTBPEModel
    except ModuleNotFoundError as e:
        logger.error(f"Exception: {e}")
        logger.error("In order to use Nemo you need to install pip install pipecat-ai[sandlogic]")
        raise Exception(f"Missing module: {e}")
    

class Model(Enum):
    RNNT = "nvidia/parakeet-rnnt-1.1b"
    RNNT_SMALL = "nvidia/parakeet-rnnt-0.6b"


class SandLogicSTTService(SegmentedSTTService):
    def __init__(
        self,
        model: str | Model = Model.RNNT,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        save_path: Optional[str] = '/mnt/data/DUMP/pipecat_latest/pipecat_version_2/pipecat/src/pipecat/services/sandlogic/audio_folder',
        language: Language = Language.EN,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._device: str = device
        self._model: Optional[EncDecRNNTBPEModel] = None
        self._save_path: str = save_path
        self.set_model_name(model if isinstance(model, str) else model.value)
        self._settings = {
            "language": language,
            "device": self._device,        
        }
        self._load()    

    def can_generate_metrics(self) -> bool:
        """Indicates whether this service can generate metrics.

        Returns:
            bool: True, as this service supports metric generation.
        """
        return True

    async def set_language(self, language: Language):
        """Set the language for transcription.

        Args:
            language: The Language enum value to use for transcription.
        """
        logger.info(f"Switching STT language to: [{language}]")
        self._settings["language"] = language

    def _load(self):
        """
        Loads the nemo model.
        """

        try:
            from nemo.collections.asr.models import EncDecRNNTBPEModel
            logger.debug(f"Loading the model")
            self._model = EncDecRNNTBPEModel.from_pretrained(
                model_name=self._model_name,
            ).to(self._device)
            self._model.eval()
            logger.debug(f"Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model {self._model_name}: {e}")
            logger.error(f"in order to use SandLogic STT you need to install pip install pipecat-ai[sandlogic]")
            self._model = None

    @traced_stt
    async def _handle_transcription(
        self, transcript: str, is_final: bool, language: Optional[Language] = None
    ):
        """Handle a transcription result with tracing."""
        pass

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        if not self._model:
            logger.error(f"{self} error: Whisper model not available")
            yield ErrorFrame("Whisper model not available")
            return
        
        await self.start_processing_metrics()
        await self.start_ttfb_metrics()

        audio_clip = AudioSegment.from_raw(io.BytesIO(audio), sample_width=2, frame_rate=16000,
                                               channels=1)
        filename = os.path.join(self._save_path, f"Stream_{time_now_iso8601}.wav")
        audio_clip.export(filename, format="wav")
        output_text = await asyncio.to_thread(
            self._model.transcribe,
            filename
        )
        logger.info(f"{self} output_text: {output_text}")
        text = output_text[0].text if output_text else ""

        await self.stop_ttfb_metrics()
        await self.stop_processing_metrics()
        
        if text:
            await self._handle_transcription(text, True, self._settings["language"])
            logger.debug(f"{self} transcription: {text}")
            yield TranscriptionFrame(
                text,
                self._user_id,
                time_now_iso8601(),
                self._settings["language"]
                )

    
