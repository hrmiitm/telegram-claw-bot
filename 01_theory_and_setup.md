# Part 1 — Theory, Architecture & Setup

## 📚 What Are We Building?

A **Telegram chatbot** powered by a **LangChain Agent** that can:

- 💬 Chat with memory (remembers conversation per user)
- 📄 Read & analyze any document (direct file upload to LLM)
- 🖼️ Understand images (multimodal)
- 💾 Generate files (.md, .py, .csv, etc.) and send them back to the user
- 🕐 Tell the current date/time

---

## 🏗️ Architecture Overview

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Telegram   │  HTTP   │   bot.py     │  async  │   agent.py   │
│   User Chat  │◄──────► │  (Handlers)  │◄──────► │  (LangChain) │
└──────────────┘         └──────┬───────┘         └──────┬───────┘
                               │                         │
                          Downloads                 ┌────┴────┐
                          files to                  │ tools.py│
                          /downloads/               │ (create_│
                                                    │  file,  │
                                                    │  time)  │
                                                    └─────────┘
```

**Flow:**
1. User sends a message/file/image on Telegram
2. `bot.py` receives it via `python-telegram-bot` (polling)
3. `bot.py` calls the appropriate function in `agent.py`
4. `agent.py` constructs a multimodal `HumanMessage` to pass files directly to the LLM
5. The agent may call **tools** (e.g. `create_file` to write documents for the user)
6. Agent returns the text response and a list of generated file paths
7. `bot.py` sends the text and documents back to the user via Telegram

---

## 🧠 Key Concepts

### 1. python-telegram-bot (v22+)

The official Python wrapper for the Telegram Bot API. Since v20+, it is **fully async**.

**Core classes:**
- `ApplicationBuilder` — builds and configures the bot
- `CommandHandler` — handles `/start`, `/help`, etc.
- `MessageHandler` — handles text, photos, documents
- `filters` — filter messages by type (PHOTO, Document.ALL, TEXT)

**Pattern:**
```python
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello!")

app = ApplicationBuilder().token("YOUR_TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
```

### 2. LangChain v1 — `create_agent`

LangChain v1 introduced `create_agent` as the **standard way to build agents**, replacing the deprecated `create_react_agent` from `langgraph.prebuilt`.

```python
from langchain.agents import create_agent

agent = create_agent(
    model="openai:gpt-4o",          # provider:model format
    tools=[my_tool],                  # list of @tool functions
    system_prompt="You are helpful.", # system instructions
    checkpointer=memory,             # for chat history
)
```

**Key differences from old `create_react_agent`:**

| Feature | Old (deprecated) | New (v1) |
|---------|-----------------|----------|
| Import | `from langgraph.prebuilt import create_react_agent` | `from langchain.agents import create_agent` |
| Prompt | `prompt=` | `system_prompt=` |
| Model | ChatOpenAI object | `"provider:model"` string |
| Memory | Same checkpointer pattern | Same checkpointer pattern |

### 3. InMemorySaver (Chat History)

The checkpointer saves conversation state per `thread_id`:

```python
from langgraph.checkpoint.memory import InMemorySaver

memory = InMemorySaver()
agent = create_agent(model=..., tools=..., checkpointer=memory)

# Each user gets their own thread
config = {"configurable": {"thread_id": "user_123"}}
result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "Hi!"}]},
    config=config
)
```

> ⚠️ `InMemorySaver` is RAM-only — data is lost on restart. For production, use `PostgresSaver` or `SqliteSaver`.

### 4. Direct File Uploads & Multimodal

LangChain supports sending files directly to models (like `gpt-4o`) via `file` and `image_url` content blocks. We do not need custom Python code to extract PDF text; the LLM handles it natively!

```python
import base64

content = [
    {"type": "text", "text": "What's in this document?"},
    {
        "type": "file",
        "base64": b64_data,
        "mime_type": "application/pdf"
    }
]

result = await agent.ainvoke({"messages": [{"role": "user", "content": content}]}, config=config)
```

### 5. Tools (@tool decorator) & File Generation

Tools are Python functions the agent can call. The docstring becomes the prompt.
We use a tool to let the LLM generate files and save them to disk. `bot.py` then sends them back!

```python
from langchain.tools import tool
from langchain_core.runnables.config import RunnableConfig

@tool
def create_file(filename: str, content: str, config: RunnableConfig) -> str:
    """Create a text-based file (e.g. .md, .py, .txt, .csv) with the given content."""
    # Saves file to disk and tracks it for the current thread_id
    # ...
    return "File created successfully."
```

---

## 📦 Project Structure

```
BasicChatbot/
├── .env                # API keys & config
├── requirements.txt    # Python dependencies
├── tools.py            # Agent tools (create_file, datetime)
├── agent.py            # LangChain agent handling LLM/multimodal
├── bot.py              # Telegram bot handling messages & file sending
└── downloads/          # Auto-created for downloaded/generated files
```

Only **3 Python files** + config!

---

## 🔧 Step 1: Prerequisites

1. **Python 3.10+** installed
2. **Telegram Bot Token** — get one from [@BotFather](https://t.me/BotFather):
   - Open Telegram → search `@BotFather`
   - Send `/newbot` → follow prompts → copy the token
3. **LLM API Key** — at least one of:
   - OpenAI API key ([platform.openai.com](https://platform.openai.com))
   - Google API key ([aistudio.google.com](https://aistudio.google.com))
   - Or use Ollama locally (free, no key needed)

---

## 🔧 Step 2: Environment Setup

```bash
# Clone/navigate to the project
cd BasicChatbot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🔧 Step 3: Configure `.env`

Edit the `.env` file with your actual values:

```env
# Required
TELEGRAM_BOT_TOKEN=7123456789:AAH_your_actual_token_here

# Model (provider:model format)
MODEL_NAME=openai:gpt-4o

# API Key (set the one matching your provider)
OPENAI_API_KEY=sk-your-key-here

# Optional: custom endpoint for Ollama/LMStudio
# OPENAI_API_BASE=http://localhost:11434/v1
```

**Supported model strings:**

| Provider | MODEL_NAME example |
|----------|-------------------|
| OpenAI | `openai:gpt-4o` |
| Google | `google_genai:gemini-2.5-flash` |
| Anthropic | `anthropic:claude-sonnet-4-6` |
| Ollama | `ollama:llama3` |
| OpenRouter | `openrouter:anthropic/claude-sonnet-4-6` |

---

**Next:** [Part 2 — Code Walkthrough →](./02_code_walkthrough.md)
