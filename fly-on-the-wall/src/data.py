from typing import List, Optional

from pydantic import BaseModel
import discord


class Role(BaseModel):
    id: int
    name: str


class Author(BaseModel):
    id: int
    name: str
    nick: Optional[str] = None
    avatar_url: Optional[str] = None
    is_bot: bool
    roles: List[Role]


class Channel(BaseModel):
    id: int
    name: str
    topic: Optional[str] = None


class Guild(BaseModel):
    id: int
    name: str


class Mention(BaseModel):
    id: int
    name: str


class MessagePayload(BaseModel):
    message_id: int
    content: str
    created_at: str
    edited_at: Optional[str] = None
    author: Author
    channel: Channel
    guild: Guild
    mentions: List[Mention]
    reply_to_message_id: Optional[int] = None


def get_message_payload(message: discord.Message) -> MessagePayload:
    payload = {
        "message_id": message.id,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "author": {
            "id": message.author.id,
            "name": message.author.name,
            "nick": message.author.nick,
            "avatar_url": str(message.author.avatar.url) if message.author.avatar else None,
            "is_bot": message.author.bot,
            "roles": [{"id": role.id, "name": role.name} for role in message.author.roles],
        },
        "channel": {
            "id": message.channel.id,
            "name": message.channel.name,
            "topic": message.channel.topic if hasattr(message.channel, 'topic') else None,
        },
        "guild": {
            "id": message.guild.id,
            "name": message.guild.name,
        },
        "mentions": [{"id": user.id, "name": user.name} for user in message.mentions],
        "reply_to_message_id": message.reference.message_id if message.reference else None,
    }
    return MessagePayload.model_validate(payload)