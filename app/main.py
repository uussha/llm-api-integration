import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DATABASE_PATH", "./chat_history.db")
MAX_HISTORY_MESSAGES = max(2, int(os.getenv("MAX_HISTORY_MESSAGES", "20")))
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = """You are StudyBuddy, a friendly and practical learning assistant.
Your purpose is to help users understand technical topics, debug code, and learn
step by step. Use clear, simple language, give concise examples when useful,
and ask a focused follow-up question when the request is unclear. Be honest
about uncertainty. Never claim to have executed code or accessed information
that you have not actually checked."""

app = FastAPI(title="StudyBuddy Gemini Chatbot", version="1.1.0")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


@contextmanager
def db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id, id)
        """)


init_db()


class ChatRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=12000)


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    history_messages_sent: int


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured. Add GEMINI_API_KEY to your .env file and restart the server.",
        )
    return genai.Client(api_key=api_key, http_options={"timeout": int(GEMINI_TIMEOUT_SECONDS * 1000)})


def get_recent_messages(conversation_id: str):
    with db_connection() as conn:
        rows = conn.execute(
            """SELECT role, content FROM messages
               WHERE conversation_id = ?
               ORDER BY id DESC LIMIT ?""",
            (conversation_id, MAX_HISTORY_MESSAGES),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


@app.get("/")
def home():
    return FileResponse(APP_DIR / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL, "provider": "Google Gemini"}


@app.get("/api/conversations/{conversation_id}")
def conversation_history(conversation_id: str):
    with db_connection() as conn:
        rows = conn.execute(
            """SELECT role, content, created_at FROM messages
               WHERE conversation_id = ? ORDER BY id ASC""",
            (conversation_id,),
        ).fetchall()
    return {
        "conversation_id": conversation_id,
        "messages": [
            {"role": r["role"], "content": r["content"], "created_at": r["created_at"]}
            for r in rows
        ],
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    user_text = request.message.strip()
    if not user_text:
        raise HTTPException(status_code=422, detail="Please enter a message.")

    with db_connection() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)",
            (request.conversation_id, user_text),
        )

    history = get_recent_messages(request.conversation_id)

    # Gemini expects its own role names: assistant messages are "model".
    contents = [
        {"role": "user" if item["role"] == "user" else "model",
         "parts": [{"text": item["content"]}]}
        for item in history
    ]

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.7,
            },
        )
        reply = response.text
        if not reply or not reply.strip():
            raise HTTPException(status_code=502, detail="Gemini returned an empty response. Please try again.")
    except HTTPException:
        raise
    except (TimeoutError,):
        raise HTTPException(status_code=504, detail="The Gemini request timed out. Please try again.")
    except genai_errors.APIError as exc:
        status_code = getattr(exc, "code", None)
        if status_code == 429:
            raise HTTPException(status_code=429, detail="Gemini is rate-limiting requests or the free-tier quota may be exhausted. Please wait or check your Google AI Studio quota.")
        if status_code in (401, 403):
            raise HTTPException(status_code=502, detail="Gemini rejected the API key or access. Check your key and project settings.")
        if status_code == 504:
            raise HTTPException(status_code=504, detail="The Gemini request timed out. Please try again.")
        raise HTTPException(status_code=502, detail=f"Gemini returned an API error (code {status_code}). Please try again.")
    except Exception:
        raise HTTPException(status_code=503, detail="Could not reach Gemini. Check your internet connection and try again.")

    with db_connection() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'assistant', ?)",
            (request.conversation_id, reply.strip()),
        )

    return ChatResponse(
        conversation_id=request.conversation_id,
        reply=reply.strip(),
        history_messages_sent=len(history),
    )


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    with db_connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    return {"deleted": True, "conversation_id": conversation_id}
