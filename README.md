# StudyBuddy — Gemini LLM API Integration

A full-stack AI chatbot built using Python, FastAPI, Google's Gemini API, and SQLite. StudyBuddy maintains multi-turn conversation history, manages context windows, and provides a simple web-based chat interface.

## Features

- **Gemini API Integration:** Uses Google's official `google-genai` Python SDK.
- **Multi-turn Conversations:** Maintains separate conversation histories using unique conversation IDs.
- **Context Window Management:** Sends only the latest 20 messages to Gemini.
- **SQLite Persistence:** Stores conversation history across server restarts.
- **Custom System Prompt:** Configures StudyBuddy as a friendly technical learning assistant.
- **Error Handling:** Handles API errors, timeouts, rate limits, missing API keys, and connection failures.
- **Web Interface:** Responsive chat interface with new conversation functionality.
- **API Key Security:** Stores API credentials in environment variables.

## Tech Stack

- Python
- FastAPI
- Google Gemini API
- Google GenAI SDK
- SQLite
- HTML, CSS, JavaScript
- Pytest

## Project Structure

```text
llm_api_chatbot/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── tests/
│   └── test_app.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/uussha/llm-api-integration.git
cd llm-api-integration
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Gemini API key

Copy `.env.example` to `.env` and add your Gemini API key.

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_configured_gemini_model
DATABASE_PATH=./chat_history.db
MAX_HISTORY_MESSAGES=20
GEMINI_TIMEOUT_SECONDS=30
```

Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

Never commit your `.env` file or expose your API key.

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

Open:

http://127.0.0.1:8000

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Check API health |
| POST | `/api/chat` | Send a message and receive an AI response |
| GET | `/api/conversations/{conversation_id}` | Retrieve conversation history |
| DELETE | `/api/conversations/{conversation_id}` | Delete a conversation |

## Context Window Management

All conversation messages are stored in SQLite. However, only the latest 20 messages are retrieved and sent to Gemini for each request.

This prevents unlimited conversation history from being sent to the model.

The limit can be configured using `MAX_HISTORY_MESSAGES` in `.env`.

## Testing

Run the automated tests:

```bash
pytest -v
```

The test suite checks:

- Health endpoint functionality
- Multi-turn conversation history
- Context window truncation
- Missing API key error handling

The tests use mocked Gemini responses and do not require API credits.

## Manual Testing

Test multi-turn memory by sending these messages in one conversation:

1. My name is Usha.
2. I am learning Python.
3. I prefer simple explanations.
4. What is a Python variable?
5. What is my name, what am I learning, and how do I prefer explanations?

The chatbot should recall the details shared earlier.

## Security

- API keys are stored in `.env`.
- `.env` is excluded using `.gitignore`.
- Never upload API credentials to GitHub.

## Author

Usha Sree Bevara

GitHub: https://github.com/uussha