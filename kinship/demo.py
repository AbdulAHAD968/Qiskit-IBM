"""One-command demo: one family, one visit, one plan.

    python -m kinship.demo                         default instance, about 20 seconds
    python -m kinship.demo --size M --index 3      a 16-relative family, a few minutes
    python -m kinship.demo --seed 42 --n 9 --k 3   a new random family

The demo builds a synthetic family, computes carrier probabilities, trains the
constrained QAOA circuit with Qiskit, measures plans, and compares the result
with the exact optimum and the field officer's rule. It also saves the family
tree with the chosen relatives highlighted.
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np

from .classical import feasible_table, field_rule, greedy, relevance_rule
from .pedigree import generate_family
from .problem import build_problem, make_instance
from .view import family_view

ROOT = Path(__file__).resolve().parents[1]


def _rule(char: str = "-", width: int = 78) -> str:
    return char * width


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", choices=["S", "M"], default="S")
    parser.add_argument("--index", type=int, default=16, help="seeded instance index (default: the report's example)")
    parser.add_argument("--seed", type=int, help="generate a new family from this seed instead")
    parser.add_argument("--n", type=int, default=10, help="relatives who can be tested (with --seed)")
    parser.add_argument("--k", type=int, default=4, help="test kits (with --seed)")
    parser.add_argument("--depth", type=int, default=3, help="largest QAOA depth p")
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--no-figure", action="store_true")
    args = parser.parse_args(argv)
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    from .quantum.qaoa import QAOA, counts_metrics, distribution_metrics

    if args.seed is not None:
        problem = build_problem(generate_family(args.seed, args.n), args.k, name=f"seed-{args.seed}")
    else:
        problem = make_instance(args.size, args.index)
    fam = problem.family
    print(_rule("="))
    print(f"Kinship screening demo: instance {problem.name}")
    print(f"{len(fam.people)} people in the family tree, {problem.n} can be tested, {problem.k} kits")
    print(_rule("="))
    print(f"{'qubit':<6}{'relative':<34}{'life stage':<12}{'carrier p':>10}{'relevance':>11}")
    for i in range(problem.n):
        stage = fam.people[problem.person_ids[i]].stage
        print(f"q{i:<5}{problem.labels[i]:<34}{stage:<12}{problem.p[i]:>10.3f}{problem.r[i]:>11.1f}")
    print(_rule())
    print("Couple links between relatives who can be tested")
    for (i, j), kind, w, c in zip(problem.edges, problem.kinds, problem.w, problem.c):
        print(f"  {problem.labels[i]} + {problem.labels[j]}: {kind}, both carriers {w:.3f}, "
              f"link strength {c:.2f}, weight {w * c:.3f}")
    if not problem.edges:
        print("  none")

    table = feasible_table(problem)
    print(_rule())
    print(f"Exact reference: brute force over {len(table.masks)} valid plans")
    reference = {
        "Exact optimum": problem.mask_to_x(table.best_mask),
        "Field officer's rule": field_rule(problem),
        "Relevance-weighted rule": relevance_rule(problem),
        "Greedy": greedy(problem),
    }

    print(_rule())
    print("Constrained QAOA in Qiskit: Dicke start state, RZZ cost layer, XY ring mixer")
    warm, engine, run = None, None, None
    for p in range(1, args.depth + 1):
        t0 = time.perf_counter()
        engine = QAOA(problem, "constrained", reps=p)
        run = engine.train(warm=warm)
        warm = np.array(run.angles)
        m = distribution_metrics(engine.probabilities(run.angles), table)
        print(f"  depth {p}: quality {m['quality']:.3f}, chance one shot is the best plan {100 * m['p_opt']:.2f}%, "
              f"valid shots {100 * m['valid_share']:.0f}%, {run.evaluations} circuit evaluations, "
              f"{time.perf_counter() - t0:.1f} s")
    random_p = len(table.optimal_masks()) / len(table.masks)
    print(f"  random valid plan: quality {table.quality(table.mean):.3f}, chance of the best plan {100 * random_p:.2f}%")

    counts = engine.sample(run.angles, shots=args.shots, seed=1)
    sampled = counts_metrics(counts, problem, table)
    print(_rule())
    print(f"Sampler: {args.shots} shots, {len(counts)} distinct plans measured, "
          f"{100 * sampled['valid_share']:.0f}% use exactly {problem.k} kits")
    print("Most frequent measured plans")
    for item in sampled["top"][:5]:
        people = ", ".join(problem.describe(problem.mask_to_x(item["mask"])))
        print(f"  {100 * item['share']:5.1f}% of shots, value {item['value']:.3f}: {people}")
    qaoa_x = problem.mask_to_x(sampled["best_mask"])
    reference["Constrained QAOA (best measured plan)"] = qaoa_x

    print(_rule())
    print(f"{'plan':<40}{'couples found':>14}{'value':>9}{'of best':>9}")
    for name, x in reference.items():
        value = problem.value(x)
        print(f"{name:<40}{problem.couples_found(x):>14.3f}{value:>9.3f}{100 * value / table.best:>8.0f}%")
    print(_rule())
    print("Plan for this visit (constrained QAOA):")
    for label in problem.describe(qaoa_x):
        print(f"  test {label}")
    if abs(problem.value(qaoa_x) - table.best) < 1e-9:
        print("This matches the exact optimum.")
    print("Note: at this size brute force is instant. The demo shows the method, not a speedup.")

    if not args.no_figure:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from .plots import AQUA, BLUE, draw_pedigree

        view = family_view(problem)
        fig, axes = plt.subplots(2, 1, figsize=(9.5, 8.6))
        fx = reference["Field officer's rule"]
        chosen = lambda x: [problem.person_ids[i] for i in np.flatnonzero(x)]  # noqa: E731
        draw_pedigree(axes[0], view, chosen(fx), "Field officer's rule", AQUA,
                      f"{100 * problem.value(fx) / table.best:.0f}% of the best plan")
        draw_pedigree(axes[1], view, chosen(qaoa_x), "Constrained QAOA plan", BLUE,
                      f"{100 * problem.value(qaoa_x) / table.best:.0f}% of the best plan")
        out = ROOT / "results" / "figures" / f"demo_{problem.name}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out)
        plt.close(fig)
        print(f"Family tree saved to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
