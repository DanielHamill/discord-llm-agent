"""Export the content of a discord channel

on_ready is essentially the entrypoint for this script and
will get executed when the bot connects to the server. This script
supports multiple export formats."""
import os
from typing import Dict
import logging

import discord
from dotenv import load_dotenv

from data import get_message_payload
from exporters import get_exporter

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
EXPORTER_TYPE = os.getenv("EXPORTER_TYPE", "csv")
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "general")
OUT_PATH = os.getenv("OUT_PATH", "./exported_messages.csv")

# establish discord connection
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
discord_client = discord.Client(intents=intents)

# get logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("history-bot")
exporter = get_exporter(EXPORTER_TYPE, file_path=OUT_PATH)


@discord_client.event
async def on_ready():
    """Callback that gets run when the bot is ready."""
    logger.info(f'We have logged in as {discord_client.user}')
    channel_map: Dict[str, discord.TextChannel] = {}
    for channel in discord_client.get_all_channels():
        channel_map[channel.name] = channel

    channel = channel_map[CHANNEL_NAME]
    async for message in channel.history():
        exporter.export_message(logger=logger, message=get_message_payload(message))
    exporter.close()
    await discord_client.close()

    
discord_client.run(DISCORD_TOKEN)