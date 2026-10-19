# WebSocket voice examples

Real-time audio streaming examples using FastAPI WebSockets.

## Security

API keys are **not** stored in source. Load them from a local `.env` file.

1. Copy [`env.example`](env.example) to `.env` (repo root or this folder).
2. Fill in the keys for the services you use.
3. Run the bot from a directory where `python-dotenv` can find `.env`.

Required variables for the remaining Shakti Cop example:

| Variable | Used for |
|----------|----------|
| `OPENAI_API_KEY` | GPT models in `Shakti_cop` |
| `GROQ_API_KEY` | Groq LLM in `bot_fast_api.py` / `sam_endcall.py` |
| `DEEPGRAM_API_KEY` | Speech-to-text |
| `DEEPGRAM_TTS_API_KEY` | Deepgram TTS |
| `BHASHINI_API_KEY` | Bhashini STT/TTS |

`.env` is gitignored. If a key was ever committed, rotate it in the provider dashboard.

## Run Shakti Cop

```bash
cd examples/websocket/Shakti_cop
python server.py
```
