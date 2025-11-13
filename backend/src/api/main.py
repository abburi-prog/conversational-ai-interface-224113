import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.chat import router as chat_router

openapi_tags = [
    {
        "name": "Chat",
        "description": "Endpoints for AI chat generation.",
    }
]

app = FastAPI(
    title="Talk 2 AI Backend",
    description="FastAPI backend providing chat via OpenAI.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# Configure CORS: prefer REACT_APP_FRONTEND_URL; always include localhost dev origins
frontend_origin = os.getenv("REACT_APP_FRONTEND_URL")
allowed_origins: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if frontend_origin:
    # Ensure env origin is also allowed, without duplicates
    if frontend_origin not in allowed_origins:
        allowed_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat_router)


# PUBLIC_INTERFACE
@app.get("/", tags=["Chat"], summary="Health Check")
def health_check():
    """Basic health check endpoint."""
    return {"message": "Healthy"}
