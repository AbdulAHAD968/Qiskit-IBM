"""Independent check of the pedigree engine by Monte Carlo gene dropping.

    python -m kinship.validate_genetics        about 1 minute, writes results/genetics_montecarlo.json

Nothing here uses the engine's inference code. Founders are drawn in
Hardy-Weinberg proportions, alleles are dropped down the family tree by
Mendel's first law, and a simulated family is kept only when the index child
is affected and nobody else is. The exact carrier and couple probabilities of
the engine must lie inside the sampling error of the simulation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import CARRIER_RATE
from .genetics import PedigreeModel, allele_frequency
from .problem import make_instance

ROOT = Path(__file__).resolve().parents[1]
CASES = (("S", 16, 40_000, 1), ("S", 1, 30_000, 2), ("M", 1, 30_000, 3))     # size, index, accepted samples, seed


def simulate(family, q: float, target: int, rng: np.random.Generator, chunk: int = 1_500_000, max_chunks: int = 80):
    """Rejection sampling of genotypes (number of copies of the allele) given the evidence."""
    people = family.people
    for p in people:                             # ids must be in topological order
        assert p.father is None or (p.father < p.id and p.mother < p.id)
    kept, total = [], 0
    for _ in range(max_chunks):
        g = np.zeros((len(people), chunk), dtype=np.int8)
        for p in people:
            if p.father is None or p.mother is None:
                g[p.id] = (rng.random(chunk) < q).astype(np.int8) + (rng.random(chunk) < q).astype(np.int8)
            else:
                g[p.id] = ((rng.random(chunk) < g[p.father] / 2.0).astype(np.int8)
                           + (rng.random(chunk) < g[p.mother] / 2.0).astype(np.int8))
        ok = np.ones(chunk, dtype=bool)
        for p in people:
            ok &= (g[p.id] == 2) if p.affected else (g[p.id] != 2)
        kept.append(g[:, ok])
        total += chunk
        if sum(k.shape[1] for k in kept) >= target:
            break
    return np.concatenate(kept, axis=1), total


def check(size: str, index: int, target: int, seed: int) -> dict:
    problem = make_instance(size, index)
    family = problem.family
    samples, total = simulate(family, allele_frequency(CARRIER_RATE), target, np.random.default_rng(seed))
    n = samples.shape[1]
    model = PedigreeModel(family, CARRIER_RATE)
    z_scores, rows = [], []

    def compare(kind: str, label: str, exact: float, estimate: float) -> None:
        if exact < 1e-12 or exact > 1 - 1e-12:           # certain events must be reproduced exactly
            assert abs(estimate - exact) < 1e-12, (label, exact, estimate)
            return
        z = (estimate - exact) / np.sqrt(exact * (1 - exact) / n)
        z_scores.append(float(z))
        rows.append({"kind": kind, "label": label, "exact": exact, "simulated": estimate, "z": float(z)})

    for p in family.people:
        if not p.affected:
            compare("carrier", p.label, model.carrier_prob(p.id), float((samples[p.id] == 1).mean()))
    for c in family.couples:
        label = f"{family.people[c.a].label} + {family.people[c.b].label}"
        compare("couple", label, model.both_carriers(c.a, c.b),
                float(((samples[c.a] == 1) & (samples[c.b] == 1)).mean()))
    z = np.abs(z_scores)
    return {"instance": problem.name, "people": len(family.people), "accepted": int(n), "simulated": int(total),
            "comparisons": len(z_scores), "max_abs_z": float(z.max()), "share_above_2": float((z > 2).mean()),
            "rows": rows}


def main() -> int:
    cases = [check(*case) for case in CASES]
    all_z = np.abs([r["z"] for c in cases for r in c["rows"]])
    out = {"carrier_rate": CARRIER_RATE, "method": "gene dropping with rejection sampling",
           "comparisons": int(all_z.size), "max_abs_z": float(all_z.max()),
           "share_above_2": float((all_z > 2).mean()), "share_above_3": float((all_z > 3).mean()),
           "cases": cases}
    path = ROOT / "results" / "genetics_montecarlo.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for c in cases:
        print(f"{c['instance']}: {c['people']} people, {c['accepted']:,} accepted of {c['simulated']:,} simulated, "
              f"{c['comparisons']} comparisons, largest deviation {c['max_abs_z']:.2f} standard errors")
    print(f"all: {out['comparisons']} comparisons, largest deviation {out['max_abs_z']:.2f} standard errors, "
          f"{100 * out['share_above_2']:.1f}% beyond 2 standard errors (about 5% expected by chance)")
    print("wrote", path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
