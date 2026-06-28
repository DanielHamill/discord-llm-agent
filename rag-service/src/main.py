import logging

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from pydantic import BaseModel

import rag

logger = logging.getLogger("rag-service")

app = FastAPI()


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    logger.info(f"Received prompt: {request.prompt}")
    response = rag.query(request.prompt)
    return ChatResponse(response=response)


def start() -> None:
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
