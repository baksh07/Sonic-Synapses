"""LingoVoice TTS service implementation."""

import base64
from typing import AsyncGenerator, Optional

import aiohttp
from loguru import logger

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts


class LingoVoiceTTSService(TTSService):
    """LingoVoice TTS service implementation.

    Provides integration with LingoVoice HTTP TTS server for text-to-speech
    synthesis. Handles JSON API responses with base64 encoded audio.
    """

    def __init__(
        self,
        *,
        base_url: str,
        aiohttp_session: aiohttp.ClientSession,
        voice_id: str = "Priya",
        output_format: str = "pcm_8000",
        sample_rate: Optional[int] = 8000,
        **kwargs,
    ):
        """Initialize the LingoVoice TTS service.

        Args:
            base_url: Base URL for the LingoVoice TTS HTTP server.
            aiohttp_session: aiohttp ClientSession for making HTTP requests.
            voice_id: Voice ID to use for synthesis (default: "Harsh").
            output_format: Audio output format (default: "pcm_8000").
            sample_rate: Output sample rate (default: 8000).
            **kwargs: Additional arguments passed to the parent TTSService.
        """
        super().__init__(sample_rate=sample_rate, **kwargs)

        if base_url.endswith("/"):
            base_url = base_url[:-1]

        self._base_url = base_url
        self._session = aiohttp_session
        self._voice_id = voice_id
        self._output_format = output_format
        self._settings = {
            "base_url": base_url,
            "voice_id": voice_id,
            "output_format": output_format,
        }

    def can_generate_metrics(self) -> bool:
        """Check if this service can generate processing metrics.

        Returns:
            True, as LingoVoice service supports metrics generation.
        """
        return True

    @traced_tts
    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Generate speech from text using LingoVoice HTTP API.

        Args:
            text: The text to convert to speech.

        Yields:
            Frame: Audio frames containing the synthesized speech and status frames.
        """
        logger.debug(f"{self}: Generating TTS [{text}]")
        
        # Construct the API endpoint URL
        url = f"{self._base_url}/LingoVoiceApiTTS/speech_to_text/"
        params = {
            "audio_string": "true",
            "voice_id": self._voice_id,
            "output_format": self._output_format,
        }
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        
        # Prepare the JSON payload
        payload = {"Text": text}

        try:
            await self.start_ttfb_metrics()

            async with self._session.post(url, params=params, json=payload, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(
                        f"{self} error getting audio (status: {response.status}, error: {error})"
                    )
                    yield ErrorFrame(
                        f"Error getting audio (status: {response.status}, error: {error})"
                    )
                    return

                await self.start_tts_usage_metrics(text)

                # Parse JSON response
                response_data = await response.json()
                
                # Extract base64 audio string from nested response structure
                try:
                    audio_string = response_data["output"]["audio_string"]["audio_string"]
                except KeyError as e:
                    logger.error(f"{self} error parsing response structure: {e}")
                    yield ErrorFrame(f"Error parsing response structure: {e}")
                    return

                # Decode base64 audio data
                try:
                    audio_data = base64.b64decode(audio_string)
                except Exception as e:
                    logger.error(f"{self} error decoding base64 audio: {e}")
                    yield ErrorFrame(f"Error decoding base64 audio: {e}")
                    return

                yield TTSStartedFrame()
                
                # Process audio data in chunks
                CHUNK_SIZE = self.chunk_size
                offset = 0
                
                # Remove WAV header if present (first 44 bytes for standard WAV)
                if audio_data.startswith(b"RIFF"):
                    audio_data = audio_data[44:]
                
                while offset < len(audio_data):
                    chunk = audio_data[offset:offset + CHUNK_SIZE]
                    if len(chunk) > 0:
                        await self.stop_ttfb_metrics()
                        yield TTSAudioRawFrame(chunk, self.sample_rate, 1)
                    offset += CHUNK_SIZE

        except Exception as e:
            logger.error(f"Error in run_tts: {e}")
            yield ErrorFrame(error=str(e))
        finally:
            logger.debug(f"{self}: Finished TTS [{text}]")
            await self.stop_ttfb_metrics()
            yield TTSStoppedFrame()