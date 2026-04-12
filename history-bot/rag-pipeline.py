#!/usr/bin/env python
# coding: utf-8

# In[17]:


import atexit
import pandas as pd
import json
import weaviate
from sentence_transformers import SentenceTransformer
from datetime import datetime, timedelta
import numpy as np
from ollama import chat


# ```
# docker run -d --rm -p 8081:8080 -p 50052:50051 cr.weaviate.io/semitechnologies/weaviate:latest
# ```

# In[2]:


# MESSAGES_SRC = "~/Data/discord-llm-data/exported_messages.csv"
MESSAGES_SRC = "./exported_messages.csv"
CLEAR_COLLECTION = False  # Set to True to delete and recreate the collection

# Model is only needed to encode th
# e query at search time.
model = SentenceTransformer("BAAI/bge-base-en-v1.5")


# In[3]:


import weaviate.classes as wvc

# Pre-requisite: start Weaviate with Docker before running this cell:
#   docker run -d --rm -p 8081:8080 -p 50052:50051 cr.weaviate.io/semitechnologies/weaviate:latest

client = weaviate.connect_to_local(port=8081, grpc_port=50052)
atexit.register(client.close)

COLLECTION_NAME = "DiscordMessage"

if CLEAR_COLLECTION and client.collections.exists(COLLECTION_NAME):
    print(f"CLEAR_COLLECTION=True — deleting existing collection '{COLLECTION_NAME}'.")
    client.collections.delete(COLLECTION_NAME)

if client.collections.exists(COLLECTION_NAME):
    print(f"Collection '{COLLECTION_NAME}' already exists — reusing existing data.")
    messages = client.collections.get(COLLECTION_NAME)
else:
    # --- Create collection ---
    # We supply our own vectors, so vectorizer is set to none.
    df = pd.read_csv(MESSAGES_SRC)
    df["embedding"] = df["embedding"].apply(json.loads)
    # Parse timestamps to timezone-aware datetimes (required for DATE type)
    df["timestamp_parsed"] = pd.to_datetime(df["timestamp"], format="ISO8601", utc=True)

    print(f"Loaded {len(df)} messages")
    df.head()

    messages = client.collections.create(
        name=COLLECTION_NAME,
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[
            wvc.config.Property(name="message_id", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="author",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content",    data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="created_at", data_type=wvc.config.DataType.DATE),
        ],
    )

    # --- Ingest using pre-computed embeddings from the CSV ---
    objects = [
        wvc.data.DataObject(
            properties={
                "message_id": str(row["id"]),
                "author":     str(row["user"]),
                "content":    str(row["content"]),
                "created_at": row["timestamp_parsed"].to_pydatetime(),
            },
            vector=row["embedding"],
        )
        for _, row in df.iterrows()
    ]

    result = messages.data.insert_many(objects)
    print(f"Inserted {len(objects)} messages. Errors: {len(result.errors)}")


# In[4]:


def query_db_with_time_filter(query: str, num: int = 6, start_datetime: datetime = None, end_datetime: datetime = None):
    query_vector = model.encode(query).tolist()

    filters = None
    if start_datetime is not None:
        filters = wvc.query.Filter.by_property("created_at").greater_or_equal(start_datetime)
    if end_datetime is not None:
        end_filter = wvc.query.Filter.by_property("created_at").less_or_equal(end_datetime)
        filters = (filters & end_filter) if filters is not None else end_filter

    # Hybrid search combines BM25 keyword matching with vector similarity.
    return messages.query.hybrid(
        query=query,
        vector=query_vector,
        limit=num,
        filters=filters,
        return_metadata=wvc.query.MetadataQuery(score=True),
    )


# In[5]:


def get_message_conversation(message_id: str, timeframe_minutes: int, max_messages: int = 20) -> list:
    """Fetch messages within a symmetric time window around a given message,
    limited to max_messages with the anchor message kept in the centre.

    Returns a list of property dicts sorted by created_at.
    """
    # --- 1. Look up the anchor message to get its timestamp ---
    anchor_result = messages.query.fetch_objects(
        filters=wvc.query.Filter.by_property("message_id").equal(message_id),
        limit=1,
    )
    if not anchor_result.objects:
        raise ValueError(f"No message found with message_id={message_id!r}")

    anchor_ts: datetime = anchor_result.objects[0].properties["created_at"]

    # --- 2. Build the symmetric window around the anchor ---
    half = timedelta(minutes=timeframe_minutes / 2)
    start = anchor_ts - half
    end   = anchor_ts + half

    # --- 3. Fetch all messages in that window ---
    result = messages.query.fetch_objects(
        filters=(
            wvc.query.Filter.by_property("created_at").greater_or_equal(start)
            & wvc.query.Filter.by_property("created_at").less_or_equal(end)
        ),
        limit=10_000,
    )

    conversation = sorted(
        [obj.properties for obj in result.objects],
        key=lambda p: p["created_at"],
    )

    # --- 4. Centre the anchor and limit total messages ---
    if len(conversation) > max_messages:
        anchor_idx = next(
            (i for i, p in enumerate(conversation) if p["message_id"] == message_id),
            len(conversation) // 2,
        )
        half_n = max_messages // 2
        start_idx = max(0, anchor_idx - half_n)
        end_idx = start_idx + max_messages
        # Shift window back if it overruns the end
        if end_idx > len(conversation):
            end_idx = len(conversation)
            start_idx = max(0, end_idx - max_messages)
        conversation = conversation[start_idx:end_idx]

    return conversation


# In[6]:


def query_result_conversations(query_results):
  all_conversations = []
  for result in query_results.objects:
    test_id = result.properties["message_id"]
    conversation = get_message_conversation(test_id, timeframe_minutes=30)
    all_conversations.append(conversation)
  return all_conversations


# In[ ]:


import time

def ask(messages: list, model: str = 'qwen3.5:0.8b', think: bool = False, timer: bool = False) -> dict:
  start = time.time()
  response = chat(
      model=model,
      messages=messages,
      think=think,
  )
  elapsed = time.time() - start
  if timer:
      print(f"ask() took {elapsed:.2f}s")
  return {
      'thinking': response.message.thinking or '',
      'content': response.message.content or '',
  }


# In[7]:


# Configurable time range for the search filter
query = "What camping trips have there been?"
query_results = query_db_with_time_filter(query, num=6)
all_conversations = query_result_conversations(query_results)


# In[8]:


for res in query_results.objects:
    p = res.properties
    print(f"  {p['created_at']}  {p['author']}: {p['content']}")


# In[12]:


combined_conversations = ""
for conversation in all_conversations:
    combined_conversations += "Conversation:\n"
    for msg in conversation:
        combined_conversations += f"  {msg['created_at']}  {msg['author']}: {msg['content']}\n"
    combined_conversations += "\n"


# In[19]:


prompt = f"Use the conversation below to answer the question: {query}. Ignore any conversations that don't seem relevant.\n\n{combined_conversations}"


# In[23]:


response = ask(
    messages=[
        {"role": "user", "content": prompt},
    ],
    model='qwen3.5:0.8b',
    think=False,
    timer=True,
)



print(response["content"])

client.close()