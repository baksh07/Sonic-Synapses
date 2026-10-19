# 🎙️ Voice Bot Framework

A comprehensive Python framework for building real-time voice and multimodal conversational AI agents. This project provides a complete toolkit for creating intelligent voice bots that can handle phone calls, web interactions, and various AI-powered conversations.

## 🚀 What You Can Build

- **Voice Assistants** – Natural, streaming conversations with AI
- **Phone Chatbots** – Handle incoming and outgoing calls with PSTN/SIP integration
- **AI Companions** – Coaches, meeting assistants, customer service bots
- **Multimodal Interfaces** – Voice, video, images, and more
- **Interactive Storytelling** – Creative tools with generative media
- **Business Agents** – Customer intake, support bots, guided flows
- **Complex Dialog Systems** – Design logic with structured conversations

## 🧠 Key Features

- **Voice-first**: Integrates speech recognition, text-to-speech, and conversation handling
- **Pluggable**: Supports many AI services and tools
- **Composable Pipelines**: Build complex behavior from modular components
- **Real-time Communication**: WebRTC, WebSocket, and phone call support
- **Multiple AI Providers**: OpenAI, Google, Anthropic, and more
- **Production Ready**: Includes deployment examples and best practices

## 📋 Prerequisites

- Python 3.10 or higher
- API keys for your chosen services (OpenAI, Deepgram, ElevenLabs, etc.)
- For phone features: Daily.co or Twilio account

## 🛠️ Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd voice-bot-framework
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables (never commit real keys):**
```bash
cp .env.example .env
# Edit .env with your API keys. `.env` is gitignored.
```

WebSocket examples under `examples/websocket` also use this file (see `examples/websocket/env.example`). GitHub will reject pushes that contain live AWS, OpenAI, Groq, or similar secrets.

## 🎯 Quick Start

### Simple Voice Chatbot

Start with the basic voice chatbot example:

```bash
cd examples/simple-chatbot
pip install -r requirements.txt
python server.py
```

### Phone Chatbot

For phone call handling:

```bash
cd examples/phone-chatbot/daily-pstn-dial-in
pip install -r requirements.txt
python server.py
```

## 📚 Examples & Use Cases

### Core Examples

| Project | Description | Services |
|---------|-------------|----------|
| [Simple Chatbot](examples/simple-chatbot) | Basic voice-driven conversational bot | Deepgram, ElevenLabs, OpenAI, Daily |
| [Phone Chatbot](examples/phone-chatbot) | PSTN/SIP phone call handling | Deepgram, ElevenLabs, OpenAI, Daily, Twilio |
| [Patient Intake](examples/patient-intake) | Medical intake with function calling | Deepgram, ElevenLabs, OpenAI, Daily |
| [Translation Bot](examples/translation-chatbot) | Real-time speech translation | Deepgram, Azure, OpenAI, Daily |
| [Storytelling Bot](examples/storytelling-chatbot) | Collaborative story creation | Deepgram, ElevenLabs, OpenAI, Fal, Daily |

### Advanced Examples

| Project | Description | Services |
|---------|-------------|----------|
| [Moondream Chatbot](examples/moondream-chatbot) | Vision capabilities with GPT-4 | Deepgram, ElevenLabs, OpenAI, Moondream, Daily |
| [WebSocket Server](examples/websocket) | Real-time audio streaming | Cartesia, Deepgram, OpenAI, WebSockets |
| [StudyPal](examples/studypal) | Article-based conversations | Various AI services |
| [News Chatbot](examples/news-chatbot) | News discussion bot | Deepgram, ElevenLabs, OpenAI, Daily |

### Phone Call Features

- **Incoming Calls**: Handle calls with voicemail detection
- **Outgoing Calls**: Make automated calls
- **Call Transfer**: Transfer to human operators
- **Voicemail Detection**: Smart voicemail vs human detection
- **Multi-provider Support**: Daily.co and Twilio integration

## 🏗️ Architecture

The framework is built around a modular architecture:

### Core Components

- **Frames**: Discrete chunks of data (text, audio, images, control signals)
- **Frame Processors**: Operate on frames (LLM, TTS, STT, etc.)
- **Pipelines**: Chain frame processors together
- **Transports**: Handle input/output (WebRTC, WebSocket, Phone)

### Supported Services

#### Speech-to-Text
- Deepgram
- Google Cloud Speech
- Azure Speech
- AssemblyAI
- Whisper

#### Text-to-Speech
- ElevenLabs
- Cartesia
- Azure TTS
- Google Cloud TTS
- PlayHT

#### Large Language Models
- OpenAI (GPT-4, GPT-3.5)
- Google (Gemini)
- Anthropic (Claude)
- Groq
- Together AI

#### Communication
- Daily.co (WebRTC)
- Twilio (Phone/SIP)
- WebSocket
- LiveKit

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your API keys:

```env
# OpenAI
OPENAI_API_KEY=your_openai_key

# Groq
GROQ_API_KEY=your_groq_key

# Deepgram
DEEPGRAM_API_KEY=your_deepgram_key
DEEPGRAM_TTS_API_KEY=your_deepgram_tts_key

# Bhashini
BHASHINI_API_KEY=your_bhashini_key

# ElevenLabs
ELEVENLABS_API_KEY=your_elevenlabs_key

# Daily.co
DAILY_API_KEY=your_daily_key
DAILY_DOMAIN=your_daily_domain

# Twilio (for phone features)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

Copy [`.env.example`](.env.example) rather than pasting keys into Python files.

### Service-Specific Setup

Each example includes detailed setup instructions in its README file. Common setup steps include:

1. **Daily.co Setup**: Create rooms and configure webhooks
2. **Twilio Setup**: Configure phone numbers and webhooks
3. **API Keys**: Obtain and configure service API keys
4. **Webhook URLs**: Set up for phone call handling

## 🚀 Deployment

### Docker Deployment

Most examples include Dockerfiles for easy deployment:

```bash
# Build the image
docker build -t voice-bot .

# Run the container
docker run -p 7860:7860 --env-file .env voice-bot
```

### Cloud Deployment

Examples are provided for:
- **Fly.io**: Serverless deployment
- **Modal**: GPU-accelerated deployment
- **Pipecat Cloud**: Managed hosting

## 📖 Usage Examples

### Basic Voice Bot

```python
from pipecat.pipeline import Pipeline
from pipecat.transports.daily import DailyTransport
from pipecat.services.openai import OpenAILLMService
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.deepgram import DeepgramSTTService

# Create services
llm = OpenAILLMService(api_key="your_key")
tts = ElevenLabsTTSService(api_key="your_key")
stt = DeepgramSTTService(api_key="your_key")

# Create transport
transport = DailyTransport(room_url, token)

# Create pipeline
pipeline = Pipeline([
    transport.input(),
    stt,
    llm,
    tts,
    transport.output()
])

# Run the bot
await pipeline.run()
```

### Phone Bot with Function Calling

```python
async def handle_phone_call(room_url: str, token: str):
    # Define functions the bot can call
    async def schedule_appointment(params):
        # Handle appointment scheduling
        return "Appointment scheduled for tomorrow at 2 PM"
    
    # Create bot with function calling
    llm = OpenAILLMService(
        api_key="your_key",
        functions=[schedule_appointment]
    )
    
    # Set up pipeline and run
    # ... (similar to basic example)
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

For integration testing:

```bash
pytest tests/integration/
```

## 📁 Project Structure

```
voice-bot-framework/
├── src/pipecat/           # Core framework
├── examples/              # Example applications
│   ├── simple-chatbot/    # Basic voice bot
│   ├── phone-chatbot/     # Phone call handling
│   ├── patient-intake/    # Medical intake bot
│   └── ...                # More examples
├── tests/                 # Test suite
├── docs/                  # Documentation
└── requirements.txt       # Dependencies
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the BSD 2-Clause License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [docs](docs/) folder
- **Examples**: Browse the [examples](examples/) folder
- **Issues**: Open an issue on GitHub

## 🔗 Related Projects

- [Pipecat Flows](https://github.com/pipecat-ai/pipecat-flows) - For managing complex conversational states
- [Daily.co](https://daily.co) - WebRTC infrastructure
- [Deepgram](https://deepgram.com) - Speech-to-text services
- [ElevenLabs](https://elevenlabs.io) - Text-to-speech services

---

**Ready to build your voice bot?** Start with the [Simple Chatbot](examples/simple-chatbot) example and explore from there!
