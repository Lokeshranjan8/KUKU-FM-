"""Runs NyayaSaathi on my own test inputs and saves the outputs exactly as produced.

Usage (from the project root, with .env filled in):
    python -m scripts.generate_raw_outputs

Writes to raw_outputs/:
    cases/NN_<name>.json  one file per input: the input, laws retrieved, the model's raw
                          reply (before my grounding check) and the final answer the app shows
    summary.md            one-line-per-case table generated from those files
    retrieval_eval.txt    output of the retrieval eval
    unit_tests.txt        output of the unit tests
Nothing in these files is edited by hand.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "raw_outputs"


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env()

from fastapi import HTTPException  # noqa: E402

from backend import service  # noqa: E402
from backend.rag import retrieve  # noqa: E402

# Follow-up conversations, to show the clarifying-question flow and that later
# answers are used for retrieval. The assistant turn is filled in at run time.
FOLLOW_UPS = [
    {
        "name": "followup_vague_story",
        "location": "Karnataka",
        "turns": [
            "Some guy took my stuff and won't give it back.",
            "It was my laptop. I lent it to my roommate for a week, now he says it's his and stopped answering my calls.",
        ],
    },
    {
        "name": "followup_police_refused",
        "location": "Uttar Pradesh",
        "turns": [
            "My neighbour beat my father with a stick yesterday, he has stitches on his head.",
            "We went to the police station but they refused to write an FIR and said settle it between yourselves.",
        ],
    },
]


def slug(text: str, n: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:n]


def run_conversation(user_turns: list[str], location: str) -> dict:
    """Same code path as POST /api/analyze, plus capture of the model's raw reply."""
    captured: dict = {}
    real_post = service.requests.post

    def capturing_post(*args, **kwargs):
        response = real_post(*args, **kwargs)
        try:
            captured["raw"] = response.json()["choices"][0]["message"]["content"]
        except Exception:  # keep whatever came back, even if it's malformed
            captured["raw"] = response.text
        return response

    messages: list[dict] = []
    turns_out = []
    service.requests.post = capturing_post
    try:
        for text in user_turns:
            messages.append({"role": "user", "content": text})
            query = " ".join(m["content"] for m in messages if m["role"] == "user")
            retrieved = [{"id": r["id"], "score": r["score"]} for r in retrieve(query)]
            captured.clear()
            record = {"user_message": text, "retrieved": retrieved}
            try:
                result = service.analyze_case(messages, location)
                record["final_output"] = result.model_dump()
                messages.append({"role": "assistant", "content": result.response})
            except HTTPException as error:
                record["error"] = {"status": error.status_code, "detail": error.detail}
            raw = captured.get("raw")
            try:
                record["model_raw_reply"] = json.loads(raw) if raw else None
            except (TypeError, json.JSONDecodeError):
                record["model_raw_reply"] = raw
            turns_out.append(record)
            if "error" in record:
                break
    finally:
        service.requests.post = real_post
    return {"location": location, "turns": turns_out}


def run_command(args: list[str]) -> str:
    done = subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True
    )
    return f"$ python {' '.join(args)}\n\n{done.stdout}{done.stderr}"


def main() -> None:
    if not os.getenv("AI_API_KEY"):
        sys.exit("AI_API_KEY is not set. Fill in .env first (cp .env.example .env).")

    (OUT / "cases").mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))
    rows = []

    jobs = [
        (f"{i:02d}_{slug(c['story'])}", [c["story"]], "", c["expected"])
        for i, c in enumerate(cases, start=1)
    ]
    jobs += [
        (f"{len(cases) + i:02d}_{f['name']}", f["turns"], f["location"], None)
        for i, f in enumerate(FOLLOW_UPS, start=1)
    ]

    for name, turns, location, expected in jobs:
        print(f"running {name} ...", flush=True)
        result = run_conversation(turns, location)
        result["expected_laws"] = expected
        (OUT / "cases" / f"{name}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        last = result["turns"][-1]
        final = last.get("final_output") or {}
        cited = [law["ref_id"] for law in final.get("possible_laws", [])]
        rows.append((name, len(result["turns"]), final.get("issue_type", "ERROR"),
                     cited, final.get("dropped_citations", "-"), expected))

    lines = [
        "# Raw outputs summary",
        "",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} with model `{os.getenv('AI_MODEL')}`.",
        "Auto-generated from the files in `cases/`. Not edited by hand.",
        "",
        "| Case | Turns | Issue type (from model) | Laws cited (final) | Dropped | Expected (eval) |",
        "|---|---|---|---|---|---|",
    ]
    for name, n, issue, cited, dropped, expected in rows:
        exp = "n/a (follow-up)" if expected is None else (", ".join(expected) or "none (civil)")
        lines.append(f"| {name} | {n} | {issue} | {', '.join(cited) or '-'} | {dropped} | {exp} |")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (OUT / "retrieval_eval.txt").write_text(run_command(["-m", "eval.run_retrieval_eval"]))
    (OUT / "unit_tests.txt").write_text(
        run_command(["-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"])
    )
    print(f"done -> {OUT}")


if __name__ == "__main__":
    main()
