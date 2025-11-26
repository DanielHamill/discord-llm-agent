import os
import sys
import logging

import discord
import pika
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MESSAGE_BROKER_HOST = os.getenv("MESSAGE_BROKER_HOST")
EXCHANGE = os.getenv("EXCHANGE")

# establish discord connection
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

# establish message broker connection

# connection = pika.SelectConnection(
#     pika.ConnectionParameters(host=MESSAGE_BROKER_HOST)
# )
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=MESSAGE_BROKER_HOST))
channel = connection.channel()
channel.exchange_declare(exchange=EXCHANGE, exchange_type='fanout')

# get logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("message-producer")

@discord_client.event
async def on_ready():
    logger.info(f'We have logged in as {discord_client.user}')


def get_message_payload(message: discord.Message) -> str:
    return ""


@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    payload = get_message_payload(message)
    channel.basic_publish(exchange=EXCHANGE, routing_key='', body=payload)
    # connection.close()
    logger.info("Publishing message.")

discord_client.run(DISCORD_TOKEN)
