"""
agent.py — LangChain Agent with Memory
=======================================
Uses LangChain v1's `create_agent` with `InMemorySaver` checkpointer.

Key concepts:
  • Multimodal input: Files and images are sent directly to the LLM
    using LangChain's standard content blocks (`file` and `image_url`).
  • File generation: Uses `create_file` tool.
"""

import os
import base64
import mimetypes
from dotenv import load_dotenv

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from tools import ALL_TOOLS, generated_files_per_thread

load_dotenv(override=True)

# ──────────────────────────────────────────────
# 1. Configuration from .env
# ──────────────────────────────────────────────
MODEL_NAME = os.getenv("MODEL_NAME", "openai:gpt-4o")

SYSTEM_PROMPT = """You are a helpful, friendly AI assistant inside a Telegram bot.

Your capabilities:
- Answer questions on any topic.
- Read files and images directly (they will be sent to you as file attachments).
- Create and return files to the user (use the create_file tool).
- Tell the current date/time (use the get_datetime tool).

Guidelines:
- Keep responses concise and well-formatted for Telegram (use Markdown).
- When a user asks you to write code, create a report, or generate a document, ALWAYS use the `create_file` tool to save it so the user can download it.
- If you don't know something, say so honestly.
- Use bold (**text**) and bullet points for readability.
"""

# ──────────────────────────────────────────────
# 2. Create the Agent (singleton)
# ──────────────────────────────────────────────
checkpointer = InMemorySaver()

agent = create_agent(
    model=MODEL_NAME,
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


# ──────────────────────────────────────────────
# 3. Public API used by bot.py
# ──────────────────────────────────────────────
async def chat(chat_id: int, user_message: str) -> tuple[str, list[str]]:
    """Send a text message to the agent and return the response."""
    thread_id = str(chat_id)
    generated_files_per_thread[thread_id] = []
    
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
    )
    
    files = generated_files_per_thread.get(thread_id, [])
    return result["messages"][-1].content, files


async def chat_with_image(chat_id: int, user_message: str, image_bytes: bytes) -> tuple[str, list[str]]:
    """Send an image directly to the LLM (vision)."""
    thread_id = str(chat_id)
    generated_files_per_thread[thread_id] = []
    
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    content = [
        {"type": "text", "text": user_message or "What do you see in this image?"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
        },
    ]

    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": content}]},
        config=config,
    )
    
    files = generated_files_per_thread.get(thread_id, [])
    return result["messages"][-1].content, files


async def chat_with_file(chat_id: int, file_path: str, caption: str = "") -> tuple[str, list[str]]:
    """Send a file directly to the LLM using LangChain's standard file block."""
    thread_id = str(chat_id)
    generated_files_per_thread[thread_id] = []
    
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"
        
    text_prompt = caption or f"Please analyze this attached file: {os.path.basename(file_path)}"
    
    # If it's an image, use image_url for better compatibility with some providers
    if mime_type.startswith("image/"):
        content = [
            {"type": "text", "text": text_prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_data}"}}
        ]
    else:
        # Use LangChain standard file block
        content = [
            {"type": "text", "text": text_prompt},
            {"type": "file", "base64": b64_data, "mime_type": mime_type}
        ]
        
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": content}]},
        config=config,
    )
    
    files = generated_files_per_thread.get(thread_id, [])
    return result["messages"][-1].content, files


def clear_history(chat_id: int) -> None:
    """Clear the conversation history for a specific chat."""
    thread_id = str(chat_id)
    keys_to_delete = [
        k for k in checkpointer.storage.keys()
        if isinstance(k, tuple) and len(k) > 0 and k[0] == thread_id
    ]
    for key in keys_to_delete:
        del checkpointer.storage[key]
    if hasattr(checkpointer, "writes"):
        writes_to_delete = [
            k for k in checkpointer.writes.keys()
            if isinstance(k, tuple) and len(k) > 0 and k[0] == thread_id
        ]
        for key in writes_to_delete:
            del checkpointer.writes[key]
