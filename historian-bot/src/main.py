import os
import sys
import logging

import discord
import httpx
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TRIGGER_PHRASE = os.getenv("TRIGGER_PHRASE", "!historian-bot")
RAG_SERVICE_URI = os.getenv("RAG_SERVICE_URI", "http://localhost:8000")

# establish discord connection
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

# get logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("message-producer")

@discord_client.event
async def on_ready():
    logger.info(f'We have logged in as {discord_client.user}')


@discord_client.event
async def on_message(message: discord.Message):
    if message.author == discord_client.user:
        return
    
    if TRIGGER_PHRASE in message.content:
        prompt = message.content.replace(TRIGGER_PHRASE, "", 1).strip()
        async with httpx.AsyncClient() as client:
            try:
                logger.info("Making rag-service request.")
                resp = await client.post(
                    f"{RAG_SERVICE_URI}/chat",
                    json={"prompt": prompt},
                    timeout=300.0,
                )
                resp.raise_for_status()
                reply = resp.json()["response"]
            except Exception as e:
                logger.error(f"RAG service error: {e}")
                reply = "Sorry, I encountered an error processing your request."
        await message.reply(reply)

discord_client.run(DISCORD_TOKEN)
