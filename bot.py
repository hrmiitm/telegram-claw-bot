"""
bot.py — Telegram Bot with LangChain Agent Integration
=======================================================
Handles all Telegram commands and message types, routes them to the
LangChain agent (agent.py), and sends responses back to the user.

Commands:
  /start  — Welcome message
  /help   — List available commands
  /clear  — Clear conversation history
  /stop   — Stop the bot for this user (clears history + goodbye)
  /pdf    — Reply to a PDF with this command to summarise it

Message types handled:
  • Text messages       → forwarded to agent
  • Photos (with caption) → multimodal agent call
  • Documents (PDF, txt, etc.) → downloaded, then agent processes via tools
"""

import os
import logging

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from agent import chat, chat_with_image, chat_with_file, clear_history

load_dotenv(override=True)

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ══════════════════════════════════════════════
# Command Handlers
# ══════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — send a welcome message."""
    user = update.effective_user
    welcome = (
        f"👋 Hello, **{user.first_name}**\\!\n\n"
        "I'm your AI assistant powered by LangChain\\. Here's what I can do:\n\n"
        "💬 Chat with me on any topic\n"
        "📄 Send me a PDF — I'll summarise it\n"
        "🖼️ Send me an image — I'll describe it\n"
        "📁 Send me text files — I'll read them\n\n"
        "Type /help for all commands\\."
    )
    await update.message.reply_text(welcome, parse_mode="MarkdownV2")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — list all commands."""
    help_text = (
        "🤖 **Available Commands:**\n\n"
        "/start — Welcome message\n"
        "/help — This help menu\n"
        "/clear — Clear conversation history\n"
        "/stop — Stop bot & clear history\n"
        "/pdf — Reply to a PDF to summarise it\n\n"
        "📌 **Tips:**\n"
        "• Just type to chat!\n"
        "• Send a photo with a caption to ask about it\n"
        "• Send any document and I'll try to read it"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — reset conversation memory."""
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    await update.message.reply_text("🧹 Conversation history cleared! Let's start fresh.")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop — clear history and say goodbye."""
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    await update.message.reply_text("👋 Goodbye! Your history has been cleared. Send /start to begin again.")


async def cmd_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pdf — must be a reply to a document message."""
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("⚠️ Reply to a PDF message with /pdf to summarise it.")
        return

    doc = update.message.reply_to_message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("⚠️ That doesn't look like a PDF file.")
        return

    await update.message.reply_text("📖 Reading your PDF... please wait.")

    # Download the file
    file = await context.bot.get_file(doc.file_id)
    file_path = os.path.join(DOWNLOAD_DIR, doc.file_name)
    await file.download_to_drive(custom_path=file_path)

    # Send to agent
    chat_id = update.effective_chat.id
    try:
        response, files = await chat_with_file(chat_id, file_path, "Summarise this PDF in detail with key points.")
        await send_long_message(update, response)
        for fpath in files:
            await update.message.reply_document(document=open(fpath, 'rb'))
    except Exception as e:
        logger.error(f"PDF processing error: {e}")
        await update.message.reply_text(f"❌ Error processing PDF: {e}")


# ══════════════════════════════════════════════
# Message Handlers
# ══════════════════════════════════════════════

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages — send to agent."""
    chat_id = update.effective_chat.id
    user_text = update.message.text

    # Show "typing" indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response, files = await chat(chat_id, user_text)
        await send_long_message(update, response)
        for fpath in files:
            await update.message.reply_document(document=open(fpath, 'rb'))
    except Exception as e:
        logger.error(f"Agent error: {e}")
        await update.message.reply_text(f"❌ Something went wrong: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photos — download and send to agent as multimodal input."""
    chat_id = update.effective_chat.id
    caption = update.message.caption or ""

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Get the highest resolution photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # Download to memory (as bytes)
    image_bytes = await file.download_as_bytearray()

    try:
        response, files = await chat_with_image(chat_id, caption, bytes(image_bytes))
        await send_long_message(update, response)
        for fpath in files:
            await update.message.reply_document(document=open(fpath, 'rb'))
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        await update.message.reply_text(f"❌ Error processing image: {e}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle documents — download and process via agent tools."""
    chat_id = update.effective_chat.id
    doc = update.message.document
    caption = update.message.caption or ""

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    await update.message.reply_text(f"📥 Received `{doc.file_name}`, processing...")

    # Download the file
    file = await context.bot.get_file(doc.file_id)
    file_path = os.path.join(DOWNLOAD_DIR, doc.file_name)
    await file.download_to_drive(custom_path=file_path)

    try:
        response, files = await chat_with_file(chat_id, file_path, caption)
        await send_long_message(update, response)
        for fpath in files:
            await update.message.reply_document(document=open(fpath, 'rb'))
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        await update.message.reply_text(f"❌ Error processing document: {e}")


# ══════════════════════════════════════════════
# Utility: Split long messages (Telegram 4096 char limit)
# ══════════════════════════════════════════════

async def send_long_message(update: Update, text: str, max_length: int = 4000) -> None:
    """Send a message, splitting into chunks if it exceeds Telegram's limit."""
    if len(text) <= max_length:
        try:
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception:
            # Fallback: send without Markdown if parsing fails
            await update.message.reply_text(text)
        return

    # Split into chunks at newline boundaries
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # Find a good split point
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(chunk)


# ══════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════

def main() -> None:
    """Build and run the Telegram bot."""
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file!")

    # Build the application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("pdf", cmd_pdf))

    # Register message handlers (order matters — commands are checked first)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start polling
    logger.info("🤖 Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
