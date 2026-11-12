"""Experiment runner. Every number in the report and on the website comes from here.

    python -m kinship.evaluate all            full matrix (about 10 minutes on 12 cores)
    python -m kinship.evaluate all --quick    reduced matrix for a fast check (about 2 minutes)
    python -m kinship.evaluate benchmark      one experiment only

Raw outputs are written to results/*.json. Seeds are fixed, so a rerun on the
same package versions reproduces the files.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import CARRIER_RATE, DEFAULT_LAMBDA, __version__
from .classical import (
    feasible_table, field_rule, greedy, milp_exact, relevance_rule, simulated_annealing, tie_break_range,
)
from .decompose import couple_components, largest_component, pool_values, split_budget
from .genetics import PedigreeModel, allele_frequency
from .pedigree import Family, Person
from .problem import SIZES, ScreeningProblem, make_instance
from .view import family_view

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
INSTANCES = ROOT / "data" / "instances"

NOISE_LEVELS = [0.0, 0.0005, 0.001, 0.002, 0.005, 0.01]
LAMBDAS = [0.0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _jsonable(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not serialisable: {type(o)}")


def save(name: str, obj) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(obj, indent=1, default=_jsonable), encoding="utf-8")
    return path


def load(name: str):
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def mask_of(x) -> int:
    return int(sum(1 << int(i) for i in np.flatnonzero(x)))


def _stats(values) -> dict:
    v = np.array([u for u in values if u is not None], dtype=float)
    if v.size == 0:
        return {"mean": None, "std": None, "median": None, "min": None, "max": None, "n": 0}
    return {"mean": float(v.mean()), "std": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "median": float(np.median(v)), "min": float(v.min()), "max": float(v.max()), "n": int(v.size)}


def _map(fn, tasks, workers: int) -> list:
    """Run tasks in worker processes; fall back to fewer workers if a pool breaks."""
    tasks = list(tasks)
    for w in (workers, max(2, workers // 2), 1):
        if w <= 1:
            return [fn(t) for t in tasks]
        try:
            with ProcessPoolExecutor(max_workers=w) as ex:
                return list(ex.map(fn, tasks))
        except BrokenProcessPool:
            print(f"worker pool broke with {w} workers, retrying with fewer", flush=True)
    return [fn(t) for t in tasks]


# --------------------------------------------------------------------------
# 1. genetics engine: textbook values and calibration
# --------------------------------------------------------------------------
def _mini(rows, probands) -> Family:
    people = [Person(i, lab, "x", "M", 0, fa, mo, affected=aff) for i, (lab, fa, mo, aff) in enumerate(rows)]
    return Family(people, [], probands, seed=0)


def _calibration_task(args):
    size, idx = args
    prob = make_instance(size, idx)
    fam = prob.family
    model = PedigreeModel(fam, CARRIER_RATE)
    living = [p.id for p in fam.people if p.alive and not p.affected]
    w_all, w_excl = [], []
    for c in fam.couples:
        if c.kind != "married" or not (fam.people[c.a].alive and fam.people[c.b].alive):
            continue
        w = model.both_carriers(c.a, c.b)
        w_all.append(w)
        if fam.people[c.a].role not in ("father", "mother"):
            w_excl.append(w)
    return {"share_all": float(np.mean([model.carrier_prob(i) for i in living])),
            "share_cand": float(prob.p.mean()), "people": len(fam.people), "w_all": w_all, "w_excl": w_excl}


def exp_genetics(n_cal: int = 60, workers: int = 8, **_) -> dict:
    q = allele_frequency(CARRIER_RATE)
    nuclear = _mini([("father", None, None, False), ("mother", None, None, False),
                     ("index", 0, 1, True), ("sibling", 0, 1, False)], [2])
    grand = _mini([("gf", None, None, False), ("gm", None, None, False), ("father", 0, 1, False),
                   ("mother", None, None, False), ("index", 2, 3, True)], [4])
    uncle = _mini([("gf", None, None, False), ("gm", None, None, False), ("father", 0, 1, False),
                   ("uncle", 0, 1, False), ("mother", None, None, False), ("index", 2, 4, True)], [5])
    three = _mini([("gf", None, None, False), ("gm", None, None, False), ("father", 0, 1, False),
                   ("uncle", 0, 1, False), ("mother", None, None, False), ("index", 2, 4, True),
                   ("wife", None, None, False), ("cousin", 3, 6, False)], [5])
    control = _mini([("a", None, None, False), ("b", None, None, False), ("c", 0, 1, False)], [])
    m_n, m_g, m_u, m_t, m_c = (PedigreeModel(f, CARRIER_RATE) for f in (nuclear, grand, uncle, three, control))
    checks = [
        {"relation": "Parent of the affected child", "textbook": "1", "expected": 1.0,
         "computed": m_n.carrier_prob(0)},
        {"relation": "Unaffected sibling", "textbook": "2/3", "expected": 2 / 3,
         "computed": m_n.carrier_prob(3)},
        {"relation": "Grandparent", "textbook": "about 1/2", "expected": (1 + q) / 2,
         "computed": m_g.carrier_prob(0), "formula": "(1 + q) / 2"},
        {"relation": "Aunt or uncle", "textbook": "about 1/2", "expected": 2 / (4 - q),
         "computed": m_u.carrier_prob(3), "formula": "2 / (4 - q)"},
        {"relation": "First cousin", "textbook": "about 1/4", "expected": None,
         "computed": m_t.carrier_prob(7)},
        {"relation": "Married-in spouse", "textbook": "population rate", "expected": None,
         "computed": m_t.carrier_prob(6)},
        {"relation": "Member of a family with no affected child", "textbook": "population rate",
         "expected": None, "computed": m_c.carrier_prob(2)},
        {"relation": "Both grandparents carriers (joint)", "textbook": "not a product", "expected": q,
         "computed": m_g.both_carriers(0, 1), "formula": "q",
         "note": "product of the two single probabilities would be %.3f" % (m_g.carrier_prob(0) ** 2)},
    ]

    cal = _map(_calibration_task, [(size, idx) for size in ("S", "M") for idx in range(n_cal)], workers)
    share_all = [c["share_all"] for c in cal]
    share_cand = [c["share_cand"] for c in cal]
    sizes = [c["people"] for c in cal]
    w_all = [w for c in cal for w in c["w_all"]]
    w_excl = [w for c in cal for w in c["w_excl"]]
    calibration = {
        "families": 2 * n_cal,
        "mean_people_per_family": float(np.mean(sizes)),
        "carrier_share_living_relatives": float(np.mean(share_all)),
        "carrier_share_candidates": float(np.mean(share_cand)),
        "couples_both_carriers_all_married": float(np.mean(w_all)),
        "couples_both_carriers_excluding_index_parents": float(np.mean(w_excl)),
        "married_couples": len(w_all),
        "target_carrier_share": 183 / 591,
        "target_couples_both_carriers": 17 / 214,
        "source": "Ahmed et al., N Engl J Med 2002;347:1162-8",
    }
    out = {"carrier_rate": CARRIER_RATE, "allele_frequency": q, "checks": checks, "calibration": calibration}
    save("genetics", out)
    return out


# --------------------------------------------------------------------------
# 2. Gate 1: is the problem non-trivial?
# --------------------------------------------------------------------------
def _classical(prob: ScreeningProblem, table, seed: int) -> dict:
    from .quantum.qaoa import shots_needed

    rng = np.random.default_rng(10_000 + seed)
    out = {}
    for name, x in (("field", field_rule(prob)), ("relevance", relevance_rule(prob)),
                    ("greedy", greedy(prob)), ("annealing", simulated_annealing(prob, rng))):
        v = prob.value(x)
        out[name] = {"value": v, "ratio": v / table.best, "quality": table.quality(v), "mask": mask_of(x),
                     "optimal": bool(v >= table.best - 1e-12)}
    p_opt = len(table.optimal_masks()) / len(table.masks)
    out["random"] = {"value": table.mean, "ratio": table.mean / table.best, "quality": table.quality(table.mean),
                     "p_opt": p_opt, "shots_95": shots_needed(p_opt)}
    return out


def _gate1_task(args):
    size, idx = args
    prob = make_instance(size, idx)
    table = feasible_table(prob)
    cl = _classical(prob, table, idx)
    best_x = prob.mask_to_x(table.best_mask)
    tie_best, tie_worst, tie = tie_break_range(prob, prob.p)
    return {"size": size, "index": idx, "edges": len(prob.edges), "best": table.best,
            "largest_component": largest_component(prob),
            "couple_share_of_optimum": prob.couples_found(best_x) / table.best,
            "field_tie": bool(tie), "field_best_tie_ratio": tie_best / table.best,
            "field_worst_tie_ratio": tie_worst / table.best,
            **{f"{k}_ratio": v["ratio"] for k, v in cl.items()},
            **{f"{k}_optimal": v.get("optimal") for k, v in cl.items() if "optimal" in v}}


def exp_gate1(n_instances: int = 50, workers: int = 8, **_) -> dict:
    tasks = [(s, i) for s in ("S", "M") for i in range(n_instances)]
    rows = _map(_gate1_task, tasks, workers)
    out = {"n_instances": n_instances, "rows": rows, "summary": {}}
    for size in ("S", "M"):
        sub = [r for r in rows if r["size"] == size]
        summ = {"n": SIZES[size]["n"], "k": SIZES[size]["k"], "edges": _stats([r["edges"] for r in sub]),
                "largest_component": _stats([r["largest_component"] for r in sub]),
                "couple_share_of_optimum": _stats([r["couple_share_of_optimum"] for r in sub])}
        for name in ("field", "relevance", "greedy", "annealing", "random"):
            ratios = [r[f"{name}_ratio"] for r in sub]
            summ[name] = {"ratio": _stats(ratios)}
            if name != "random":
                summ[name]["miss_rate"] = float(np.mean([not r[f"{name}_optimal"] for r in sub]))
                summ[name]["mean_gap"] = float(1 - np.mean(ratios))
        # The field rule breaks ties in carrier probability by index. Bracket that choice.
        summ["field"]["tie_break"] = {
            "families_with_tie": int(sum(r["field_tie"] for r in sub)),
            "best_ratio": _stats([r["field_best_tie_ratio"] for r in sub]),
            "worst_ratio": _stats([r["field_worst_tie_ratio"] for r in sub]),
            "best_miss_rate": float(np.mean([r["field_best_tie_ratio"] < 1 - 1e-9 for r in sub])),
        }
        out["summary"][size] = summ
    save("gate1", out)
    return out


# --------------------------------------------------------------------------
# 3. Main benchmark: QAOA against exact answers and classical rules
# --------------------------------------------------------------------------
def _bench_task(args):
    from .quantum.qaoa import run_depth_ladder

    size, idx, depths, shots, maxiter = args
    t0 = time.perf_counter()
    prob = make_instance(size, idx)
    table = feasible_table(prob)
    row = {"size": size, "index": idx, "name": prob.name, "n": prob.n, "k": prob.k,
           "edges": len(prob.edges), "n_feasible": int(len(table.masks)),
           "n_optimal": int(len(table.optimal_masks())), "best": table.best, "worst": table.worst,
           "mean": table.mean, "best_mask": table.best_mask, "classical": _classical(prob, table, idx),
           "qaoa": []}
    for method in ("constrained", "penalty"):
        row["qaoa"] += run_depth_ladder(prob, table, method, depths, shots, seed=idx, maxiter=maxiter)
    row["seconds"] = round(time.perf_counter() - t0, 2)
    return row


def summarise_benchmark(instances: list[dict]) -> list[dict]:
    rows = []
    for size in sorted({r["size"] for r in instances}):
        sub = [r for r in instances if r["size"] == size]
        base = {"size": size, "n": sub[0]["n"], "k": sub[0]["k"], "instances": len(sub)}
        rand = [r["classical"]["random"] for r in sub]
        rows.append({**base, "method": "random", "p": None, "kind": "classical",
                     "quality": _stats([c["quality"] for c in rand]), "ratio": _stats([c["ratio"] for c in rand]),
                     "p_opt": _stats([c["p_opt"] for c in rand]), "valid_share": _stats([1.0] * len(sub)),
                     "shots_95": _stats([c["shots_95"] for c in rand])})
        for name in ("field", "relevance", "greedy", "annealing"):
            cl = [r["classical"][name] for r in sub]
            rows.append({**base, "method": name, "p": None, "kind": "classical",
                         "quality": _stats([c["quality"] for c in cl]), "ratio": _stats([c["ratio"] for c in cl]),
                         "optimal_share": float(np.mean([c["optimal"] for c in cl]))})
        for method in ("constrained", "penalty"):
            for p in sorted({q["p"] for r in sub for q in r["qaoa"]}):
                runs = [q for r in sub for q in r["qaoa"] if q["method"] == method and q["p"] == p]
                gains = [q["p_opt"] / r["classical"]["random"]["p_opt"]
                         for r in sub for q in r["qaoa"] if q["method"] == method and q["p"] == p]
                rows.append({**base, "method": method, "p": p, "kind": "quantum",
                             "quality": _stats([q["quality"] for q in runs]),
                             "ratio": _stats([q["ratio"] for q in runs]),
                             "p_opt": _stats([q["p_opt"] for q in runs]),
                             "p_near": _stats([q["p_near"] for q in runs]),
                             "valid_share": _stats([q["valid_share"] for q in runs]),
                             "shots_95": _stats([q["shots_95"] for q in runs]),
                             "p_opt_gain": _stats(gains),
                             "best_sample_optimal_share": float(np.mean(
                                 [(q["sampled_best_ratio"] or 0) >= 1 - 1e-9 for q in runs])),
                             "evaluations": _stats([q["evaluations"] for q in runs])})
    return rows


def exp_benchmark(n_s: int = 20, n_m: int = 12, depths=(1, 2, 3), shots: int = 4096,
                  maxiter: int = 150, workers: int = 8, **_) -> dict:
    INSTANCES.mkdir(parents=True, exist_ok=True)
    for size, count in (("S", n_s), ("M", n_m)):
        for idx in range(count):
            make_instance(size, idx).save(INSTANCES / f"{size}-{idx:02d}.json")
    tasks = [("M", i, tuple(depths), shots, maxiter) for i in range(n_m)]
    tasks += [("S", i, tuple(depths), shots, maxiter) for i in range(n_s)]
    t0 = time.perf_counter()
    instances = _map(_bench_task, tasks, workers)
    instances.sort(key=lambda r: (r["size"], r["index"]))
    out = {"config": {"n_s": n_s, "n_m": n_m, "depths": list(depths), "shots": shots, "maxiter": maxiter,
                      "lambda": DEFAULT_LAMBDA, "optimizer": "COBYLA", "sizes": SIZES},
           "seconds": round(time.perf_counter() - t0, 1),
           "summary": summarise_benchmark(instances), "instances": instances}
    save("benchmark", out)
    return out


# --------------------------------------------------------------------------
# 4. Circuit resources
# --------------------------------------------------------------------------
def _circuit_task(args):
    from .quantum.circuits import dicke_state
    from .quantum.noise import resources
    from .quantum.qaoa import QAOA

    size, method, p, line = args
    prob = make_instance(size, 0)
    if method == "dicke_only":
        logical = dicke_state(prob.n, prob.k)
    else:
        engine = QAOA(prob, method, reps=p)
        logical = engine.bound_logical(np.full(2 * p, 0.37))
    res = resources(logical, line=line)
    return {"size": size, "n": prob.n, "k": prob.k, "edges": len(prob.edges), "method": method, "p": p,
            "topology": "line" if line else "all-to-all", **res}


def exp_circuits(depths=(1, 2, 3), workers: int = 8, sizes=("S", "M"), **_) -> dict:
    tasks = []
    for size in sizes:
        for line in (False, True):
            tasks.append((size, "dicke_only", 0, line))
            for method in ("constrained", "penalty"):
                tasks += [(size, method, p, line) for p in depths]
    rows = _map(_circuit_task, tasks, workers)
    out = {"basis": ["rz", "sx", "x", "cz"], "optimization_level": 3, "rows": rows}
    save("circuits", out)
    return out


# --------------------------------------------------------------------------
# 5. Start-state ablation (something that did not work)
# --------------------------------------------------------------------------
def _ablation_task(args):
    from .quantum.qaoa import run_depth_ladder

    idx, initial, depths = args
    prob = make_instance("S", idx)
    table = feasible_table(prob)
    rows = run_depth_ladder(prob, table, "constrained", depths, shots=1024, seed=idx, initial=initial)
    field_quality = table.quality(prob.value(field_rule(prob)))
    return [{"index": idx, "initial": initial, "p": r["p"], "quality": r["quality"], "p_opt": r["p_opt"],
             "field_quality": field_quality, "random_quality": table.quality(table.mean)} for r in rows]


def exp_ablation(n: int = 8, depths=(1, 2, 3), workers: int = 8, **_) -> dict:
    tasks = [(i, init, tuple(depths)) for i in range(n) for init in ("dicke", "field")]
    rows = [r for chunk in _map(_ablation_task, tasks, workers) for r in chunk]
    summary = []
    for init in ("dicke", "field"):
        for p in depths:
            sub = [r for r in rows if r["initial"] == init and r["p"] == p]
            summary.append({"initial": init, "p": p, "quality": _stats([r["quality"] for r in sub]),
                            "p_opt": _stats([r["p_opt"] for r in sub]),
                            "field_quality": _stats([r["field_quality"] for r in sub]),
                            "random_quality": _stats([r["random_quality"] for r in sub])})
    out = {"instances": n, "summary": summary, "rows": rows}
    save("ablation", out)
    return out


# --------------------------------------------------------------------------
# 6. Noise
# --------------------------------------------------------------------------
def _noise_task(args):
    from .quantum.noise import noisy_counts, resources
    from .quantum.qaoa import QAOA, counts_metrics, run_depth_ladder

    idx, method, p, levels, shots = args
    prob = make_instance("S", idx)
    table = feasible_table(prob)
    ladder = run_depth_ladder(prob, table, method, tuple(range(1, p + 1)), shots=256, seed=idx)
    angles = ladder[-1]["angles"]
    engine = QAOA(prob, method, reps=p)
    logical = engine.bound_logical(angles)
    res = resources(logical)
    rows = []
    for e2 in levels:
        m = counts_metrics(noisy_counts(logical, e2, shots=shots, seed=idx), prob, table)
        rows.append({"index": idx, "method": method, "p": p, "e2": e2, "two_qubit": res["two_qubit"],
                     "depth": res["depth"], "valid_share": m["valid_share"], "quality": m["quality"],
                     "p_opt": m["p_opt"], "best_ratio": m["best_ratio"],
                     "random_quality": table.quality(table.mean),
                     "random_p_opt": len(table.optimal_masks()) / len(table.masks)})
    return rows


def exp_noise(n: int = 6, depths=(1, 2), shots: int = 4096, workers: int = 8, **_) -> dict:
    tasks = [(i, m, p, NOISE_LEVELS, shots) for i in range(n) for m in ("constrained", "penalty") for p in depths]
    rows = [r for chunk in _map(_noise_task, tasks, workers) for r in chunk]
    summary = []
    for method in ("constrained", "penalty"):
        for p in depths:
            for e2 in NOISE_LEVELS:
                sub = [r for r in rows if r["method"] == method and r["p"] == p and r["e2"] == e2]
                summary.append({"method": method, "p": p, "e2": e2,
                                "two_qubit": _stats([r["two_qubit"] for r in sub]),
                                "valid_share": _stats([r["valid_share"] for r in sub]),
                                "quality": _stats([r["quality"] for r in sub]),
                                "p_opt": _stats([r["p_opt"] for r in sub]),
                                "random_quality": _stats([r["random_quality"] for r in sub]),
                                "random_p_opt": _stats([r["random_p_opt"] for r in sub])})
    out = {"instances": n, "size": "S", "shots": shots, "levels": NOISE_LEVELS,
           "model": "depolarising: e2 on CZ, e2/10 on SX and X, readout 2*e2; basis rz, sx, x, cz; all-to-all",
           "summary": summary, "rows": rows}
    save("noise", out)
    return out


# --------------------------------------------------------------------------
# 7. Trade-off curve: couples found against carriers found
# --------------------------------------------------------------------------
def _pareto(points: np.ndarray) -> np.ndarray:
    """Indices of non-dominated points when both columns are maximised."""
    order = np.lexsort((-points[:, 1], -points[:, 0]))
    keep, best_y = [], -np.inf
    for i in order:
        if points[i, 1] > best_y + 1e-12:
            keep.append(i)
            best_y = points[i, 1]
    return np.array(keep, dtype=int)


def _hypervolume(points: np.ndarray) -> float:
    """Area dominated by a set of points, measured from the origin."""
    if len(points) == 0:
        return 0.0
    front = points[_pareto(points)]
    front = front[np.argsort(-front[:, 0])]
    area, prev_y = 0.0, 0.0
    for x, y in front:
        area += x * (y - prev_y)
        prev_y = y
    return float(area)


def _tradeoff_task(args):
    from .quantum.qaoa import QAOA, counts_metrics, run_depth_ladder

    size, idx, lam, p, shots = args
    prob = make_instance(size, idx, lam=lam)
    table = feasible_table(prob)
    ladder = run_depth_ladder(prob, table, "constrained", tuple(range(1, p + 1)), shots=shots, seed=idx)
    last = ladder[-1]
    engine = QAOA(prob, "constrained", reps=p)
    counts = engine.sample(last["angles"], shots=shots, seed=1000 + idx)
    m = counts_metrics(counts, prob, table)
    return {"lam": lam, "masks": sorted(counts), "best_mask": m["best_mask"], "quality": last["quality"],
            "p_opt": last["p_opt"], "best_is_optimal": bool((m["best_ratio"] or 0) >= 1 - 1e-9)}


def _front_size(prob: ScreeningProblem) -> int:
    masks = prob.feasible_masks()
    bits = ((masks[:, None] >> np.arange(prob.n)) & 1).astype(float)
    pts = np.column_stack([0.5 * np.einsum("si,ij,sj->s", bits, prob.W, bits), bits @ (prob.r * prob.p)])
    return len({(round(float(a), 9), round(float(b), 9)) for a, b in pts[_pareto(pts)]})


def exp_tradeoff(size: str = "M", index: int | None = None, p: int = 2, shots: int = 256,
                 workers: int = 8, scan: int = 12, **_) -> dict:
    if index is None:
        # Fixed rule, stated in the report: the instance with the largest exact front.
        index = max(range(scan), key=lambda i: (_front_size(make_instance(size, i)), -i))
    runs = _map(_tradeoff_task, [(size, index, lam, p, shots) for lam in LAMBDAS], workers)
    prob = make_instance(size, index)
    masks = prob.feasible_masks()
    bits = ((masks[:, None] >> np.arange(prob.n)) & 1).astype(float)
    couples = 0.5 * np.einsum("si,ij,sj->s", bits, prob.W, bits)
    carriers = bits @ (prob.r * prob.p)
    pts = np.column_stack([couples, carriers])
    lookup = {int(m): t for t, m in enumerate(masks)}
    front_idx = _pareto(pts)
    front_keys = {(round(float(pts[i, 0]), 9), round(float(pts[i, 1]), 9)) for i in front_idx}
    hv_exact = _hypervolume(pts)

    def recovered(index_set) -> int:
        keys = {(round(float(pts[i, 0]), 9), round(float(pts[i, 1]), 9)) for i in index_set}
        return len(keys & front_keys)

    sampled = sorted({lookup[m] for r in runs for m in r["masks"] if m in lookup})
    total_shots = shots * len(LAMBDAS)
    rng = np.random.default_rng(7)
    rand_hv, rand_found = [], []
    for _ in range(200):
        pick = rng.integers(0, len(masks), size=total_shots)
        rand_hv.append(_hypervolume(pts[pick]) / hv_exact)
        rand_found.append(recovered(set(pick.tolist())))
    cloud = rng.choice(len(masks), size=min(700, len(masks)), replace=False)
    q_front = [sampled[i] for i in _pareto(pts[sampled])]

    def point(i):
        return {"couples": float(pts[i, 0]), "carriers": float(pts[i, 1]), "mask": int(masks[i])}

    def plan_point(x):
        return {"couples": prob.couples_found(x), "carriers": prob.carriers_found(x)}

    out = {
        "instance": prob.name, "n": prob.n, "k": prob.k, "p": p, "shots_per_lambda": shots,
        "selection": f"size {size} instance with the largest exact trade-off front among the first {scan}",
        "lambdas": LAMBDAS, "total_shots": total_shots, "n_feasible": int(len(masks)),
        "front": [point(i) for i in sorted(front_idx, key=lambda i: pts[i, 0])],
        "cloud": [point(i) for i in cloud],
        "qaoa_front": [point(i) for i in sorted(q_front, key=lambda i: pts[i, 0])],
        "per_lambda": [{"lam": r["lam"], "quality": r["quality"], "p_opt": r["p_opt"],
                        "best_is_optimal": r["best_is_optimal"], **point(lookup[r["best_mask"]])} for r in runs],
        "field": plan_point(field_rule(prob)), "relevance": plan_point(relevance_rule(prob)),
        "hypervolume": {"exact": hv_exact, "qaoa_ratio": _hypervolume(pts[sampled]) / hv_exact,
                        "random_ratio_mean": float(np.mean(rand_hv)), "random_ratio_std": float(np.std(rand_hv))},
        "front_points": {"exact": len(front_keys), "qaoa_found": recovered(sampled),
                         "random_found_mean": float(np.mean(rand_found))},
        "distinct_plans_sampled": len(sampled),
    }
    save("tradeoff", out)
    return out


# --------------------------------------------------------------------------
# 8. Linked families: decomposition along the couple graph
# --------------------------------------------------------------------------
MAX_COMPONENT_QUBITS = 14


def _component_task(args):
    from .quantum.qaoa import run_depth_ladder

    inst, comp_idx, budget, depths, shots = args
    prob = make_instance("L", inst)
    comps, _, _ = couple_components(prob, MAX_COMPONENT_QUBITS)
    comp = comps[comp_idx]
    sub = prob.restrict(comp, budget, name=f"{prob.name}-C{comp_idx + 1}-k{budget}")
    table = feasible_table(sub)
    cell = {"inst": inst, "component": comp_idx, "budget": budget, "n": sub.n, "exact": table.best,
            "exact_mask": table.best_mask, "n_feasible": int(len(table.masks))}
    if sub.n >= 3 and 0 < budget < sub.n:
        last = run_depth_ladder(sub, table, "constrained", depths, shots=shots, seed=inst)[-1]
        cell.update({"solver": "qaoa", "qaoa_mask": last["sampled_best_mask"],
                     "qaoa_value": table.best * (last["sampled_best_ratio"] or 0.0),
                     "p_opt": last["p_opt"], "quality": last["quality"]})
    else:      # one couple, or "test everyone": nothing to optimise
        cell.update({"solver": "trivial", "qaoa_mask": table.best_mask, "qaoa_value": table.best,
                     "p_opt": None, "quality": None})
    return cell


def exp_decomposition(n: int = 3, depths=(1, 2), shots: int = 512, workers: int = 8, **_) -> dict:
    INSTANCES.mkdir(parents=True, exist_ok=True)
    problems = [make_instance("L", i) for i in range(n)]
    tasks, structure = [], []
    for i, prob in enumerate(problems):
        prob.save(INSTANCES / f"{prob.name}.json")
        comps, singles, cut = couple_components(prob, MAX_COMPONENT_QUBITS)
        structure.append((comps, singles, cut))
        tasks += [(i, c, b, tuple(depths), shots) for c, comp in enumerate(comps)
                  for b in range(1, min(len(comp), prob.k) + 1)]
    cells = _map(_component_task, tasks, workers)
    rows = []
    for i, prob in enumerate(problems):
        comps, singles, cut = structure[i]
        mine = [c for c in cells if c["inst"] == i]
        result = {"instance": prob.name, "n": prob.n, "k": prob.k, "edges": len(prob.edges),
                  "components": len(comps), "component_sizes": sorted((len(c) for c in comps), reverse=True),
                  "isolated_people": len(singles), "max_qubits": max((len(c) for c in comps), default=0),
                  "cut_weight": cut, "qaoa_runs": sum(c["solver"] == "qaoa" for c in mine),
                  "qaoa_cells_optimal": float(np.mean([abs(c["qaoa_value"] - c["exact"]) < 1e-9
                                                       for c in mine if c["solver"] == "qaoa"] or [1.0])),
                  "cluster_p_opt": _stats([c["p_opt"] for c in mine if c["solver"] == "qaoa"])}
        x_milp, v_milp, info = milp_exact(prob)
        result["exact"] = {"value": v_milp, "proven_optimal": info["proven_optimal"]}
        pool, order = pool_values(prob, singles, prob.k)
        for key, value_key, mask_key in (("decomposed_qaoa", "qaoa_value", "qaoa_mask"),
                                         ("decomposed_exact", "exact", "exact_mask")):
            tables, plans = [], {}
            for c, comp in enumerate(comps):
                vals = [0.0]
                for b in range(1, min(len(comp), prob.k) + 1):
                    cell = next(u for u in mine if u["component"] == c and u["budget"] == b)
                    vals.append(cell[value_key])
                    plans[(c, b)] = cell[mask_key]
                tables.append(vals)
            budgets, dp_value = split_budget(tables + [pool], prob.k)
            x = np.zeros(prob.n, dtype=int)
            for c, comp in enumerate(comps):
                if budgets[c] > 0:
                    for t, node in enumerate(comp):
                        x[node] = (plans[(c, budgets[c])] >> t) & 1
            x[order[:budgets[-1]]] = 1
            value = prob.value(x)
            result[key] = {"budgets": budgets, "value": value, "ratio": value / v_milp,
                           "feasible": bool(prob.is_feasible(x)), "optimal": bool(value >= v_milp - 1e-9)}
        rng = np.random.default_rng(i)
        for name, x in (("field", field_rule(prob)), ("relevance", relevance_rule(prob)),
                        ("greedy", greedy(prob)), ("annealing", simulated_annealing(prob, rng, sweeps=60))):
            result[name] = {"value": prob.value(x), "ratio": prob.value(x) / v_milp}
        rows.append(result)
    summary = {name: _stats([r[name]["ratio"] for r in rows])
               for name in ("decomposed_qaoa", "decomposed_exact", "field", "relevance", "greedy", "annealing")}
    out = {"instances": n, "depths": list(depths), "shots": shots, "max_component_qubits": MAX_COMPONENT_QUBITS,
           "rows": rows, "summary": summary, "cells": cells}
    save("decomposition", out)
    return out


# --------------------------------------------------------------------------
# 9. Demo instance for the website and the report
# --------------------------------------------------------------------------
def exp_demo(index: int | None = None, **_) -> dict:
    from .quantum.qaoa import QAOA

    bench = load("benchmark")
    small = [r for r in bench["instances"] if r["size"] == "S"]
    if index is None:
        # Fixed rule, independent of QAOA performance: among the small instances with at
        # least five couple links, take the one whose best plan is worth the most.
        index = max(small, key=lambda r: (r["edges"] >= 5, r["best"]))["index"]
    row = next(r for r in small if r["index"] == index)
    prob = make_instance("S", index)
    table = feasible_table(prob)
    fam = prob.family
    cand = {pid: t for t, pid in enumerate(prob.person_ids)}
    view = family_view(prob)
    people, couples = view["people"], view["couples"]

    def plan(mask: int) -> dict:
        x = prob.mask_to_x(mask)
        return {"mask": int(mask), "chosen": [prob.person_ids[i] for i in np.flatnonzero(x)],
                "labels": prob.describe(x), "value": prob.value(x), "couples": prob.couples_found(x),
                "carriers": prob.carriers_found(x), "ratio": prob.value(x) / table.best,
                "quality": table.quality(prob.value(x))}

    plans = {"exact": plan(table.best_mask)}
    for name in ("field", "relevance", "greedy", "annealing"):
        plans[name] = plan(row["classical"][name]["mask"])
    edges = np.linspace(0, 1, 11)
    span = table.best - table.worst
    qual = (table.values - table.worst) / span

    def histogram(probs):
        pv = probs[table.masks]
        pv = pv / pv.sum()
        return [float(pv[(qual >= lo) & ((qual < hi) | (hi >= 1.0))].sum()) for lo, hi in zip(edges[:-1], edges[1:])]

    uniform = np.zeros(1 << prob.n)
    uniform[table.masks] = 1.0 / len(table.masks)
    hist = {"edges": edges.tolist(), "random": histogram(uniform)}
    qaoa = []
    for q in row["qaoa"]:
        engine = QAOA(prob, q["method"], reps=q["p"])
        probs = engine.probabilities(q["angles"])
        hist[f"{q['method']}_p{q['p']}"] = histogram(probs)
        qaoa.append({"method": q["method"], "p": q["p"], "angles": q["angles"], "quality": q["quality"],
                     "ratio": q["ratio"], "p_opt": q["p_opt"], "valid_share": q["valid_share"],
                     "shots_95": q["shots_95"], "best": plan(q["sampled_best_mask"]),
                     "top": [{**plan(t["mask"]), "share": t["share"]} for t in q["sampled_top"][:6]]})
    out = {"name": prob.name, "n": prob.n, "k": prob.k, "lam": prob.lam, "people": people, "couples": couples,
           "candidates": [{"qubit": t, "id": pid, "label": prob.labels[t], "p": float(prob.p[t]),
                           "r": float(prob.r[t])} for pid, t in cand.items()],
           "edges": [{"i": i, "j": j, "kind": k, "w": float(w), "c": float(c), "weight": float(w * c)}
                     for (i, j), k, w, c in zip(prob.edges, prob.kinds, prob.w, prob.c)],
           "n_feasible": int(len(table.masks)), "best": table.best, "worst": table.worst, "mean": table.mean,
           "random": row["classical"]["random"], "plans": plans, "qaoa": qaoa, "histogram": hist,
           "parents_are_cousins": bool(fam.params.get("parents_are_cousins")),
           "selection": "small instance with the largest optimum among those with at least five couple links"}
    save("demo", out)
    return out


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
EXPERIMENTS = {
    "genetics": exp_genetics, "gate1": exp_gate1, "benchmark": exp_benchmark, "circuits": exp_circuits,
    "ablation": exp_ablation, "noise": exp_noise, "tradeoff": exp_tradeoff,
    "decomposition": exp_decomposition, "demo": exp_demo,
}

QUICK = {
    "genetics": {"n_cal": 10}, "gate1": {"n_instances": 12}, "benchmark": {"n_s": 4, "n_m": 2, "maxiter": 80},
    "circuits": {"sizes": ("S",)}, "ablation": {"n": 3}, "noise": {"n": 2, "depths": (1,), "shots": 2048},
    "tradeoff": {"size": "S", "shots": 64, "scan": 4}, "decomposition": {"n": 1, "depths": (1,)}, "demo": {},
}


def write_meta(timings: dict, quick: bool, workers: int) -> None:
    import qiskit
    import qiskit_aer
    import scipy

    save("meta", {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "package": __version__, "quick": quick, "workers": workers,
        "python": platform.python_version(), "platform": platform.platform(),
        "qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__,
        "numpy": np.__version__, "scipy": scipy.__version__,
        "carrier_rate": CARRIER_RATE, "lambda": DEFAULT_LAMBDA, "sizes": SIZES, "seconds": timings,
        "hardware": "simulator only (Qiskit Aer); no real quantum processor was used",
    })


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("experiment", choices=["all", *EXPERIMENTS])
    parser.add_argument("--quick", action="store_true", help="reduced matrix for a fast check")
    parser.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) // 2)))
    args = parser.parse_args(argv)
    names = list(EXPERIMENTS) if args.experiment == "all" else [args.experiment]
    timings = {}
    for name in names:
        t0 = time.perf_counter()
        kwargs = dict(QUICK[name]) if args.quick else {}
        EXPERIMENTS[name](workers=args.workers, **kwargs)
        timings[name] = round(time.perf_counter() - t0, 1)
        print(f"[{name}] done in {timings[name]} s", flush=True)
    if args.experiment == "all":
        write_meta(timings, args.quick, args.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
