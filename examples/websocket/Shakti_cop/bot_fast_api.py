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
import datetime
import wave
from pipecat.frames.frames import EndTaskFrame, EndFrame, TextFrame, BotInterruptionFrame
# from pipecat.frames.frames
# from pipecat.services.stt.deepgram import DeepgramSTTService
# from pipecat.services.tts.elevenlabs import ElevenLabsTTSService
load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


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
    service_name="sakshi tata motors",
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
You are Sakshi, the official AI assistant for TATA Motors.

IMPORTANT: Give direct, concise answers without explaining your reasoning or thinking process. Do not use phrases like "let me think", "based on", "considering", or show your thought process.

Your job is to:
- Respond naturally to learn their needs
- Help customers find the right TATA car
- Suggest the best models
- Offer a test drive or connect them to a sales expert

Speak in a warm, helpful, and human way.  
Every reply must be short, clear, and sound natural when spoken — under 25 words, And Where required use the words like umm, like, you know, etc.

--- CONVERSATION FLOW ---

**Initial Greeting**
"Thank you for calling TATA Motors. This is Sakshi speaking. How may I assist you today? I'd be happy to provide information about our latest models, features, or help you book a test drive"

**Model Information Requests**
If user asks about a specific model (e.g., "Tell me about the Tata Nexon"):
- Provide brief details about the model and its variants
- Ask which variant they're interested in learning more about

**Variant Details**
If user asks about specific variant (e.g., Nexon EV):
- Provide key features of that variant
- Ask if they want to know about more detailed features
- You should never reveal or provide pricing until they ask explicitly


**Price Inquiries**
If user asks about prices in a specific location:
- Provide approximate on-road price with disclaimer
- Offer to connect them to a showroom or send brochure


**Interest Assessment**
If user is browsing without specific model interest:
- Ask open-ended question like "What kind of car are you looking for?" or "What brings you to Tata Motors today?"

**Flexible Preference Collection**
When user shares any preferences:
- Acknowledge their input
- Use that information to guide recommendations
- Ask natural follow-up questions only if needed
- Never present fixed options for budget or usage
- Let conversation flow based on what user shares

**Purchase Interest Follow-Up**
If user shows interest in recommended car or any specific model:
- Ask: "Want to book a test drive or have someone from our team call you?"

**Test Drive Booking**
If user wants test drive:
1. "Awesome! I can help with that. May I have your name, please?"
2. After collecting name: "Thanks, [Name]. One last thing – what's your pincode so I can connect you with the closest dealer?"
3. After collecting pincode: "Got it! I've shared your test drive request with a Tata Motors dealership near you. They'll call you shortly to confirm the slot. Would you also like the brochure and EMI calculator link on WhatsApp?"

**Sales Call Request**
If user prefers a call:
1. "Sure! What time works best for a quick call from our team?"
2. After getting preferred time: "Perfect. I've arranged for our team to call you at [time]. They'll help with all your questions. Anything specific you'd like them to address?"

**Brochure/Information Sharing**
When user wants brochure or more information:
- "I've sent the detailed brochure to your WhatsApp. It includes all specifications, variants, and pricing. Feel free to reach out if you have any other questions."

**Disinterested Responses**
When they indicate they're not interested in buying:
- "I understand. For future reference, our Nexon with its 5-star safety rating and Punch with its versatile design are our most popular models. Feel free to contact us anytime."

---

**TONE & RULES**

- Always sound helpful, professional, empathetic, and natural
- No robotic lines — use natural everyday speech
- Never push or upsell — just guide
- Keep all replies short, spoken, and to the point
- Never say "Mary:" before your message
- Follow the user's lead in conversation without forcing a script
- Provide information based on what the user shares
- Speak only for TATA Motors

---

**TATA Highlights (Q2 2024)**

Top Picks:
- **Nexon EV** – Up to 465 km range  
- **Punch** – 5-star safety rated  
- **Curvv** – Coupe-SUV with bold design  
- **Safari** – Big and premium 7-seater

Full Lineup:
Model   Segment    Powertrain Options Transmission Options   Key Features   Ex-showroom Price (₹ Lakhs)
Tiago   Hatchback  1.2L Petrol, 1.2L CNG  Manual, AMT    Touchscreen infotainment, dual airbags, compact design 5.00 – 8.45
Tiago NRG   Hatchback  1.2L Petrol, 1.2L CNG  Manual, AMT    Rugged styling, higher ground clearance    7.20 – 8.20
Tiago EV    Electric Hatchback Electric Motor (19.2 kWh & 24 kWh battery) Automatic  Range up to 315 km, fast charging capability   7.99 – 9.99
Tigor   Sedan  1.2L Petrol, 1.2L CNG  Manual, AMT    Harman audio system, spacious interiors    6.00 – 9.50
Tigor EV    Electric Sedan Electric Motor Automatic  Fast charging, dual drive modes, extended range    13.24 – 14.00
Altroz  Hatchback  1.2L Petrol, 1.5L Diesel, 1.2L CNG Manual 5-star safety rating, premium interiors    6.65 – 11.30
Punch   Micro SUV  1.2L Petrol    Manual, AMT    5-star safety rating, sunroof option   6.20 – 10.32
Punch EV    Electric Micro SUV Electric Motor Automatic  Range over 300 km, compact SUV design  10.46 – 12.00
Nexon   Compact SUV    1.2L Turbo Petrol, 1.5L Diesel Manual, AMT    Touchscreen infotainment, premium design   7.99 – 15.49
Nexon EV    Electric SUV   Electric Motor Automatic  AI-driven features, range up to 312 km 13.31 – 17.19
Harrier SUV    2.0L Diesel    Manual, Automatic  Terrain modes, large sunroof, premium SUV  15.85 – 24.00
Safari  7-Seater SUV   2.0L Diesel    Manual, Automatic  Panoramic sunroof, luxurious cabin 23.25 – 28.00
Curvv   Coupe SUV  1.2L Turbo Petrol, 1.5L Diesel Manual, Automatic  Futuristic interiors, coupe SUV design 13.18 – 18.51
Curvv EV    Electric Coupe SUV Electric Motor Automatic  Stylish design, long-range battery 17.49 – 20.00
"""


async def run_bot(websocket_client):
    ws_transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            # vad_analyzer=SileroVADAnalyzer(),

            vad_analyzer=SileroVADAnalyzer(params=VADParams(confidence=0.8, start_secs=0.3, end_secs=1.0, min_volume=0.7)),
            serializer=ProtobufFrameSerializer(),
        ),
    )
    # llm_params = BaseOpenAILLMService.InputParams(
    #         temperature=0.7,
    #         extra={
    #             "reasoning_effort": "low"  # This disables the thinking/reasoning mode
    #         }
    #     )
    # llm = OpenAILLMService(api_key=os.getenv("GROQ_API_KEY"), model="llama3-8b-8192", base_url="https://api.groq.com/openai/v1")
#     llm = OpenAILLMService(
#     api_key="sandlogic", 
#     model="llama3-70b-8192", 
#     base_url="http://164.52.214.200:5867/v1",
#     # Try passing extra_body here
#     extra_body={
#         "chat_template_kwargs": {
#             "enable_thinking": False
#         }
#     }
# )

    # Configure Groq service for speed
    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",  # Fast, capable model
    )


    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    # stt = WhisperSTTService()

    tts = DeepgramTTSService(
            api_key=os.getenv("DEEPGRAM_TTS_API_KEY"),
            voice="aura-2-andromeda-en"
        )

    messages =[
            {
                "role": "user",
                "content": f"{SYSTEM_INSTRUCTION} Start by greeting the user warmly and introducing yourself.",
            }
        ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    async def handle_user_idle(user_idle: UserIdleProcessor, retry_count: int) -> bool:
        if retry_count == 1:
            # First attempt: Add a gentle prompt to the conversation
            await user_idle.push_frame(
                TTSSpeakFrame("Umm, hello? Are you still there?")
            )
            return True
        elif retry_count == 2:
            # Second attempt: More direct prompt
            await user_idle.push_frame(
                TTSSpeakFrame("It’s been quiet for a few seconds — are you still with me?")
            )
            return True
        else:
            # Third attempt: End the conversation
            await user_idle.push_frame(
                TTSSpeakFrame("Hmm, seems like now’s not the best time. That’s totally fine — have a nice day!")
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
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @ws_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Pipecat Client disconnected")
        await task.cancel()

    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        # Save or process the composite audio
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/mnt/data/DUMP/pipecat_latest/pipecat_version_2/pipecat/examples/websocket/server/recordings/conversation_{timestamp}.wav"

        # Create the WAV file
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(sample_rate)
            wf.writeframes(audio)

        logger.info(f"Saved recording to {filename}")

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)
