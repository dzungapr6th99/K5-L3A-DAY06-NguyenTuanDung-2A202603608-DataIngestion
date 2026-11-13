"""Ingest the pinned VLA corpus into Milvus from the repository root."""
import hashlib
import json
import os
import re
import unicodedata
from contextlib import closing
from pathlib import Path
from urllib.request import Request, urlopen

from pymilvus import DataType, MilvusClient

MODEL = "qwen3-embedding:0.6b"
DIM = 1024


def normalize(text):
    return " ".join(re.sub(r"<!--.*?-->", "", unicodedata.normalize("NFC", text), flags=re.S).split())


def embed(ollama, texts):
    payload = {"model": MODEL, "input": texts, "truncate": False}
    request = Request(f"{ollama}/api/embed", json.dumps(payload).encode(),
                      {"Content-Type": "application/json"})
    with urlopen(request, timeout=120) as response:
        vectors = json.load(response)["embeddings"]
    if len(vectors) != len(texts) or any(len(vector) != DIM for vector in vectors):
        raise RuntimeError("Unexpected embedding response")
    return vectors


def chunks(source, strategy):
    source = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    sections = [source] if strategy == "fixed" else re.split(r"(?m)(?=^#{1,6} )", source)
    offset = 0
    for section in sections:
        text = normalize(section)
        if not text:
            continue
        for start in range(0, len(text), 675):
            yield offset + start, text[start:start + 750]
            if start + 750 >= len(text):
                break
        offset += len(text) + 1


def main(strategy="fixed"):
    ollama = os.getenv("OLLAMA_URL", "http://192.168.1.246:11434").rstrip("/")
    milvus = os.getenv("MILVUS_URI", "http://192.168.1.246:19530")
    manifest = Path("data/manifest.json").read_bytes()
    revision = hashlib.sha256(manifest).hexdigest()[:12]
    name = f"day06_vla_{strategy}_{revision}"
    entries = json.loads(manifest)["sources"]
    rows = []
    for entry in entries:
        raw = Path(entry["local_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"Hash mismatch for {entry['local_path']}")
        source = unicodedata.normalize("NFC", raw.decode("utf-8-sig"))
        text = normalize(source)
        if len(text) != entry["pages"][0]["chars"]:
            raise ValueError(f"Character count mismatch for {entry['local_path']}")
        for start, chunk in chunks(source, strategy):
            key = hashlib.sha256(f"{entry['source_id']}:{start}".encode()).hexdigest()
            rows.append(dict(id=key, document_id=entry["source_id"], source=entry["source_path_or_url"],
                             page=1, category=entry["category"], offset=start, text=chunk))

    with closing(MilvusClient(milvus, timeout=60)) as client:
        if not client.has_collection(name):
            schema = client.create_schema(auto_id=False)
            for field, size in (("id", 64), ("document_id", 256), ("source", 512),
                                ("category", 32), ("text", 4096)):
                schema.add_field(field, DataType.VARCHAR, max_length=size, is_primary=field == "id")
            schema.add_field("page", DataType.INT64)
            schema.add_field("offset", DataType.INT64)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=DIM)
            indexes = client.prepare_index_params()
            indexes.add_index(field_name="vector", index_type="FLAT", metric_type="COSINE")
            client.create_collection(name, schema=schema, index_params=indexes, consistency_level="Strong")

        for start in range(0, len(rows), 32):
            batch = rows[start:start + 32]
            vectors = embed(ollama, [row["text"] for row in batch])
            client.upsert(name, [dict(row, vector=vector) for row, vector in zip(batch, vectors)])
            if start % 256 == 0 or start + len(batch) == len(rows):
                print(f"{start + len(batch)}/{len(rows)} chunks", flush=True)
        client.flush(name)
        client.load_collection(name)
        count = client.query(name, filter="", output_fields=["count(*)"])[0]["count(*)"]
        if count != len(rows):
            raise RuntimeError(f"Expected {len(rows)} rows, found {count}")
        hits = client.search(name, [vectors[-1]], limit=3, filter='category == "nvidia_skills"',
                             output_fields=["category", "source"])
        if len(hits[0]) != 3 or any(hit["entity"]["category"] != "nvidia_skills" for hit in hits[0]):
            raise RuntimeError("Filtered search failed")
        print(f"{name}: {count} chunks from {len(entries)} sources. Filtered top-3 verified.")
    return name


if __name__ == "__main__":
    main()
