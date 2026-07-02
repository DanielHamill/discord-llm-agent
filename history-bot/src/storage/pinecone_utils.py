import os

import pandas as pd
from pinecone import Pinecone
import dotenv

dotenv.load_dotenv()

# Initialize a Pinecone client with your API key
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

def create_index_using_model(index_name: str, model_name: str) -> None:
    if not pc.has_index(index_name):
        pc.create_index_for_model(
            name=index_name,
            cloud="aws",
            region="us-east-1",
            embed={
                "model": model_name,
                "field_map": {"text": "chunk_text"}
            }
        )
        
def preprocess_dataframe(df: pd.DataFrame) -> list[dict]:
    records = []
    for _, row in df.iterrows():
        records.append({
            "id": str(row["id"]),
            "chunk_text": row["content"],
            "user": row["user"],
            "channel": row["channel"],
            "timestamp": row["timestamp"],
        })
    return records

def upsert_records(index_name: str, namespace: str, records: list[dict], batch_size: int = 96) -> None:
    index = pc.Index(index_name)
    for i in range(0, len(records), batch_size):
        index.upsert_records(namespace, records[i:i + batch_size])


if __name__	== "__main__":
    # create_index_using_model("discord-messages", "llama-text-embed-v2")
    df = pd.read_csv("./exported_messages.csv")
    df["channel"] = "events"
    records = preprocess_dataframe(df)
    upsert_records("discord-messages", "parking-deck", records)