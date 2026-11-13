"""Validate DAY06 gold questions and run Milvus retrieval for A/B/C."""
import argparse
import json
import os
from collections import Counter
from contextlib import closing
from pathlib import Path

from pymilvus import MilvusClient

from starter.src.ingest_vla import embed, main as ingest, normalize


def load_questions(path):
    manifest = json.loads(Path("data/manifest.json").read_text(encoding="utf-8"))
    sources = {entry["source_id"]: entry for entry in manifest["sources"]}
    categories = {entry["category"] for entry in sources.values()}
    questions = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(questions, list):
        raise ValueError("Questions must be a JSON array.")
    ids = set()
    for index, row in enumerate(questions, 1):
        for field in ("id", "question", "expected_answer", "gold_source_id", "evidence_quote"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Question {index}: fill in {field}.")
        if row["id"] in ids or row.get("split") not in ("dev", "test"):
            raise ValueError(f"Question {index}: use a unique ID and split dev or test.")
        ids.add(row["id"])
        entry = sources.get(row["gold_source_id"])
        if not entry or type(row.get("gold_page")) is not int or row["gold_page"] != 1:
            raise ValueError(f"Question {index}: use a source_id from the manifest and logical page 1.")
        evidence = normalize(row["evidence_quote"])
        if not evidence or evidence not in normalize(Path(entry["local_path"]).read_text(encoding="utf-8-sig")):
            raise ValueError(f"Question {index}: evidence was not found in the source.")
        scope = row.get("filter")
        if scope is not None and (not isinstance(scope, dict) or set(scope) != {"category"}
                                  or not isinstance(scope["category"], str)
                                  or scope["category"] not in categories):
            raise ValueError(f"Question {index}: filter must be null or a valid category object.")
        if scope and scope["category"] != entry["category"]:
            raise ValueError(f"Question {index}: the gold source is outside the filter.")
    splits = Counter(row["split"] for row in questions)
    filtered = Counter(row["split"] for row in questions if row.get("filter"))
    if splits["dev"] < 15 or splits["test"] < 5 or filtered.total() < 3 or not filtered["test"]:
        raise ValueError("Need at least 15 dev, 5 test and 3 filtered questions, including 1 filtered test.")
    return questions


def evaluate(client, questions, vectors, collections):
    traces = []
    for strategy, collection in collections.items():
        for row, vector in zip(questions, vectors):
            scope = row.get("filter") if strategy == "C" else None
            expression = f'category == {json.dumps(scope["category"])}' if scope else ""
            hits = client.search(collection, [vector], limit=3, filter=expression,
                                 output_fields=["document_id", "source", "page", "category", "offset", "text"])[0]
            top3 = []
            for hit in hits:
                chunk = hit["entity"]
                match = (chunk["document_id"] == row["gold_source_id"]
                         and chunk["page"] == row["gold_page"]
                         and normalize(row["evidence_quote"]) in normalize(chunk["text"]))
                top3.append(dict(chunk, id=hit["id"], score=hit["distance"], evidence_hit=match))
            traces.append(dict(row, strategy=strategy, applied_filter=scope, top3=top3,
                               hit_at_1=bool(top3 and top3[0]["evidence_hit"]),
                               evidence_hit_at_3=any(chunk["evidence_hit"] for chunk in top3)))
    return traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=Path("benchmark/questions.json"))
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    try:
        questions = load_questions(args.questions)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Validated {len(questions)} questions.")
    if args.validate:
        return

    fixed, headings = ingest("fixed"), ingest("headings")
    ollama = os.getenv("OLLAMA_URL", "http://192.168.1.246:11434").rstrip("/")
    milvus = os.getenv("MILVUS_URI", "http://192.168.1.246:19530")
    vectors = []
    for start in range(0, len(questions), 32):
        batch = questions[start:start + 32]
        vectors.extend(embed(ollama, ["Instruct: Given a question, retrieve a passage that answers it.\nQuery: "
                                      + row["question"] for row in batch]))
    with closing(MilvusClient(milvus, timeout=60)) as client:
        traces = evaluate(client, questions, vectors, {"A": fixed, "B": headings, "C": headings})
    metrics = []
    for strategy in "ABC":
        for split in ("dev", "test"):
            group = [trace for trace in traces if trace["strategy"] == strategy and trace["split"] == split]
            metrics.append(dict(strategy=strategy, split=split, total=len(group),
                                hit_at_1=sum(trace["hit_at_1"] for trace in group),
                                evidence_hit_at_3=sum(trace["evidence_hit_at_3"] for trace in group)))
    output = Path("results")
    output.mkdir(exist_ok=True)
    for filename, data in (("traces.json", traces), ("metrics.json", metrics)):
        (output / filename).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Saved results/traces.json and results/metrics.json.")


if __name__ == "__main__":
    main()
