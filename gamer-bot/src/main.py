import os
import logging

import discord
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OUTPUT_CHANNEL_NAME = os.getenv("OUTPUT_CHANNEL")
INPUT_CHANNEL_NAME = os.getenv("INPUT_CHANNEL")

PLACEHOLDER_CONTENT = "Status: initializing..."

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


@discord_client.event
async def on_message(message: discord.Message):
    if message.author == discord_client.user:
        return

    if message.channel.name == INPUT_CHANNEL_NAME:
        await update_message(f"Received message in non-input channel: {message.channel.name}")
        return

    # TODO: implement input-channel message handling


async def update_message(content: str) -> None:
    """Update the content of the managed message in output-channel."""
    global managed_message
    if managed_message is None:
        logger.warning("No managed message to update")
        return

    logger.info(f"Updating managed message with content: {content}")
    managed_message = await managed_message.edit(content=content)
    logger.info("Updated managed message")


discord_client.run(DISCORD_TOKEN)
