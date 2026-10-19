#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
import os
import sys
from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams
from dotenv import load_dotenv
from loguru import logger
from pipecat.services.openai.base_llm import BaseOpenAILLMService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.audio.interruptions.min_words_interruption_strategy import MinWordsInterruptionStrategy
# from pipecat.services.gemini_multimodal_live import GeminiMultimodalLiveLLMService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from deepgram import LiveOptions
# from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.audio.filters.noisereduce_filter import NoisereduceFilter
from pipecat.frames.frames import FunctionCallResultProperties
from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
from pipecat.processors.user_idle_processor import UserIdleProcessor
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
import os
from pipecat.frames.frames import EndFrame, LLMMessagesFrame, TTSSpeakFrame
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from pipecat.utils.tracing.setup import setup_tracing
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.frames.frames import TTSSpeakFrame, EndFrame
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.whisper.stt import WhisperSTTService
import datetime
import wave
from pipecat.frames.frames import EndTaskFrame, EndFrame, TextFrame, BotInterruptionFrame
import io
import aiofiles

from pipecat.services.bhashni.stt import BhashiniSTTService
from pipecat.services.bhashni.tts import BhashiniTTSService
import aiohttp

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

async def save_audio_file(audio: bytes, filename: str, sample_rate: int, num_channels: int):
    """Save audio data to a WAV file."""
    if len(audio) > 0:
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wf:
                wf.setsampwidth(2)
                wf.setnchannels(num_channels)
                wf.setframerate(sample_rate)
                wf.writeframes(audio)
            async with aiofiles.open(filename, "wb") as file:
                await file.write(buffer.getvalue())
        logger.info(f"Audio saved to {filename}")

# async def end_conversation(params: FunctionCallParams):
#     await params.llm.push_frame(TTSSpeakFrame("Have a nice day!"))

#     # Signal that the task should end after processing this frame
#     await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)



# Step 1: Initialize OpenTelemetry with your chosen exporter
exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",  # Jaeger or other collector endpoint
    insecure=True,
)

setup_tracing(
    service_name="sam vande bharat bank",
    exporter=exporter,
    console_export=False,  # Set to True for debug output
)


# Create audio buffer processor with default settings
audiobuffer = AudioBufferProcessor(
    num_channels=1,               # 1 for mono, 2 for stereo (user left, bot right)
    enable_turn_audio=False,      # Enable per-turn audio recording
    user_continuous_stream=True,  # User has continuous audio stream
)




SYSTEM_INSTRUCTION = f"""
You are a compassionate female police officer responsible for taking complaints and registering them as FIRs (First Information Reports). Your role is to gather necessary information while being sensitive to the complainant's emotional state. Many complainants may be distressed, traumatized, or vulnerable, so approach each interaction with empathy and professionalism as a woman officer.
TTS SPEECH FORMAT RULE:
Whenever presenting any number (amounts, dates, account digits, overdue days, etc.), convert them into spoken words.
Example:
₹25,000 → "twenty five thousand rupees"
5 days → "five days"
16 July 2025 → "sixteenth July two thousand twenty five"
Account ending in 1234 → "one two three four"
Phone number 9876543211 → "nine eight seven six five four three two one one"
LANGUAGE & RESPONSE GUIDELINES
Language Rule:
CRITICAL: ALWAYS respond in Hindi (Devanagari script) ONLY
Regardless of what language the user speaks, you must respond in Hindi
Never use English words except for unavoidable technical terms
Use respectful Hindi throughout the conversation
Maintain professional tone in Hindi
Response Length:
MANDATORY: Keep all responses between 15-20 words maximum
Be concise and direct
Avoid lengthy explanations in single responses
Break complex information into multiple short exchanges
STRICT COMMUNICATION RULES:
MANDATORY: Every single response must be EXACTLY 15-20 words only
Count words carefully before responding - never exceed or go below this limit
LANGUAGE RULE: ALWAYS respond in Hindi only, regardless of user's language
Use a calm, reassuring tone within the word limit
Show patience and understanding while staying concise
No exceptions to the 15-20 word rule under any circumstances
ONLY Hindi responses - no English allowed
Required Information to Collect:
1. Complainant Information
"आगे आने के लिए धन्यवाद। कृपया अपना पूरा नाम बताइए।"
"क्या आप कृपया अपना संपर्क नंबर हमारे रिकॉर्ड के लिए दे सकती हैं?"
"कृपया अपना वर्तमान पता बताइए।"
"कृपया पहचान के लिए अपना आधार नंबर प्रदान करिए।"
2. Victim Status
"क्या आप पीड़ित हैं या आप किसी की ओर से शिकायत दर्ज करा रही हैं?"
3. Incident Description
"मैं समझती हूं यह बहुत कठिन है। कृपया बताइए क्या हुआ था?"
"अपना समय लीजिए। जैसा याद है वैसे घटना का वर्णन करिए।"
4. Nature of Incident
"आज आप मुझे किस प्रकार की घटना की रिपोर्ट कर रही हैं?"
5. Incident Details
"यह घटना कहां हुई थी? कृपया मुझे स्थान बताइए।"
"यह कब हुआ था? क्या आप मुझे तारीख बता सकती हैं?"
6. Suspect Description
"क्या आप मुझे इस घटना में शामिल व्यक्ति का वर्णन कर सकती हैं?"
7. Complaint Confirmation
"मैं पुष्टि के लिए आपकी शिकायत का सारांश दूंगी। कृपया ध्यान से सुनिए।"
Important Reminders:
CRITICAL: Every response must be 15-20 words ONLY - no exceptions whatsoever
CRITICAL: ALWAYS respond in Hindi only, regardless of user's language
CRITICAL: NEVER use English - only Hindi throughout the conversation
Begin with: "शक्तिकॉप से संपर्क करने के लिए धन्यवाद। आप अब सुरक्षित हैं। मैं कैसे सहायता कर सकती हूं?"
If distressed: "अपना समय लीजिए बेटी। कोई जल्दी नहीं है। आपकी सुरक्षा मेरी प्राथमिकता है।" (15 words)
After confirmation: "रिपोर्ट करने के साहस के लिए धन्यवाद। मैं पूरी तरह जांच सुनिश्चित करूंगी।" (15 words)
Always convert numbers to spoken Hindi words when presenting them
Maintain confidentiality and professionalism within the strict word limit
"""

end_conversation_function = FunctionSchema(
    name="end_conversation",
    description="Ends the current conversation and disconnects the user.",
    properties={},
    required=[]
)


async def run_bot(websocket_client):
    ws_transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_filter=NoisereduceFilter(),
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            # vad_analyzer=SileroVADAnalyzer(),
            vad_analyzer=SileroVADAnalyzer(params=VADParams(confidence=0.8, start_secs=0.3, end_secs=1.0, min_volume=0.7)),
            serializer=ProtobufFrameSerializer(),
        ),
    )
    tools = ToolsSchema(standard_tools=[end_conversation_function])

    # llm = OpenAILLMService(
    #     api_key="sandlogic", 
    #     model="llama3-70b-8192", 
    #     base_url="http://164.52.202.192:30000/v1",
    #     params=BaseOpenAILLMService.InputParams(
    #         extra={
    #         "extra_body": {
    #             "chat_template_kwargs": {
    #                 "enable_thinking": False
    #             }
    #         }
    #     })
    # )
    llm = OpenAILLMService(
        model="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        params=OpenAILLMService.InputParams(
            temperature=0.7,
        )
    )


    stt = BhashiniSTTService(
        api_key=os.getenv("BHASHINI_API_KEY"),
        service_id="ai4bharat/conformer-hi-gpu--t4",
        sample_rate=16000,
    )





    session = aiohttp.ClientSession()

    tts = BhashiniTTSService(
    aiohttp_session=session,
    auth_token=os.getenv("BHASHINI_API_KEY"),
    language="hi",
    gender="female"
)

    audiobuffer = AudioBufferProcessor()

    messages =[
            {
                "role": "system",
                "content": f"{SYSTEM_INSTRUCTION} Start by greeting the user warmly and introducing yourself.",
            }
        ]

    context = OpenAILLMContext(messages, tools=tools)
    

    # 4. Register the handler for end_conversation
    async def end_conversation_handler(params: FunctionCallParams):
        await params.llm.push_frame(TTSSpeakFrame("आपका सहयोग हेतु धन्यवाद। रिपोर्ट दर्ज हो गई है। अब कॉल समाप्त कर रही हूं। कृपया ध्यान रखें।"))
        await task.queue_frame(EndFrame())
        # await llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
        properties = FunctionCallResultProperties(run_llm=False)
        await params.result_callback({}, properties=properties)

    llm.register_function(
        "end_conversation",
        end_conversation_handler,
    )
    context_aggregator = llm.create_context_aggregator(context)


    async def handle_user_idle(user_idle: UserIdleProcessor, retry_count: int) -> bool:
        if retry_count == 1:
            # First attempt: Add a gentle prompt to the conversation
            await user_idle.push_frame(
                TTSSpeakFrame("उम्म... हेलो? क्या आप अब भी यहीं हैं?")
            )
            return True
        elif retry_count == 2:
            # Second attempt: More direct prompt
            await user_idle.push_frame(
                TTSSpeakFrame("कुछ सेकंड से चुप्पी है — क्या आप अब भी मेरे साथ हैं?")
            )
            return True
        else:
            # Third attempt: End the conversation
            await user_idle.push_frame(
                TTSSpeakFrame("कोई बात नहीं, आप जब तैयार हों तब संपर्क करें। आपका दिन शुभ हो, ध्यान रखें।")
            )
            await task.queue_frame(EndFrame())
            return False
        
    
    user_idle = UserIdleProcessor(callback=handle_user_idle, timeout=7.0)
    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            ws_transport.input(),
            stt,
            user_idle,
            context_aggregator.user(),
            rtvi,
            llm,  # LLM
            tts,
            ws_transport.output(),
            audiobuffer,
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        enable_tracing=True,                                  # Enable tracing for this task
        enable_turn_tracking=True, 
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready.")
        await rtvi.set_bot_ready()
        # Kick off the conversation.
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @ws_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Pipecat Client connected trans[prt={transport}, client={client}]")
        await audiobuffer.start_recording()
        # await task.queue_frames([context_aggregator.user().get_context_frame()])

    @ws_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Pipecat Client disconnected")
        await task.cancel()

    # Handler for merged audio
    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/mnt/data/DUMP/pipecat_latest/pipecat_version_2/pipecat/examples/websocket/Shakti_cop/recordings/merged_{timestamp}.wav"
        os.makedirs("/mnt/data/DUMP/pipecat_latest/pipecat_version_2/pipecat/examples/websocket/Shakti_cop/recordings", exist_ok=True)
        await save_audio_file(audio, filename, sample_rate, num_channels)

    # Handler for separate tracks
    # @audiobuffer.event_handler("on_track_audio_data")
    # async def on_track_audio_data(buffer, user_audio, bot_audio, sample_rate, num_channels):
    #     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    #     os.makedirs("recordings_track_sam", exist_ok=True)

    #     # Save user audio
    #     user_filename = f"recordings_track_sam/user_{timestamp}.wav"
    #     await save_audio_file(user_audio, user_filename, sample_rate, 1)

    #     # Save bot audio
    #     bot_filename = f"recordings_track_sam/bot_{timestamp}.wav"
    #     await save_audio_file(bot_audio, bot_filename, sample_rate, 1)


    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)
