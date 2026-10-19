import base64
import wave
import io
import audioop
import aiohttp
from typing import AsyncGenerator
from scipy.io import wavfile
import numpy as np
from loguru import logger
from pipecat.frames.frames import (
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    ErrorFrame,
    Frame,
)
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts


class BhashiniTTSService(TTSService):
    def __init__(
        self,
        *,
        aiohttp_session: aiohttp.ClientSession,
        sample_rate: int = 8000,
        gender: str = "female",
        language: str = "hi",  
        service_id: str = "ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4",
        auth_token: str = "",
        **kwargs,
    ):
        super().__init__(sample_rate=sample_rate, **kwargs)
        self.session = aiohttp_session
        self.gender = gender
        self.language = language
        self.service_id = service_id
        self.auth_token = auth_token
        self.api_url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    def can_generate_metrics(self) -> bool:
        return True



    def _convert_32bit_wav_to_16bit_pcm(self, wav_bytes: bytes) -> bytes:
        # Read WAV using scipy which supports format 3 (IEEE float)
        sample_rate, data = wavfile.read(io.BytesIO(wav_bytes))

        if sample_rate != self.sample_rate:
            raise ValueError(f"Unexpected sample rate: {sample_rate}")

        if data.dtype == np.float32:
            # Convert float32 [-1, 1] to int16 PCM
            data = np.clip(data, -1.0, 1.0)
            data = (data * 32767).astype(np.int16)
        elif data.dtype == np.int32:
            # Convert int32 to int16
            data = (data >> 16).astype(np.int16)
        elif data.dtype != np.int16:
            raise ValueError(f"Unsupported WAV dtype: {data.dtype}")

        return data.tobytes()


    @traced_tts
    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        logger.debug(f"[BhashiniTTS] Generating speech for: {text}")
        yield TTSStartedFrame()

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": self.language},
                        "serviceId": self.service_id,
                        "gender": self.gender,
                        "samplingRate": self.sample_rate,
                    },
                }
            ],
            "inputData": {
                "input": [{"source": text}],
            },
        }

        headers = {
            "Authorization": self.auth_token,
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

        try:
            await self.start_ttfb_metrics()

            async with self.session.post(self.api_url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.error(f"Bhashini TTS failed: {resp.status} - {error}")
                    yield ErrorFrame(f"Bhashini TTS failed: {error}")
                    return

                response_json = await resp.json()
                audio_base64 = response_json["pipelineResponse"][0]["audio"][0]["audioContent"]
                wav_bytes = base64.b64decode(audio_base64)
                pcm_bytes = self._convert_32bit_wav_to_16bit_pcm(wav_bytes)

                await self.start_tts_usage_metrics(text)
                await self.stop_ttfb_metrics()

                # ✅ Send full audio as one frame
                yield TTSAudioRawFrame(pcm_bytes, self.sample_rate, 1)

        except Exception as e:
            logger.exception("[BhashiniTTS] Exception in run_tts")
            yield ErrorFrame(str(e))

        finally:
            yield TTSStoppedFrame()
            await self.stop_ttfb_metrics()
            logger.debug("[BhashiniTTS] Finished synthesis")
