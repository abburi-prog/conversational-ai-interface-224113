from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


# PUBLIC_INTERFACE
class ChatMessage(BaseModel):
    """Represents a single chat message with a role and content."""
    role: Literal["system", "user", "assistant"] = Field(..., description="Role of the message author")
    content: str = Field(..., description="Message content")

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must not be empty")
        return v


# PUBLIC_INTERFACE
class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    message: str = Field(..., description="User message to the assistant")
    context: Optional[List[ChatMessage]] = Field(default=None, description="Optional prior messages context")

    @field_validator("message")
    @classmethod
    def message_not_empty_and_limit(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("message must not be empty")
        if len(v) > 8000:
            # Route will handle 413, but prevent excessive payload here too
            raise ValueError("message too long")
        return v


# PUBLIC_INTERFACE
class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    reply: str = Field(..., description="Assistant reply text")
