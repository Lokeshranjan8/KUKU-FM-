"""Checks whether retrieval finds the right law for realistic stories.

Run from the project root:  python -m eval.run_retrieval_eval
No API key needed - this only tests the retrieval step.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.rag import get_index

K = 6
cases = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))
index = get_index()

hit, full, total_expected, found_expected, rows = 0, 0, 0, 0, []
labelled = [c for c in cases if c["expected"]]
for case in cases:
    got = [r["id"] for r in index.search(case["story"], k=K)]
    expected = set(case["expected"])
    found = expected & set(got)
    if not expected:
        rows.append(("CIVIL", case["story"], got[:3], []))
        continue
    total_expected += len(expected)
    found_expected += len(found)
    hit += bool(found)
    full += found == expected
    status = "OK" if found == expected else ("PART" if found else "MISS")
    rows.append((status, case["story"], got[:3], sorted(expected - found)))

for status, story, top, missing in rows:
    print(f"[{status:5}] {story[:70]}")
    print(f"        top3={top}" + (f"  missing={missing}" if missing else ""))

n = len(labelled)
print()
print(f"Cases with expected laws: {n}")
print(f"Hit@{K} (at least one right law found): {hit}/{n} = {hit / n:.0%}")
print(f"All expected laws found:              {full}/{n} = {full / n:.0%}")
print(f"Recall@{K} over all expected laws:     {found_expected}/{total_expected} = {found_expected / total_expected:.0%}")
