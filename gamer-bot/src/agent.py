from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_ollama import ChatOllama

load_dotenv()

logger = logging.getLogger("gamer-bot.agent")

_model_name = os.getenv("MODEL_NAME", "qwen3.5:4b")
_ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

_update_callback: Callable[[list[str], list[str], list[str], list[str]], Awaitable[None]] | None = None


def set_update_callback(callback: Callable[[list[str], list[str], list[str], list[str]], Awaitable[None]]) -> None:
    """Register the async function that pushes the updated lists to the Discord message."""
    global _update_callback
    _update_callback = callback


@tool
async def update_message(
    completed: list[str],
    currently_playing: list[str],
    queue: list[str],
    waiting_room: list[str],
) -> str:
    """Update the game lists displayed in the Discord channel.

    Args:
        completed: Games the user has finished.
        currently_playing: Games the user is actively playing.
        queue: Games the user plans to play next.
        waiting_room: Games the user is interested in but not yet committed to.
    """
    if _update_callback is not None:
        await _update_callback(completed, currently_playing, queue, waiting_room)
    return "Message updated successfully."


_system_prompt = (
    "You monitor a Discord conversation and manage a gamer's game list across four categories: "
    "Completed (finished games), Currently Playing (actively playing), "
    "Queue (committed to play next), and Waiting Room (interested but not yet committed). "
    "Only call the update_message tool if the latest message contains new information "
    "that requires a change to any of the lists. "
    "If the message is just conversation or does not affect the lists, do nothing. "
    "Pass only plain game titles as list items — no markdown or formatting."
)

_agent = create_agent(
    ChatOllama(model=_model_name, base_url=_ollama_base_url),
    tools=[update_message],
    system_prompt=_system_prompt,
)
logger.info("Gamer agent initialized with model: %s", _model_name)

_SESSION_TIMEOUT = timedelta(hours=1)
_sessions: dict[int, list[tuple[datetime, str]]] = {}


async def run_agent(
    prompt: str,
    completed: list[str],
    currently_playing: list[str],
    queue: list[str],
    waiting_room: list[str],
    guild_id: int,
) -> str:
    """Invoke the agent with the session window history and current user message."""
    now = datetime.now()
    session = _sessions.setdefault(guild_id, [])

    # Reset session if idle for over an hour
    if session and (now - session[-1][0]) > _SESSION_TIMEOUT:
        logger.info("Session window expired for guild %d — starting new session", guild_id)
        session.clear()

    # Inject current list state as context in the first message of the session
    if not session:
        content = (
            f"Current lists:\n"
            f"Completed: {completed}\n"
            f"Currently Playing: {currently_playing}\n"
            f"Queue: {queue}\n"
            f"Waiting Room: {waiting_room}\n\n"
            f"{prompt}"
        )
    else:
        content = prompt

    session.append((now, content))

    messages = [{"role": "user", "content": c} for _, c in session]
    response = await _agent.ainvoke({"messages": messages})

    return response["messages"][-1].content
