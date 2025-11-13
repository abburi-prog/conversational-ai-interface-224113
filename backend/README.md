# Talk 2 AI Backend (FastAPI)

FastAPI backend providing both non-streaming and streaming chat endpoints.

- Non-streaming: POST /api/chat
- Streaming: POST /api/chat/stream (text/plain), streams tokens incrementally.

CORS is configured to allow:
- http://localhost:3000
- http://127.0.0.1:3000

Environment variables:
- OPENAI_API_KEY (required for real OpenAI calls; otherwise dev echo fallback is used)
- OPENAI_MODEL (optional, default gpt-4o-mini)

Run locally:
1) Create and fill .env from .env.example (optional if using dev fallback)
2) Install dependencies:
   pip install fastapi uvicorn pydantic "openai>=1.0.0"
3) Start the server:
   uvicorn main:app --host 0.0.0.0 --port 3001 --reload

OpenAPI docs:
- http://localhost:3001/docs
- http://localhost:3001/openapi.json

Streaming usage (curl example):
curl -N -X POST http://localhost:3001/api/chat/stream -H "Content-Type: application/json" -d '{"message":"Hello"}'
