import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
from pathlib import Path
import json
from datetime import date, timedelta
import dotenv

dotenv.load_dotenv()

USE_LAST_MONTH = os.environ.get("USE_LAST_MONTH", "")
start_date = os.environ.get("START_DATE", "")
end_date = os.environ.get("END_DATE", "")
query = os.environ.get("QUERY", "")
MESSAGES_SRC = os.environ.get("MESSAGES_SRC", "~/Data/discord-llm-data/exported_messages.csv")


model_name = "BAAI/bge-base-en-v1.5"
model_path = Path.home() / Path("models", model_name)
model = SentenceTransformer(model_name)

def load_data(csv_path: str = 'exported_messages.csv'):
    df = pd.read_csv(os.path.expanduser(csv_path))
    embeddings = np.array(df["embedding"].apply(json.loads).tolist())
    return df, embeddings

df, message_embeddings = load_data(MESSAGES_SRC)

timestamp_col = "created_at" if "created_at" in df.columns else "timestamp"

# Date range filter read from env vars:
#   USE_LAST_MONTH=true  → override START_DATE/END_DATE with last 30 days
#   START_DATE=yyyy-mm-dd
#   END_DATE=yyyy-mm-dd
use_last_month = USE_LAST_MONTH.lower() in ("1", "true", "yes")

if use_last_month:
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=30)).isoformat()

if start_date or end_date:
    dates = pd.to_datetime(df[timestamp_col], format='ISO8601', utc=True).dt.date
    mask = pd.Series(True, index=df.index)
    if start_date:
        mask &= dates >= date.fromisoformat(start_date)
    if end_date:
        mask &= dates <= date.fromisoformat(end_date)
    df = df.loc[mask]
    message_embeddings = message_embeddings[mask.to_numpy()]

# Sort by timestamp so positional context windows are chronological, keeping
# embeddings aligned with df rows.
sort_order = df[timestamp_col].argsort()
df = df.iloc[sort_order].reset_index(drop=True)
message_embeddings = message_embeddings[sort_order]

# --- Conversation window config ---
CONTEXT_BEFORE = 2
CONTEXT_AFTER = 3
TOP_CONVERSATIONS = 5

channel_col = next((c for c in ["channel_id", "channel", "guild_channel_id"] if c in df.columns), None)

def get_conversation(idx: int) -> list[dict]:
    """Return rows for the context window around idx, restricted to the same channel."""
    start = max(0, idx - CONTEXT_BEFORE)
    end = min(len(df) - 1, idx + CONTEXT_AFTER)
    rows = df.iloc[start:end + 1]
    if channel_col:
        target_channel = df.iloc[idx][channel_col]
        rows = rows[rows[channel_col] == target_channel]
    return rows.to_dict("records")

def format_conversation(conv: list[dict]) -> str:
    lines = []
    for row in conv:
        author = row.get("author", row.get("username", row.get("author_name", "unknown")))
        ts = row.get(timestamp_col, "")
        content = row.get("content", "")
        lines.append(f"  [{ts}] {author}: {content}")
    return "\n".join(lines)

# Search using individual message embeddings
query_embedding = model.encode([query])

cos_scores = cosine_similarity(query_embedding, message_embeddings)[0]
candidates = np.argsort(cos_scores)[::-1]

# Walk ranked candidates; skip any message already covered by a chosen conversation
seen_indices: set[int] = set()
conversations: list[tuple[int, float, list[dict]]] = []

for i in candidates:
    if i in seen_indices:
        continue
    conv = get_conversation(i)
    # Mark the full window (not just the channel-filtered subset) as seen to
    # avoid nearby messages spawning a nearly identical conversation.
    seen_indices.update(range(max(0, i - CONTEXT_BEFORE), min(len(df), i + CONTEXT_AFTER + 1)))
    conversations.append((int(i), float(cos_scores[i]), conv))
    if len(conversations) >= TOP_CONVERSATIONS:
        break

print(f"Query: {query!r}\n")
print(f"Top {TOP_CONVERSATIONS} conversations (sorted by anchor message similarity):\n")
for rank, (anchor_idx, score, conv) in enumerate(conversations, 1):
    print(f"--- Conversation {rank} [cos={score:.4f}] ---")
    print(format_conversation(conv))
    print()
