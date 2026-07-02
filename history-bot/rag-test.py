#!/usr/bin/env python
# coding: utf-8

import json
import pandas as pd
from sentence_transformers import SentenceTransformer

from storage.storage_manager import WeaviateVectorStore
from src.rag import RAGPipeline


MESSAGES_SRC = "./exported_messages.csv"
CLEAR_COLLECTION = False  # Set to True to delete and recreate the collection

# Pre-requisite: start Weaviate with Docker before running this cell:
#   docker run -d --rm -p 8081:8080 -p 50052:50051 cr.weaviate.io/semitechnologies/weaviate:latest
store = WeaviateVectorStore(port=8081, grpc_port=50052)

if CLEAR_COLLECTION and store.collection_exists():
    print("CLEAR_COLLECTION=True — deleting existing collection.")
    store.delete_collection()

if store.collection_exists():
    print("Collection already exists — reusing existing data.")
else:
    df = pd.read_csv(MESSAGES_SRC)
    df["embedding"] = df["embedding"].apply(json.loads)
    df["timestamp_parsed"] = pd.to_datetime(df["timestamp"], format="ISO8601", utc=True)
    print(f"Loaded {len(df)} messages")
    store.insert_messages(df)

encoder = SentenceTransformer("BAAI/bge-base-en-v1.5")
pipeline = RAGPipeline(store=store, encoder=encoder)

query = "What camping trips have there been?"
response = pipeline.query(query, num=6, model_name="gemma3:1b", timer=True)
print(response["content"])

store.close()