import os
import tempfile
import uuid
from unittest.mock import MagicMock

_TEST_DB = tempfile.NamedTemporaryFile(prefix="studybuddy_gemini_test_", suffix=".sqlite3", delete=False)
os.environ["DATABASE_PATH"] = _TEST_DB.name
os.environ["GEMINI_API_KEY"] = "test-key"

from fastapi.testclient import TestClient
import app.main as main


class FakeModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        response = MagicMock()
        response.text = f"mock Gemini reply {len(self.calls)}"
        return response


def test_health():
    client = TestClient(main.app)
    result = client.get("/api/health").json()
    assert result["status"] == "ok"
    assert result["provider"] == "Google Gemini"


def test_chat_keeps_multi_turn_context(monkeypatch):
    fake_models = FakeModels()
    fake_client = MagicMock()
    fake_client.models = fake_models
    monkeypatch.setattr(main, "get_gemini_client", lambda: fake_client)
    client = TestClient(main.app)
    conversation_id = str(uuid.uuid4())

    first = client.post("/api/chat", json={"conversation_id": conversation_id, "message": "My favourite colour is blue."})
    second = client.post("/api/chat", json={"conversation_id": conversation_id, "message": "What is my favourite colour?"})

    assert first.status_code == 200
    assert second.status_code == 200
    sent = fake_models.calls[1]["contents"]
    assert any(part["text"] == "My favourite colour is blue." for item in sent for part in item["parts"])
    assert sent[0]["role"] == "user"
    assert second.json()["reply"] == "mock Gemini reply 2"


def test_context_is_bounded(monkeypatch):
    fake_models = FakeModels()
    fake_client = MagicMock()
    fake_client.models = fake_models
    monkeypatch.setattr(main, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(main, "MAX_HISTORY_MESSAGES", 4)
    client = TestClient(main.app)
    conversation_id = str(uuid.uuid4())

    for i in range(5):
        response = client.post("/api/chat", json={"conversation_id": conversation_id, "message": f"message {i}"})
        assert response.status_code == 200

    sent = fake_models.calls[-1]["contents"]
    assert len(sent) == 4
    assert not any(part["text"] == "message 0" for item in sent for part in item["parts"])


def test_api_key_missing_returns_clear_error(monkeypatch):
    def missing_key():
        raise main.HTTPException(status_code=503, detail="Gemini API key missing")

    monkeypatch.setattr(main, "get_gemini_client", missing_key)
    client = TestClient(main.app)
    response = client.post("/api/chat", json={"conversation_id": "test-missing-key", "message": "Hello"})
    assert response.status_code == 503
    assert "Gemini API key missing" in response.json()["detail"]
