import os
from typing import Dict
import logging
import asyncio

import json
import discord
import pika
from dotenv import load_dotenv

from data import get_message_payload

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# establish discord connection
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

# get logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("history-bot")

channel_map: Dict[str, discord.TextChannel] = {}


# async def get_messages(channel):
#     all_messages = []
#     async for message in channel.history():
#         all_messages.append(message.content)
#     return all_messages

@discord_client.event
async def on_ready():
    logger.info(f'We have logged in as {discord_client.user}')
    for channel in discord_client.get_all_channels():
        channel_map[channel.name] = channel

    general = channel_map["general"]
    async for message in general.history():
        print(message.content)


# @discord_client.event
# async def on_message(message):
#     logger.info("Reading message.")

discord_client.run(DISCORD_TOKEN)