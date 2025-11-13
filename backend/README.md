# Talk 2 AI Backend (FastAPI)

FastAPI backend providing both non-streaming and streaming chat endpoints with structured logging.

- Non-streaming: POST /api/chat
- Streaming: POST /api/chat/stream (text/plain), streams tokens incrementally.
- Health: GET /api/health (minimal)

CORS is configured to allow:
- http://localhost:3000
- http://127.0.0.1:3000
- Plus REACT_APP_FRONTEND_URL if set

Environment variables:
- OPENAI_API_KEY (required for real OpenAI calls; otherwise dev echo fallback is used)
- OPENAI_MODEL (optional, default gpt-4o-mini)
- LOG_LEVEL or REACT_APP_LOG_LEVEL (optional, default INFO) e.g., DEBUG|INFO|WARNING|ERROR|CRITICAL

Diagnostics and Logging:
- Structured JSON-like logs integrated with uvicorn (stdout)
- Request/response logging middleware records method, path, origin, status, duration_ms
- Centralized exception handler logs stack traces without exposing secrets
- Headers are sanitized (Authorization, API keys masked)
- CORS configuration and log level emitted at startup

Run locally:
1) Create and fill .env (optional if using dev fallback)
2) Install dependencies:
   pip install -r requirements.txt
3) Start the server:
   uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload

OpenAPI docs:
- http://localhost:3001/docs
- http://localhost:3001/openapi.json

Streaming usage (curl example):
curl -N -X POST http://localhost:3001/api/chat/stream -H "Content-Type: application/json" -d '{"message":"Hello"}'
