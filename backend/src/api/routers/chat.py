from typing import List

from fastapi import APIRouter, HTTPException, status, Body
from pydantic import ValidationError

from src.api.schemas.chat import ChatRequest, ChatResponse
from src.api.services.openai_client import openai_client

router = APIRouter(tags=["Chat"], prefix="")

MAX_MESSAGE_LEN = 8000


# PUBLIC_INTERFACE
@router.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Generate chat reply",
    description="Accepts user message and optional context messages; returns assistant reply generated via OpenAI.",
    responses={
        200: {"description": "Chat reply generated"},
        400: {"description": "Invalid input"},
        413: {"description": "Payload too large - message exceeds limit"},
        500: {"description": "Server error"},
        502: {"description": "Upstream LLM error"},
    },
)
def create_chat(payload: ChatRequest = Body(..., description="Chat request payload")) -> ChatResponse:
    """
    POST /api/chat

    Generates a reply using OpenAI Chat Completions.

    Parameters:
    - payload: ChatRequest { message: string, context?: ChatMessage[] }

    Returns:
    - ChatResponse { reply: string }

    Notes:
    - Uses environment variables OPENAI_API_KEY and OPENAI_MODEL for configuration.
    - Basic input size limit enforced to prevent abuse (8k chars).
    - Consider adding authentication and rate limiting in front of this endpoint in production.
    """
    # Additional validation and size guard
    msg = payload.message or ""
    if len(msg) > MAX_MESSAGE_LEN:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="message exceeds maximum length (8k chars)",
        )

    if not msg.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")

    # Build messages array with system prompt and optional context
    messages: List[dict] = [
        {"role": "system", "content": "You are Kavia, a helpful, concise AI assistant."}
    ]
    if payload.context:
        for m in payload.context:
            # Only accept valid roles and content
            messages.append({"role": m.role, "content": m.content})

    messages.append({"role": "user", "content": msg})

    # Call OpenAI
    try:
        reply = openai_client.create_chat_completion(messages)
        return ChatResponse(reply=reply)
    except HTTPException as he:
        # pass-through handled exceptions
        raise he
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from ve
    except Exception as e:
        # Generic safety net
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected server error") from e
