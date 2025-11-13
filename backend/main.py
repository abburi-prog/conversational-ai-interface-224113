from typing import AsyncGenerator, List, Optional

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator

# PUBLIC_INTERFACE
class ChatMessage(BaseModel):
    """Represents a single chat message with a role and content."""
    role: str = Field(..., description="Role of the message author", examples=["system", "user", "assistant"])
    content: str = Field(..., description="Message content")

    @validator("role")
    def validate_role(cls, v: str) -> str:
        allowed = {"system", "user", "assistant"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


# PUBLIC_INTERFACE
class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    message: str = Field(..., description="User message to the assistant")
    context: Optional[List[ChatMessage]] = Field(None, description="Optional prior messages context")


# PUBLIC_INTERFACE
class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    reply: str = Field(..., description="Assistant reply text")


app = FastAPI(
    title="Talk 2 AI Backend",
    description="FastAPI backend providing chat via OpenAI.",
    version="0.2.0",
    openapi_tags=[
        {"name": "Chat", "description": "Endpoints for AI chat generation."}
    ],
)

# CORS: allow frontend dev origins explicitly for React dev server
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_openai_client():
    """
    Internal helper to lazily import and create an OpenAI client without hardcoding secrets.
    Requires environment variable OPENAI_API_KEY to be set by runtime.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    try:
        # Prefer the official OpenAI SDK v1.x client if available.
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        # Fallback using legacy openai package if present
        try:
            import openai  # type: ignore
            openai.api_key = api_key
            return openai
        except Exception:
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}") from e


@app.get("/", tags=["Chat"], summary="Health Check", description="Basic health check endpoint.")
# PUBLIC_INTERFACE
def health():
    """Health check endpoint returning service info."""
    return {"status": "ok", "service": "talk-2-ai-backend", "version": "0.2.0"}


@app.post(
    "/api/chat",
    tags=["Chat"],
    summary="Generate chat reply (non-streaming)",
    description="Accepts user message and optional context messages; returns assistant reply generated via OpenAI.",
    response_model=ChatResponse,
)
# PUBLIC_INTERFACE
def chat(request: ChatRequest) -> ChatResponse:
    """
    Non-streaming chat endpoint.
    Parameters:
    - request: ChatRequest containing message and optional context
    Returns:
    - ChatResponse: reply text
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Try to use OpenAI completion; fallback to echo if not configured
    try:
        client = _get_openai_client()
        # Support both v1 client and legacy
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        if request.context:
            for m in request.context:
                messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": request.message})

        reply_text = ""
        try:
            # New SDK
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,  # type: ignore[arg-type]
                temperature=0.6,
            )
            reply_text = resp.choices[0].message.content or ""
        except AttributeError:
            # Legacy SDK interface
            resp = client.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=messages,  # type: ignore[arg-type]
                temperature=0.6,
            )
            reply_text = resp["choices"][0]["message"]["content"] or ""

        return ChatResponse(reply=reply_text.strip())
    except RuntimeError:
        # If OPENAI_API_KEY or client missing, provide a safe fallback
        return ChatResponse(reply=f"(dev) You said: {request.message}")


@app.post(
    "/api/chat/stream",
    tags=["Chat"],
    summary="Generate chat reply (streaming)",
    description=(
        "Streams generated assistant tokens as a UTF-8 text stream. "
        "Each chunk is a plain text token without separators. "
        "Use fetch with ReadableStream to incrementally render in clients."
    ),
    responses={
        200: {"description": "Stream of tokens", "content": {"text/plain": {}}},
        400: {"description": "Invalid input"},
        500: {"description": "Server error"},
    },
)
# PUBLIC_INTERFACE
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using OpenAI's streaming APIs when available.
    Returns a text/plain StreamingResponse with the assistant reply tokens.
    If OpenAI is not configured, streams a simple simulated typing response.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def stream_generator() -> AsyncGenerator[bytes, None]:
        # Try OpenAI streaming; if unavailable, simulate streaming
        try:
            client = _get_openai_client()
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            if request.context:
                for m in request.context:
                    messages.append({"role": m.role, "content": m.content})
            messages.append({"role": "user", "content": request.message})

            # Attempt new SDK streaming
            try:
                stream = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=messages,  # type: ignore[arg-type]
                    temperature=0.6,
                    stream=True,
                )
                for event in stream:
                    # New SDK event chunk
                    try:
                        delta = event.choices[0].delta.content or ""
                    except Exception:
                        # Some models return message.content in chunks
                        delta = getattr(event.choices[0].message, "content", "") or ""
                    if delta:
                        yield delta.encode("utf-8")
                return
            except AttributeError:
                # Legacy SDK streaming
                stream = client.ChatCompletion.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                    messages=messages,  # type: ignore[arg-type]
                    temperature=0.6,
                    stream=True,
                )
                for chunk in stream:
                    if "choices" in chunk and chunk["choices"]:
                        delta = chunk["choices"][0].get("delta", {}).get("content")
                        if delta:
                            yield delta.encode("utf-8")
                return
        except Exception:
            # Fallback simulated streaming output for development
            sim = f"(dev) You said: {request.message}"
            for ch in sim:
                yield ch.encode("utf-8")

    return StreamingResponse(stream_generator(), media_type="text/plain")
