# rag-service

FastAPI microservice exposing a RAG-backed chat endpoint.

## Structure

```
rag-service/
  src/
    main.py   # FastAPI app
    rag.py    # RAG logic
  pyproject.toml
  dockerfile
```

## Running locally

```bash
uv sync
uv run start
```

Server starts on `http://localhost:8000`.

## Endpoints

### `POST /chat`

**Request**
```json
{ "prompt": "your question here" }
```

**Response**
```json
{ "response": "..." }
```

## Docker

```bash
docker build -t rag-service .
docker run -p 8000:8000 rag-service
```
