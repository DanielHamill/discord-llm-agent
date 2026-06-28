import time
import requests

HOST = "http://136.55.181.222:11434"


def list_models() -> list[str]:
    response = requests.get(f"{HOST}/api/tags")
    response.raise_for_status()
    return [m["model"] for m in response.json().get("models", [])]


def prompt_model(model: str, prompt: str, timer: bool = False) -> str:
    start = time.perf_counter()
    response = requests.post(
        f"{HOST}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
    )
    response.raise_for_status()
    if timer:
        print(f"Request time: {time.perf_counter() - start:.2f}s")
    return response.json()["message"]["content"]


if __name__ == "__main__":
    models = list_models()
    if "qwen3.5:0.8b" in models:
        reply = prompt_model("qwen3.5:0.8b", "Say hello in one sentence.", timer=True)
        print(reply)
    else:
        print("Model qwen3.5:0.8b not found in available models.")
