"""Compare the result files of two runs, ignoring timing fields.

    python -m kinship.compare_runs path/to/other/results

Used to confirm that a second full run, for example in a fresh clone,
reproduces the committed results. Exits with status 1 if any value differs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {"seconds", "generated", "platform", "workers"}      # wall-clock and machine fields


def differences(a, b, path: str = "") -> list[tuple]:
    out: list[tuple] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key in IGNORED:
                continue
            if key not in a or key not in b:
                out.append((f"{path}/{key}", "present in one run only", None))
            else:
                out += differences(a[key], b[key], f"{path}/{key}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, f"length {len(a)} against {len(b)}", None))
        for i, (x, y) in enumerate(zip(a, b)):
            out += differences(x, y, f"{path}[{i}]")
    elif isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        if a != b:
            out.append((path, a, b))
    elif abs(a - b) > 1e-9 * max(1.0, abs(a), abs(b)):
        out.append((path, a, b))
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    other = Path(argv[0])
    total = files = 0
    for mine in sorted((ROOT / "results").glob("*.json")):
        theirs = other / mine.name
        if not theirs.exists():
            print(f"{mine.name}: missing in {other}")
            total += 1
            continue
        diff = differences(json.loads(mine.read_text(encoding="utf-8")), json.loads(theirs.read_text(encoding="utf-8")))
        files += 1
        total += len(diff)
        print(f"{mine.name}: {len(diff)} differing values")
        for item in diff[:5]:
            print("    ", str(item)[:200])
    print(f"{files} files compared, {total} differing values in total (timing fields ignored)")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
