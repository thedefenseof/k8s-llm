import os
import sys
import requests

URL = os.getenv("VLLM_URL", "http://localhost:8000/v1/chat/completions")
MODEL = os.getenv("MODEL", "/models/Qwen--Qwen2.5-0.5B-Instruct")
API_KEY = os.getenv("API_KEY")


def ask(question):
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": question}],
        "max_tokens": 100,
    }

    r = requests.post(URL, json=payload, headers=headers, timeout=300)
    print("HTTP статус:", r.status_code)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Say hello in one short sentence."
    print(ask(question))