import os
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_chat_empty_message_returns_400(monkeypatch):
    # Ensure we don't require a real OpenAI key for this validation test
    if "OPENAI_API_KEY" in os.environ:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    resp = client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 400


def test_chat_too_long_message_returns_413(monkeypatch):
    if "OPENAI_API_KEY" in os.environ:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    long_message = "a" * 8001
    resp = client.post("/api/chat", json={"message": long_message})
    assert resp.status_code == 413
