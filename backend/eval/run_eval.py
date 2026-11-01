"""Measure how good retrieval (and optionally answers) are on your own question set.

Usage (the API must be running):
    python eval/run_eval.py --pdf sample.pdf --questions eval/questions.json
    python eval/run_eval.py --pdf sample.pdf --questions eval/questions.json --answers

Metrics, per search mode:
    hit@k  share of questions where a retrieved passage covers an expected page
    MRR    average of 1 / (rank of the first correct passage); 1.0 is perfect
With --answers it also reports how often the answer contains all expected keywords.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

MODES = ("vector", "keyword", "hybrid")


def upload_and_wait(client: httpx.Client, pdf: Path, timeout_s: int = 600) -> str:
    response = client.post(
        "/documents", files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")}
    )
    response.raise_for_status()
    doc_id = response.json()["id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        info = client.get(f"/documents/{doc_id}").json()
        if info["status"] == "ready":
            return doc_id
        if info["status"] == "failed":
            sys.exit(f"Indexing failed: {info['error']}")
        time.sleep(1.5)
    sys.exit("Timed out waiting for the document to be indexed.")


def covers(source: dict, expected_pages: list[int]) -> bool:
    pages = range(source["page_start"], source["page_end"] + 1)
    return any(page in pages for page in expected_pages)


def retrieval_metrics(client, doc_id, questions, mode) -> dict:
    hits, reciprocal_ranks = 0, []
    for item in questions:
        response = client.post(
            "/search", json={"document_id": doc_id, "question": item["question"], "mode": mode}
        )
        response.raise_for_status()
        rank = next(
            (i for i, s in enumerate(response.json(), 1) if covers(s, item["expected_pages"])),
            None,
        )
        hits += rank is not None
        reciprocal_ranks.append(1 / rank if rank else 0.0)
    total = len(questions)
    return {"hit_at_k": hits / total, "mrr": sum(reciprocal_ranks) / total}


def answer_metrics(client, doc_id, questions) -> dict:
    correct, not_found = 0, 0
    for item in questions:
        response = client.post(
            "/ask", json={"document_id": doc_id, "question": item["question"]}
        )
        response.raise_for_status()
        body = response.json()
        text = body["answer"].lower()
        not_found += not body["sources"]
        keywords = [k.lower() for k in item.get("answer_keywords", [])]
        correct += bool(keywords) and all(k in text for k in keywords)
    total = len(questions)
    return {"answer_accuracy": correct / total, "not_found_rate": not_found / total}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--answers", action="store_true", help="also grade generated answers")
    parser.add_argument("--out", type=Path, default=Path("eval/results.json"))
    args = parser.parse_args()

    questions = json.loads(args.questions.read_text())
    with httpx.Client(base_url=args.api, timeout=300) as client:
        doc_id = upload_and_wait(client, args.pdf)
        results = {mode: retrieval_metrics(client, doc_id, questions, mode) for mode in MODES}
        if args.answers:
            results["answers"] = answer_metrics(client, doc_id, questions)

    print(f"\n{len(questions)} questions on {args.pdf.name}\n")
    print(f"{'mode':<10}{'hit@k':>8}{'MRR':>8}")
    for mode in MODES:
        print(f"{mode:<10}{results[mode]['hit_at_k']:>8.0%}{results[mode]['mrr']:>8.2f}")
    if args.answers:
        print(f"\nanswer accuracy: {results['answers']['answer_accuracy']:.0%}")
        print(f"'not found' rate: {results['answers']['not_found_rate']:.0%}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
