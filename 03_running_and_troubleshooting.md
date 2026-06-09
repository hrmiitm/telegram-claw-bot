# Part 3 — Running, Testing & Troubleshooting

## 🚀 Step-by-Step: Running the Bot

### 1. Install Dependencies

```bash
cd BasicChatbot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Your `.env` Values

```bash
# Edit .env with your actual tokens
nano .env
```

Minimum required:
```env
TELEGRAM_BOT_TOKEN=7123456789:AAH_your_token
MODEL_NAME=openai:gpt-4o
OPENAI_API_KEY=sk-your-key
```

### 3. Run the Bot

```bash
python bot.py
```

You should see:
```
2026-06-08 20:30:00 - __main__ - INFO - 🤖 Bot is starting...
```

### 4. Test in Telegram

1. Open Telegram → search for your bot's username
2. Send `/start` → should get welcome message
3. Type "Hello!" → should get AI response
4. Send a PDF file → bot will summarise it
5. Send a photo with caption "What is this?" → bot describes it
6. Send `/clear` → resets memory

---

## 🧪 Testing Checklist

| Test | How | Expected |
|------|-----|----------|
| `/start` | Send command | Welcome message with emoji |
| `/help` | Send command | List of all commands |
| Text chat | Type anything | AI response |
| Memory | Say "My name is X" then "What's my name?" | Remembers |
| `/clear` | Send command, then "What's my name?" | Doesn't remember |
| PDF | Send a PDF file | Auto-summarises |
| `/pdf` reply | Reply to a PDF with `/pdf` | Summarises |
| Photo | Send image with caption | Describes image |
| Document | Send .txt or .csv file | Reads and responds |
| `/stop` | Send command | Clears history + goodbye |
| Long response | Ask for a very long answer | Split into multiple messages |

---

## 🔥 Common Errors & Fixes

### Error: `TELEGRAM_BOT_TOKEN not set`

```
ValueError: TELEGRAM_BOT_TOKEN not set in .env file!
```

**Fix:** Make sure `.env` has `TELEGRAM_BOT_TOKEN=your_token` and `python-dotenv` is installed.

---

### Error: `Conflict: terminated by other getUpdates request`

```
telegram.error.Conflict: Conflict: terminated by other getUpdates request
```

**Fix:** Another instance of your bot is running. Kill it first:
```bash
# Find and kill the other process
ps aux | grep bot.py
kill <PID>
```

---

### Error: `openai.AuthenticationError`

**Fix:** Check your API key in `.env`. Make sure there are no extra spaces or quotes around the key.

---

### Error: `Model does not support images`

Not all models support multimodal. Use one of:
- `openai:gpt-4o` or `openai:gpt-4o-mini`
- `google_genai:gemini-2.5-flash`
- `anthropic:claude-sonnet-4-6`

Models like `openai:gpt-3.5-turbo` do NOT support images.

---

### Error: `File too large` (Telegram limit)

Telegram Bot API limits file downloads to **20 MB**. For larger files, you'll get an error from Telegram.

---

### Error: `Rate limit exceeded`

Your LLM provider has rate limits. Solutions:
- Wait and retry
- Use a different model/provider
- Add retry logic in `agent.py`

---

### Error: `Cannot parse Markdown` in Telegram

Some Markdown from the LLM may not be valid Telegram Markdown. Our `send_long_message` handles this with a fallback:

```python
try:
    await update.message.reply_text(text, parse_mode="Markdown")
except Exception:
    await update.message.reply_text(text)  # Plain text fallback
```

---

## 🔄 Using Different Providers

### OpenAI
```env
MODEL_NAME=openai:gpt-4o
OPENAI_API_KEY=sk-...
```
```bash
pip install langchain-openai
```

### Google Gemini
```env
MODEL_NAME=google_genai:gemini-2.5-flash
GOOGLE_API_KEY=AI...
```
```bash
pip install langchain-google-genai
```

### Anthropic Claude
```env
MODEL_NAME=anthropic:claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```
```bash
pip install langchain-anthropic
```

### Ollama (Local, Free)
```bash
# Install & run Ollama first: https://ollama.com
ollama pull llama3
```
```env
MODEL_NAME=ollama:llama3
```
```bash
pip install langchain-ollama
```

> ⚠️ Local models may not support multimodal (images). Use `ollama:llava` for vision.

---

## 🏭 Production Considerations

### 1. Persistent Memory

Replace `InMemorySaver` with a database-backed checkpointer:

```python
# In agent.py — replace InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(connection_string="postgresql://...")
await checkpointer.setup()  # Run once
```

### 2. Webhook Instead of Polling

For production, use webhooks (more efficient than polling):

```python
# In bot.py main()
app.run_webhook(
    listen="0.0.0.0",
    port=8443,
    url_path=BOT_TOKEN,
    webhook_url=f"https://yourdomain.com/{BOT_TOKEN}"
)
```

### 3. Error Retry

Add retry logic for LLM calls:

```python
import asyncio

async def chat_with_retry(chat_id, message, retries=3):
    for attempt in range(retries):
        try:
            return await chat(chat_id, message)
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise e
```

### 4. User Whitelisting

Restrict who can use the bot:

```python
ALLOWED_USERS = {123456789, 987654321}  # Telegram user IDs

async def handle_text(update, context):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    # ... rest of handler
```

---

## 📊 How the ReAct Agent Loop Works

When you send "Write a python script that prints hello world and save it":

```
Step 1: Agent receives message
        → Thinks: "I need to write python code and save it to a file"
        → Decides to call: create_file("hello.py", "print('hello world')")

Step 2: Tool executes
        → create_file saves to disk and tracks the path

Step 3: Agent receives tool result
        → Thinks: "The file was successfully created."
        → Generates final text response for the user

Step 4: Bot sends response
        → Telegram bot sends text: "Here is your script!"
        → Telegram bot sends document: hello.py
```

This is the **ReAct pattern** (Reason + Act):
1. **Reason** — the model thinks about what to do
2. **Act** — it calls a tool
3. **Observe** — it reads the tool output
4. **Repeat** — or generate the final answer

---

## 📝 Quick Reference: All Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with capabilities |
| `/help` | List all commands |
| `/clear` | Clear conversation history |
| `/stop` | Clear history + goodbye |
| `/pdf` | Reply to a PDF message to summarise |

## 📝 Quick Reference: Supported Inputs

| Input Type | How to Send | What Happens |
|-----------|-------------|-------------|
| Text | Just type | Agent responds conversationally |
| Photo | Send image (+ optional caption) | Agent describes/analyses image |
| PDF | Send as document | Agent reads & summarises |
| Text files | Send .txt/.csv/.json/.py/.md | Agent reads & responds |
| Any document | Send any file | Agent attempts to read |

---

**← Back to:** [Part 1 — Theory & Setup](./01_theory_and_setup.md) | [Part 2 — Code Walkthrough](./02_code_walkthrough.md)
