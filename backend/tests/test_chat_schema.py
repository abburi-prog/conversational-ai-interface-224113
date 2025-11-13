import pytest
from pydantic import ValidationError

from src.api.schemas.chat import ChatRequest, ChatMessage


def test_chat_request_validates_message():
    cr = ChatRequest(message="hello")
    assert cr.message == "hello"


def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


def test_chat_message_role_and_content():
    cm = ChatMessage(role="user", content="hi")
    assert cm.role == "user"
    assert cm.content == "hi"


def test_chat_message_requires_content():
    with pytest.raises(ValidationError):
        ChatMessage(role="assistant", content="   ")
