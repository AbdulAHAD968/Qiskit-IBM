"""Bundle the result files into web/data/results.js for the project website.

    python -m kinship.export_web

The website is static and opens from the file system, so the data is written as
a script that sets one global instead of a JSON file that would need a server.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
TARGET = ROOT / "web" / "data" / "results.js"


def _load(name: str):
    path = RESULTS / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _round(obj, digits: int = 5):
    if isinstance(obj, float):
        return float(f"{obj:.{digits}g}")
    if isinstance(obj, dict):
        return {k: _round(v, digits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round(v, digits) for v in obj]
    return obj


def other_platform_summary() -> dict | None:
    """How the run kept in results/linux_container differs from the committed one (None if absent)."""
    other_path = RESULTS / "linux_container" / "benchmark.json"
    mine = _load("benchmark")
    if mine is None or not other_path.exists():
        return None
    other = json.loads(other_path.read_text(encoding="utf-8"))

    def runs(bench):
        return {(inst["name"], r["method"], r["p"]): r for inst in bench["instances"] for r in inst["qaoa"]}

    a, b = runs(mine), runs(other)
    keys = [key for key in a if key[1] == "constrained" and key in b]
    differ = [key for key in keys if abs(a[key]["expectation"] - b[key]["expectation"]) > 1e-6 * abs(a[key]["expectation"])]
    depth = max(mine["config"]["depths"])
    out = {"name": "Linux container", "runs": len(keys), "runs_differ": len(differ),
           "depths_differ": sorted({key[2] for key in differ}), "depth": depth}
    for size in ("S", "M"):
        row = next((r for r in other["summary"] if r["size"] == size and r["method"] == "constrained" and r["p"] == depth), None)
        if row:
            out[size] = {"quality": row["quality"]["mean"], "p_opt": row["p_opt"]["mean"],
                         "gain_mean": row["p_opt_gain"]["mean"], "gain_median": row["p_opt_gain"]["median"],
                         "gain_max": row["p_opt_gain"]["max"]}
    return out


def build() -> dict:
    data: dict = {"meta": _load("meta") or {}}
    genetics = _load("genetics")
    if genetics:
        data["genetics"] = genetics
    mc = _load("genetics_montecarlo")
    if mc:
        data["genetics_mc"] = {k: v for k, v in mc.items() if k != "cases"}
        data["genetics_mc"]["families"] = len(mc["cases"])
    gate1 = _load("gate1")
    if gate1:
        keep = ("size", "index", "edges", "largest_component", "field_ratio", "relevance_ratio",
                "greedy_ratio", "annealing_ratio", "random_ratio")
        data["gate1"] = {"n_instances": gate1["n_instances"], "summary": gate1["summary"],
                         "rows": [{k: r[k] for k in keep} for r in gate1["rows"]]}
    bench = _load("benchmark")
    if bench:
        table: dict = {}
        for r in bench["summary"]:
            slot = table.setdefault(r["size"], {}).setdefault(r["method"], {})
            slot[str(r["p"] or 0)] = {k: v for k, v in r.items() if k not in ("size", "method", "p")}
        data["bench"] = table
        data["bench_config"] = bench["config"]
        data["bench_rows"] = bench["summary"]
    circuits = _load("circuits")
    if circuits:
        table = {}
        for r in circuits["rows"]:
            topo = "line" if r["topology"] == "line" else "all"
            table.setdefault(r["size"], {}).setdefault(topo, {}).setdefault(r["method"], {})[str(r["p"])] = {
                "depth": r["depth"], "two_qubit": r["two_qubit"], "n": r["n"], "k": r["k"]}
        data["circ"] = table
    noise = _load("noise")
    if noise:
        table = {}
        for r in noise["summary"]:
            table.setdefault(r["method"], {}).setdefault(str(r["p"]), []).append(
                {"e2": r["e2"], "valid_share": r["valid_share"]["mean"], "quality": r["quality"]["mean"],
                 "p_opt": r["p_opt"]["mean"], "two_qubit": r["two_qubit"]["mean"],
                 "random_quality": r["random_quality"]["mean"], "random_p_opt": r["random_p_opt"]["mean"]})
        data["noise"] = {"levels": noise["levels"], "instances": noise["instances"], "shots": noise["shots"],
                         "model": noise["model"], "series": table}
    ablation = _load("ablation")
    if ablation:
        data["ablation"] = {"instances": ablation["instances"], "summary": ablation["summary"]}
    tradeoff = _load("tradeoff")
    if tradeoff:
        data["tradeoff"] = tradeoff
    decomposition = _load("decomposition")
    if decomposition:
        data["decomposition"] = {k: v for k, v in decomposition.items() if k != "cells"}
    other = other_platform_summary()
    if other:
        data["other_platform"] = other
    data = _round(data)
    demo = _load("demo")
    if demo:
        data["demo"] = demo      # not rounded: the in-browser simulator must see the weights and angles Qiskit used
    return data


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(build(), separators=(",", ":"))
    TARGET.write_text("/* Generated by `python -m kinship.export_web`. Do not edit by hand. */\n"
                      f"window.KINSHIP = {payload};\n", encoding="utf-8")
    print("wrote", TARGET.relative_to(ROOT), f"({len(payload) / 1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
