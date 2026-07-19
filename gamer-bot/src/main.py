import os
import logging

import discord
from dotenv import load_dotenv

import agent as agent_module

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OUTPUT_CHANNEL_NAME = os.getenv("OUTPUT_CHANNEL")
INPUT_CHANNEL_NAME = os.getenv("INPUT_CHANNEL")

PLACEHOLDER_CONTENT = "**Completed**\n_none yet_\n\n**Currently Playing**\n_none yet_\n\n**Queue**\n_none yet_\n\n**Waiting Room**\n_none yet_"

# establish discord connection
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

# get logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gamer-bot")

# holds the single managed message in output-channel
managed_message: discord.Message | None = None


@discord_client.event
async def on_ready():
    global managed_message
    logger.info(f"Logged in as {discord_client.user}")

    output_channel = discord.utils.get(discord_client.get_all_channels(), name=OUTPUT_CHANNEL_NAME)
    if output_channel is None:
        logger.error(f"Could not find output channel: {OUTPUT_CHANNEL_NAME}")
        return

    # look for a previous message sent by this bot
    async for msg in output_channel.history(limit=100):
        if msg.author == discord_client.user:
            managed_message = msg
            logger.info(f"Found existing managed message (id={msg.id})")
            break

    if managed_message is None:
        managed_message = await output_channel.send(PLACEHOLDER_CONTENT)
        logger.info(f"Sent placeholder message (id={managed_message.id})")

    agent_module.set_update_callback(set_content)


@discord_client.event
async def on_message(message: discord.Message):
    if message.author == discord_client.user:
        return

    if message.channel.name == INPUT_CHANNEL_NAME:
        completed, currently_playing, queue, waiting_room = get_content()
        await agent_module.run_agent(message.content, completed, currently_playing, queue, waiting_room, message.guild.id)


def format_message(completed: list[str], currently_playing: list[str], queue: list[str], waiting_room: list[str]) -> str:
    """Format four game lists into a Discord markdown string."""
    def lines(lst: list[str]) -> str:
        return "\n".join(f"- {g}" for g in lst) if lst else "_none yet_"
    return (
        f"**Completed**\n{lines(completed)}\n\n"
        f"**Currently Playing**\n{lines(currently_playing)}\n\n"
        f"**Queue**\n{lines(queue)}\n\n"
        f"**Waiting Room**\n{lines(waiting_room)}"
    )


def extract_lists(content: str) -> tuple[list[str], list[str], list[str], list[str]]:
    """Parse a formatted message string into (completed, currently_playing, queue, waiting_room) lists."""
    completed: list[str] = []
    currently_playing: list[str] = []
    queue: list[str] = []
    waiting_room: list[str] = []
    current_section: str | None = None
    for line in content.splitlines():
        line = line.strip()
        if line == "**Completed**":
            current_section = "completed"
        elif line == "**Currently Playing**":
            current_section = "currently_playing"
        elif line == "**Queue**":
            current_section = "queue"
        elif line == "**Waiting Room**":
            current_section = "waiting_room"
        elif line.startswith("- "):
            item = line[2:]
            if current_section == "completed":
                completed.append(item)
            elif current_section == "currently_playing":
                currently_playing.append(item)
            elif current_section == "queue":
                queue.append(item)
            elif current_section == "waiting_room":
                waiting_room.append(item)
    return completed, currently_playing, queue, waiting_room


def get_content() -> tuple[list[str], list[str], list[str], list[str]]:
    """Return the current game lists from the managed message."""
    raw = managed_message.content if managed_message else ""
    return extract_lists(raw)


async def set_content(completed: list[str], currently_playing: list[str], queue: list[str], waiting_room: list[str]) -> None:
    """Format and update the managed message in output-channel."""
    global managed_message
    if managed_message is None:
        logger.warning("No managed message to update")
        return

    content = format_message(completed, currently_playing, queue, waiting_room)
    logger.info("Updating managed message")
    managed_message = await managed_message.edit(content=content)
    logger.info("Updated managed message")


discord_client.run(DISCORD_TOKEN)
