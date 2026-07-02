import logging
import os

logging.basicConfig(level=logging.INFO)

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

import rag

logger = logging.getLogger("rag-service")

_model_unavailable_msg = os.getenv(
    "MODEL_SERVER_UNAVAILABLE_MSG",
    "The model server is currently unavailable. Please try again later.",
)

app = FastAPI()


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    logger.info(f"Received prompt: {request.prompt}")
    try:
        response = rag.query(request.prompt)
    except httpx.ConnectTimeout:
        logger.error("Could not connect to model server")
        return ChatResponse(response=_model_unavailable_msg)
    return ChatResponse(response=response)


def start() -> None:
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
