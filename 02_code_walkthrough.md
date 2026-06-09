# Part 2 — Code Walkthrough

Complete line-by-line explanation of every file in the project.

---

## 📄 File 1: `requirements.txt`

```txt
langchain>=1.0.0            # Core framework (create_agent, tools, messages)
langgraph>=0.4.0            # Required by create_agent internally
langchain-openai>=1.0.0     # OpenAI LLM provider
python-telegram-bot>=22.0   # Telegram Bot API wrapper (async)
python-dotenv>=1.0.0        # Load .env files
```

**Why these versions?**
- `langchain>=1.0.0` — LangChain v1 introduced `create_agent`
- `langgraph>=0.4.0` — provides `InMemorySaver` checkpointer used for chat memory
- `python-telegram-bot>=22.0` — v22 uses async `Application` class

---

## 📄 File 2: `tools.py` — Agent Tools

This file defines the **tools** (functions) the agent can call during reasoning.

```python
"""
tools.py — Agent Tools for the Telegram Chatbot
"""
import os
from datetime import datetime
from langchain.tools import tool
from pypdf import PdfReader
```

### Tool 1: `read_pdf`

```python
@tool
def read_pdf(file_path: str) -> str:
    """Read and extract all text from a PDF file.
    Use this tool when you need to read, summarise, or answer
    questions about a PDF document.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at '{file_path}'"

    reader = PdfReader(file_path)
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages_text.append(f"--- Page {i + 1} ---\n{text}")
    full_text = "\n\n".join(pages_text)

    # Truncate to avoid token overflow
    if len(full_text) > 15_000:
        full_text = full_text[:15_000] + "\n\n... [truncated]"
    return full_text
```

**How it works:**
1. `PdfReader` opens the PDF and exposes `.pages`
2. Each page's `.extract_text()` returns plain text
3. We add page markers (`--- Page 1 ---`) for context
4. **Truncation at 15k chars** prevents token limit errors
5. The `@tool` decorator registers it with LangChain — the **docstring becomes the tool description** the LLM sees

### Tool 2: `read_file`

```python
@tool
def read_file(file_path: str) -> str:
    """Read the contents of a text-based file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if len(content) > 15_000:
        content = content[:15_000] + "\n\n... [truncated]"
    return content
```

**Key detail:** `errors="replace"` ensures binary files don't crash the reader — garbled chars are replaced with `�`.

### Tool 3: `get_datetime`

```python
@tool
def get_datetime() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")
```

### Tool Registry

```python
ALL_TOOLS = [read_pdf, read_file, get_datetime]
```

This list is imported by `agent.py` and passed to `create_agent`.

---

## 📄 File 3: `agent.py` — LangChain Agent

The brain of the application. Creates the agent and exposes async functions for the bot.

### Imports & Config

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import ALL_TOOLS

MODEL_NAME = os.getenv("MODEL_NAME", "openai:gpt-4o")
```

- `create_agent` — LangChain v1's standard agent builder
- `InMemorySaver` — stores chat history in RAM per thread
- `MODEL_NAME` uses the `"provider:model"` format that `create_agent` understands natively

### System Prompt

```python
SYSTEM_PROMPT = """You are a helpful, friendly AI assistant inside a Telegram bot.

Your capabilities:
- Answer questions on any topic
- Read and summarise PDF documents (use the read_pdf tool)
- Read text files (use the read_file tool)
- Tell the current date/time (use the get_datetime tool)

Guidelines:
- Keep responses concise and well-formatted for Telegram (use Markdown).
- When summarising a document, provide key points as bullet points.
- If the user sends an image, describe or analyse it.
"""
```

> The system prompt is crucial — it tells the agent what tools are available and how to format output for Telegram.

### Agent Creation

```python
checkpointer = InMemorySaver()

agent = create_agent(
    model=MODEL_NAME,           # "openai:gpt-4o"
    tools=ALL_TOOLS,            # [read_pdf, read_file, get_datetime]
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,  # enables chat memory
)
```

This is a **singleton** — created once when the module loads, shared across all requests.

### `chat()` — Text Messages

```python
async def chat(chat_id: int, user_message: str) -> tuple[str, list[str]]:
    thread_id = str(chat_id)
    generated_files_per_thread[thread_id] = []
    
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
    )
    
    files = generated_files_per_thread.get(thread_id, [])
    return result["messages"][-1].content, files
```

**Key points:**
- `thread_id = str(chat_id)` — each Telegram user gets isolated memory
- We reset the generated files list at the start of each chat
- Returns a tuple: the LLM's text response, and any files generated by tools.

### `chat_with_image()` & `chat_with_file()` — Direct File Upload

Instead of tools extracting text, we send files natively to the LLM.

```python
async def chat_with_file(chat_id: int, file_path: str, caption: str = ""):
    thread_id = str(chat_id)
    generated_files_per_thread[thread_id] = []
    
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    mime_type, _ = mimetypes.guess_type(file_path)
    
    content = [
        {"type": "text", "text": caption or "Please analyze this attached file."},
        {"type": "file", "base64": b64_data, "mime_type": mime_type}
    ]
        
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke({"messages": [{"role": "user", "content": content}]}, config=config)
    
    files = generated_files_per_thread.get(thread_id, [])
    return result["messages"][-1].content, files
```

**How native upload works:**
1. File bytes are read and base64-encoded
2. Content becomes a **list** (not a string) with a `text` block and a `file` block
3. The LLM automatically handles parsing the document (PDFs, docs, images)!

### `clear_history()` — Memory Reset

```python
def clear_history(chat_id: int) -> None:
    thread_id = str(chat_id)
    keys_to_delete = [
        k for k in checkpointer.storage.keys()
        if isinstance(k, tuple) and len(k) > 0 and k[0] == thread_id
    ]
    for key in keys_to_delete:
        del checkpointer.storage[key]
```

Directly removes entries from `InMemorySaver`'s internal storage dict.

---

## 📄 File 4: `bot.py` — Telegram Bot

The entry point. Handles all Telegram interactions.

### Setup

```python
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters,
)
from agent import chat, chat_with_image, chat_with_file, clear_history

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
```

### Command: `/start`

```python
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = f"👋 Hello, **{user.first_name}**!\n\nI'm your AI assistant..."
    await update.message.reply_text(welcome, parse_mode="MarkdownV2")
```

### Command: `/clear`

```python
async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_chat.id)
    await update.message.reply_text("🧹 Conversation history cleared!")
```

### Handler: Text Messages

```python
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    response, files = await chat(chat_id, update.message.text)
    await send_long_message(update, response)
    
    # Send generated files back
    for fpath in files:
        await update.message.reply_document(document=open(fpath, 'rb'))
```

- `send_chat_action("typing")` shows the "typing..." indicator in Telegram
- The handler unpacks the `(response, files)` tuple and sends documents via `reply_document`

### Handler: Documents & Photos

```python
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    file_path = os.path.join(DOWNLOAD_DIR, doc.file_name)
    await file.download_to_drive(custom_path=file_path)

    response, files = await chat_with_file(chat_id, file_path, caption)
    await send_long_message(update, response)
    
    for fpath in files:
        await update.message.reply_document(document=open(fpath, 'rb'))
```

- `download_to_drive()` saves to disk
- It works identically to `handle_photo` and `handle_text`, routing output files directly to the user.

### Message Splitter

```python
async def send_long_message(update, text, max_length=4000):
    if len(text) <= max_length:
        await update.message.reply_text(text, parse_mode="Markdown")
        return
    # Split at newline boundaries and send chunks
    ...
```

Telegram has a **4096 character limit** per message. This utility splits at newline boundaries.

### Main & Handler Registration

```python
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("pdf", cmd_pdf))

    # Messages (order matters!)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling(drop_pending_updates=True)
```

**Handler order matters:** Commands are checked first, then photos, documents, and finally text. `~filters.COMMAND` excludes `/` commands from the text handler.

---

**Next:** [Part 3 — Running, Testing & Troubleshooting →](./03_running_and_troubleshooting.md)
