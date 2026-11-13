"""Verify the DAY06 Ollama and Milvus endpoints from the repository root."""
import json
import os
from contextlib import closing
from urllib.request import Request, urlopen

from pymilvus import MilvusClient


def main():
    ollama = os.getenv("OLLAMA_URL", "http://192.168.1.246:11434").rstrip("/")
    milvus = os.getenv("MILVUS_URI", "http://192.168.1.246:19530")
    model = "qwen3-embedding:0.6b"
    payload = {"model": model, "input": "DAY06 environment check"}
    request = Request(f"{ollama}/api/embed", json.dumps(payload).encode(),
                      {"Content-Type": "application/json"})
    with urlopen(request, timeout=60) as response:
        vectors = json.load(response)["embeddings"]
    if len(vectors) != 1 or len(vectors[0]) != 1024:
        raise RuntimeError("Expected one 1024-dimensional embedding")
    print(f"Ollama: {model}, 1024 dimensions")
    with closing(MilvusClient(milvus, timeout=10)) as client:
        print(f"Milvus {client.get_server_version()} at {milvus}")


if __name__ == "__main__":
    main()
