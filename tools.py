"""
tools.py — Agent Tools for the Telegram Chatbot
================================================
Custom tools the LangChain agent can call:
  • create_file — Save generated content to a file
  • get_datetime — Get the current date and time
"""

import os
from datetime import datetime

from langchain.tools import tool
from langchain_core.runnables.config import RunnableConfig

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Global dictionary to track generated files per thread
# Format: {"chat_id": ["path/to/file1.md", "path/to/file2.py"]}
generated_files_per_thread = {}

# ──────────────────────────────────────────────
# Tool 1: File Generator
# ──────────────────────────────────────────────
@tool
def create_file(filename: str, content: str, config: RunnableConfig) -> str:
    """Create a text-based file (e.g. .md, .py, .txt, .csv) with the given content.
    Use this tool when the user asks you to generate a file, write code into a file,
    create a markdown document, etc.
    
    Args:
        filename: Name of the file with extension (e.g., 'report.md').
        content: The text content to write into the file.
    Returns:
        Confirmation message that the file was created.
    """
    try:
        thread_id = config["configurable"]["thread_id"]
        if thread_id not in generated_files_per_thread:
            generated_files_per_thread[thread_id] = []
            
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        generated_files_per_thread[thread_id].append(filepath)
        return f"Success! File saved at {filepath}. The bot will send it to the user automatically."
    except Exception as e:
        return f"Error creating file: {e}"


# ──────────────────────────────────────────────
# Tool 2: Current Date & Time
# ──────────────────────────────────────────────
@tool
def get_datetime() -> str:
    """Get the current date and time. Use this when the user asks about today's date or time."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y — %I:%M %p")


# ──────────────────────────────────────────────
# All tools list (imported by agent.py)
# ──────────────────────────────────────────────
ALL_TOOLS = [create_file, get_datetime]
