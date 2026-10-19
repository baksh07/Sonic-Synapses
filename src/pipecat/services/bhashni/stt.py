# bhashini_stt_service.py

import base64
import json
import aiohttp

from loguru import logger
from typing import AsyncGenerator, Optional, Any

from pipecat.frames.frames import TranscriptionFrame
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601


class BhashiniSTTService(SegmentedSTTService):
    """
    STT service using Bhashini POST API (base64 audio to text).
    """

    def __init__(self, *, api_key: str, service_id: str, sample_rate: int = 16000, **kwargs):
        super().__init__(sample_rate=sample_rate, **kwargs)
        self.api_key = api_key
        self.service_id = service_id
        self.url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    async def run_stt(self, audio: bytes) -> AsyncGenerator[TranscriptionFrame, None]:
        try:
            audio_base64 = base64.b64encode(audio).decode("utf-8")

            payload = {
                "pipelineTasks": [
                    {
                        "taskType": "asr",
                        "config": {
                            "language": {"sourceLanguage": "hi"},
                            "serviceId": self.service_id,
                            "audioFormat": "flac",
                            "samplingRate": self.sample_rate,
                        },
                    }
                ],
                "inputData": {
                    "audio": [{"audioContent": audio_base64}]
                },
            }

            headers = {
                "Accept": "*/*",
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Bhashini STT request failed with status {resp.status}")
                        return

                    response_json = await resp.json()
                    transcript = (
                        response_json.get("pipelineResponse", [{}])[0]
                        .get("output", [{}])[0]
                        .get("source", "")
                    )

                    if not transcript:
                        logger.warning("No transcription returned from Bhashini.")
                        return

                    logger.debug(f"Bhashini ASR Transcript: {transcript}")

                    yield TranscriptionFrame(
                        transcript,                  # ✅ positional arg for text
                        self._user_id,               # ✅ user_id
                        time_now_iso8601(),          # ✅ timestamp
                        Language.HI,                 # ✅ language enum
                        response_json,               # ✅ full result
                    )

        except Exception as e:
            logger.exception(f"Error during Bhashini STT: {e}")
