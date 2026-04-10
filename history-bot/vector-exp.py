import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics.pairwise import euclidean_distances
import os
from pathlib import Path
import json
from datetime import date, timedelta

model_name =  "BAAI/bge-base-en-v1.5"
model_path = Path.home() / Path("models", model_name)
model = SentenceTransformer(model_name)

def load_data(csv_path: str = 'exported_messages.csv'):
    import json
    import numpy as np
    import pandas as pd

    df = pd.read_csv(csv_path)
    embeddings = np.array(df["embedding"].apply(json.loads).tolist())
    return df, embeddings

df, message_embeddings = load_data("~/Data/discord-llm-data/exported_messages.csv")

# Date range filter read from env vars:
#   USE_LAST_MONTH=true  → override START_DATE/END_DATE with last 30 days
#   START_DATE=yyyy-mm-dd
#   END_DATE=yyyy-mm-dd
use_last_month = os.environ.get("USE_LAST_MONTH", "").lower() in ("1", "true", "yes")
start_date = os.environ.get("START_DATE")  # e.g. "2024-01-01"
end_date = os.environ.get("END_DATE")      # e.g. "2024-12-31"

if use_last_month:
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=30)).isoformat()

if start_date or end_date:
    timestamp_col = "created_at" if "created_at" in df.columns else "timestamp"
    dates = pd.to_datetime(df[timestamp_col], format='ISO8601', utc=True).dt.date
    mask = pd.Series(True, index=df.index)
    if start_date:
        mask &= dates >= date.fromisoformat(start_date)
    if end_date:
        mask &= dates <= date.fromisoformat(end_date)
    df = df.loc[mask].reset_index(drop=True)
    message_embeddings = message_embeddings[mask.to_numpy()]

messages = df["content"]

# Example: find the most similar messages to a query
query = "I'm planning on hosting/throwing an event, party or hangout if anyone want to hang out in the near future."
query_embedding = model.encode([query])

# Cosine similarity: higher score = more similar
cos_scores = cosine_similarity(query_embedding, message_embeddings)[0]

# Euclidean distance: lower score = more similar
euc_distances = euclidean_distances(query_embedding, message_embeddings)[0]

# Top-5 most similar messages by cosine similarity
top_idx = np.argsort(cos_scores)[::-1][:15]
print(f"Query: {query!r}\n")
print("Top similar messages (cosine similarity):")
for rank, i in enumerate(top_idx, 1):
    print(f"  {rank}. [cos={cos_scores[i]:.4f}, euc={euc_distances[i]:.4f}] {messages[i]!r}")

