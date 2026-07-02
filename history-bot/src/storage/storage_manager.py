from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class SearchResult:
    properties: dict
    score: float = 0.0


class VectorStore(ABC):
    """Abstract interface for a vector store.

    Implementations must store and retrieve Discord messages keyed by
    ``message_id``, supporting vector-hybrid search and time-window lookups.
    """

    @abstractmethod
    def collection_exists(self) -> bool: ...

    @abstractmethod
    def delete_collection(self) -> None: ...

    @abstractmethod
    def insert_messages(self, df: pd.DataFrame) -> None:
        """Ingest pre-embedded messages from a DataFrame.

        Expected columns: ``id``, ``user``, ``content``, ``timestamp_parsed``
        (timezone-aware datetime), ``embedding`` (list of floats).
        """
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        vector: list[float],
        num: int,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
    ) -> list[SearchResult]:
        """Hybrid (keyword + vector) search with optional time filter."""
        ...

    @abstractmethod
    def get_message_by_id(self, message_id: str) -> dict | None: ...

    @abstractmethod
    def get_messages_in_window(
        self,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[dict]:
        """Return messages in [start, end], sorted by created_at."""
        ...

    @abstractmethod
    def close(self) -> None: ...


class WeaviateVectorStore(VectorStore):
    """VectorStore backed by a local Weaviate instance.

    Pre-requisite — start Weaviate with Docker:
        docker run -d --rm -p 8081:8080 -p 50052:50051 \\
            cr.weaviate.io/semitechnologies/weaviate:latest
    """

    COLLECTION_NAME = "DiscordMessage"

    def __init__(self, port: int = 8081, grpc_port: int = 50052) -> None:
        import atexit

        import weaviate
        import weaviate.classes as wvc

        self._wvc = wvc
        self._client = weaviate.connect_to_local(port=port, grpc_port=grpc_port)
        atexit.register(self.close)

        if self._client.collections.exists(self.COLLECTION_NAME):
            self._collection = self._client.collections.get(self.COLLECTION_NAME)
        else:
            self._collection = None

    def collection_exists(self) -> bool:
        return self._client.collections.exists(self.COLLECTION_NAME)

    def delete_collection(self) -> None:
        self._client.collections.delete(self.COLLECTION_NAME)
        self._collection = None

    def insert_messages(self, df: pd.DataFrame) -> None:
        wvc = self._wvc
        self._collection = self._client.collections.create(
            name=self.COLLECTION_NAME,
            vectorizer_config=wvc.config.Configure.Vectorizer.none(),
            properties=[
                wvc.config.Property(name="message_id", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="author",     data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="content",    data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="created_at", data_type=wvc.config.DataType.DATE),
            ],
        )

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

        result = self._collection.data.insert_many(objects)
        print(f"Inserted {len(objects)} messages. Errors: {len(result.errors)}")

    def search(
        self,
        query: str,
        vector: list[float],
        num: int,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
    ) -> list[SearchResult]:
        wvc = self._wvc
        filters = None
        if start_datetime is not None:
            filters = wvc.query.Filter.by_property("created_at").greater_or_equal(start_datetime)
        if end_datetime is not None:
            end_filter = wvc.query.Filter.by_property("created_at").less_or_equal(end_datetime)
            filters = (filters & end_filter) if filters is not None else end_filter

        result = self._collection.query.hybrid(
            query=query,
            vector=vector,
            limit=num,
            filters=filters,
            return_metadata=wvc.query.MetadataQuery(score=True),
        )
        return [
            SearchResult(properties=obj.properties, score=obj.metadata.score or 0.0)
            for obj in result.objects
        ]

    def get_message_by_id(self, message_id: str) -> dict | None:
        result = self._collection.query.fetch_objects(
            filters=self._wvc.query.Filter.by_property("message_id").equal(message_id),
            limit=1,
        )
        if not result.objects:
            return None
        return result.objects[0].properties

    def get_messages_in_window(
        self,
        start: datetime,
        end: datetime,
        limit: int = 10_000,
    ) -> list[dict]:
        wvc = self._wvc
        result = self._collection.query.fetch_objects(
            filters=(
                wvc.query.Filter.by_property("created_at").greater_or_equal(start)
                & wvc.query.Filter.by_property("created_at").less_or_equal(end)
            ),
            limit=limit,
        )
        return sorted(
            [obj.properties for obj in result.objects],
            key=lambda p: p["created_at"],
        )

    def close(self) -> None:
        self._client.close()
