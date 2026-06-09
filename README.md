# Telegram AI Assistant (BasicChatbot)

A powerful, multimodal AI assistant integrated with Telegram, powered by LangChain and built using a robust ReAct agent architecture. 

## ✨ Features
- **Conversational AI**: Chat seamlessly on any topic using leading LLM providers.
- **Multimodal Support**: Send images with captions, and the bot will describe or analyze them.
- **Document Processing**: Send PDFs, text, or code files, and the agent can read and summarize them.
- **Autonomous File Generation**: Ask the bot to write code or draft a report, and it will generate and return the downloadable file to you directly.
- **Memory**: Remembers conversation history using LangGraph's checkpointer.

---

## 🚀 Quick Start

### 1. Configuration
Create a `.env` file in the root directory and add your credentials:
```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
MODEL_NAME=openai:gpt-4o-mini
OPENAI_API_KEY=your-api-key
```

### 2. Controlling the Bot
You can easily manage the bot's lifecycle using the provided shell script:

```bash
# Start the bot in the background
./bot.sh start

# Check if the bot is currently running
./bot.sh status

# Restart the bot cleanly
./bot.sh restart

# Stop the bot
./bot.sh stop
```

*Note: Logs are saved automatically to `bot.log`.*

---

## 📚 Documentation
For a deep dive into how the bot works, architectural decisions, and troubleshooting steps, refer to the detailed documentation included in this repository:

1. [Theory & Setup](01_theory_and_setup.md)
2. [Code Walkthrough](02_code_walkthrough.md)
3. [Running & Troubleshooting](03_running_and_troubleshooting.md)
