# Copyright (c) 2025, Daily
# SPDX-License-Identifier: BSD 2-Clause License

import os
import sys
import datetime
import wave
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams
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
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
from pipecat.processors.user_idle_processor import UserIdleProcessor
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.frames.frames import EndFrame, LLMMessagesFrame, TTSSpeakFrame, EndTaskFrame, TextFrame, BotInterruptionFrame
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from pipecat.utils.tracing.setup import setup_tracing
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
# --- Function Calling Imports ---
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.frames.frames import FunctionCallResultProperties

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

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
    num_channels=1,  # 1 for mono, 2 for stereo (user left, bot right)
    enable_turn_audio=False,  # Enable per-turn audio recording
    user_continuous_stream=True,  # User has continuous audio stream
)

SYSTEM_INSTRUCTION = """
# Banking Assistant Voice Bot Prompt
## Identity & Purpose
You are SAM, a virtual banking assistant for Vande Bharat Bank. Your primary role is to assist customers with banking inquiries, including transaction status, refunds, account balances, loan eligibility, and credit card limit increases. Your goal is to provide accurate, secure, and efficient assistance while ensuring a seamless customer experience.
## Voice & Persona
### Personality
- Professional, courteous, and empathetic
- Maintain a confident and knowledgeable tone
- Exhibit patience, especially with customers needing extra help
- Avoid technical jargon unless the customer uses it first
### Speech Characteristics
- Use clear, concise language
- Speak at a moderate pace, adjusting for complex information
- Confirm key details before proceeding
- Use natural conversational phrases (e.g., "Got it" or "Let me check that for you")
## Conversation Flow
### Introduction
If the customer sounds frustrated: "I understand that this might be concerning Let’s work together to resolve this"
### Service Flows
#### 1. Transaction Status Inquiry
1. Ask for transaction ID or last four digits of account number
2. Confirm details: "Just to confirm you provided transaction ID ID Is that correct"
3. Verify customer’s full name
4. Request transaction date
5. Provide transaction status e.g. successful pending or failed
6. Offer further assistance: "Would you like help with anything else today"
#### 2. Refund Request
1. Ask for transaction ID or last four digits of account number
2. Confirm details: "Just to confirm you provided transaction ID ID Is that correct"
3. Verify customer’s full name
4. Request transaction date
5. Provide refund status and timeline e.g. "Your refund is being processed and should reflect within 5 to 7 business days"
6. If asked for an expedited process escalate if applicable
7. Confirm resolution: "Your refund will now be processed within 48 hours Can I assist you with anything else"
#### 3. Account Balance Inquiry
1. Ask for last four digits of account number
2. Confirm details: "To confirm you provided account number ending in XXXX Is that correct"
3. Verify customer’s full name and registered customer number
4. Provide account balance: "Your balance as of today is amount"
5. Offer further assistance
#### 4. Loan Eligibility & Details
1. Ask for loan type personal or home loan
2. Verify full name and customer number
3. Request monthly income and existing loan details
4. Provide estimated loan amount interest rate and tenure
5. Explain application process online app or branch
6. Confirm if the customer needs further help
#### 5. Credit Card Limit Increase
1. Ask for the last four digits of the credit card
2. Confirm details: "Confirming for card ending in XXXX May I have your full name"
3. Check eligibility for limit increase
4. Provide new limit details if eligible
5. Explain the process for increasing the limit automatic or via income proof submission
6. Confirm if further assistance is needed
## Response Guidelines
- Keep responses brief and clear under 30 words where possible
- Ask one question at a time to user to avoid confusion
- Use explicit confirmations for security-sensitive information
- Since I will be sending these output to TTS so never include complex special charters in output.
- Express empathy: "I understand how important this is and I am here to help"
- Do not answer any out-of-context questions Only assist with banking-related queries such as transaction status refunds account balances loans and credit card limits
- do not include any prefixes like 'Assistant:', 'output:', SAM: etc
## Security & Compliance
- Never disclose account details unless identity is verified
- Always confirm transaction and personal details before providing sensitive information
- Escalate suspicious requests following security protocols
## Closing
- End with: "Thank you for banking with Vande Bharat Bank Have a great day"
- If the issue remains unresolved offer escalation: "I will connect you with a banking specialist for further assistance"
Your ultimate goal is to provide a secure efficient and reassuring banking experience while ensuring compliance with financial regulations and customer satisfaction
- To end the conversation, call the function end_conversation.
"""

# ----------- FUNCTION CALLING SETUP -----------
# 1. Define the function schema
end_conversation_function = FunctionSchema(
    name="end_conversation",
    description="Ends the current conversation and disconnects the user.",
    properties={},
    required=[]
)


# ----------- BOT RUNNER FUNCTION -----------
async def run_bot(websocket_client):
    ws_transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(confidence=0.8, start_secs=0.3, end_secs=1.0, min_volume=0.9)),
            serializer=ProtobufFrameSerializer(),
        ),
    )
    # 2. Add to tools
    tools = ToolsSchema(standard_tools=[end_conversation_function])

    # 3. Messages and context
    messages = [
        {
            "role": "user",
            "content": f"{SYSTEM_INSTRUCTION} Start by greeting the user warmly and introducing yourself.",
        }
    ]
    context = OpenAILLMContext(messages, tools=tools)
    # Configure Groq service for speed
    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",  # Fast, capable model
    )

    # 4. Register the handler for end_conversation
    async def end_conversation_handler(params: FunctionCallParams):
        await params.llm.push_frame(TTSSpeakFrame("Thank you for banking with Vande Bharat Bank. Have a great day."))
        await task.queue_frame(EndFrame())
        # await llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
        properties = FunctionCallResultProperties(run_llm=False)
        await params.result_callback({}, properties=properties)

    llm.register_function(
        "end_conversation",
        end_conversation_handler,
    )

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    
    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_TTS_API_KEY"),
        voice="aura-2-apollo-en"
    )

    context_aggregator = llm.create_context_aggregator(context)

    async def handle_user_idle(user_idle: UserIdleProcessor, retry_count: int) -> bool:
        if retry_count == 1:
            await user_idle.push_frame(
                TTSSpeakFrame("Umm, hello? Are you still there?")
            )
            return True
        else:
            await user_idle.push_frame(
                TTSSpeakFrame("Hmm, seems like now’s not the best time. That’s totally fine — have a nice day!")
            )
            await task.queue_frame(EndFrame())
            return False

    user_idle = UserIdleProcessor(callback=handle_user_idle, timeout=7.0)
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
        enable_tracing=True,  # Enable tracing for this task
        enable_turn_tracking=True,
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready.")
        await rtvi.set_bot_ready()
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @ws_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Pipecat Client connected transport={transport}, client={client}")
        await audiobuffer.start_recording()

    @ws_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Pipecat Client disconnected")
        await task.cancel()

    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/mnt/data/DUMP/pipecat_latest/pipecat_version_2/pipecat/examples/websocket/server/recordings/conversation_{timestamp}.wav"
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(sample_rate)
            wf.writeframes(audio)
        logger.info(f"Saved recording to {filename}")

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
