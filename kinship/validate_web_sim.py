"""Check the website's in-browser simulator against the Qiskit circuits.

    python -m kinship.validate_web_sim        needs Node.js, a few seconds

web/qaoa-sim.js re-implements both QAOA circuits in JavaScript so that the
website can run them live: the constrained circuit inside the subspace of valid
plans, and the penalty circuit on all 2^n bitstrings. This script runs that
file under Node.js on the demonstration family and compares it with Qiskit:

1. the probability of every outcome, at the trained angles and at seeded random
   angles, for both circuits and every depth, and the expected value against
   the Estimator primitive (tolerance 1e-9);
2. the page's own tuning recipe (grid, warm starts, Nelder-Mead in place of
   COBYLA) against the numbers Qiskit's trained angles give for the constrained
   circuit (tolerance 1e-4, which is 0.01 percentage points).

Exit status 1 if a tolerance is exceeded, 2 if Node.js is not installed.
Nothing is written to results/.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from .problem import make_instance
from .quantum.qaoa import QAOA

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1e-9            # probabilities and expected values
RECIPE_TOLERANCE = 1e-4     # result of the browser tuning recipe against Qiskit's trained angles

DRIVER = """
const fs = require("fs");
const api = require(process.argv[1]);
const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const con = new api.Sim(data.problem), pen = new api.PenaltySim(data.problem);
const cases = data.cases.map(function (c) {
  let diff = 0, known = 0, total = 0, expectation;
  if (c.method === "constrained") {
    con.run(c.angles);
    const pr = con.probs();
    total = con.N;
    for (let s = 0; s < con.N; s++) {
      const ref = c.probs[String(con.masks[s])];
      if (typeof ref === "number") { known++; diff = Math.max(diff, Math.abs(pr[s] - ref)); }
    }
    expectation = con.expectation();
  } else {
    expectation = pen.f(c.angles);
    total = pen.M;
    for (let s = 0; s < pen.M; s++) {
      const ref = c.probs[String(s)];
      if (typeof ref === "number") { known++; diff = Math.max(diff, Math.abs(pen.re[s] * pen.re[s] + pen.im[s] * pen.im[s] - ref)); }
    }
  }
  return { label: c.label, outcomes: total, compared: known, max_diff: diff, expectation: expectation };
});
const ladder = api.tuneLadder(new api.Sim(data.problem), data.max_depth);
const recipe = {};
Object.keys(ladder).forEach(function (p) {
  const m = con.run(ladder[p].angles).metrics();
  recipe[p] = { p_opt: m.p_opt, ratio: m.ratio, quality: m.quality, evals: ladder[p].evals };
});
console.log(JSON.stringify({ cases: cases, recipe: recipe, penalty: pen.penalty, valid_plans: con.N }));
"""


def main() -> int:
    node = shutil.which("node")
    if node is None:
        print("Node.js is not installed, so web/qaoa-sim.js could not be run. Nothing was checked.")
        return 2
    demo = json.loads((ROOT / "results" / "demo.json").read_text(encoding="utf-8"))
    size, _, index = demo["name"].partition("-")
    problem = make_instance(size, int(index))
    assert (problem.n, problem.k) == (demo["n"], demo["k"]), "results/demo.json does not match the instance it names"

    cases, expected, sizes = [], {}, {}
    for run in demo["qaoa"]:
        method, p = run["method"], run["p"]
        engine = QAOA(problem, method, reps=p)
        rng = np.random.default_rng(100 * p + (0 if method == "constrained" else 1))
        random_angles = [float(v) for v in np.concatenate([rng.uniform(-1.5, 1.5, p), rng.uniform(0.0, np.pi, p)])]
        for kind, angles in (("trained angles", run["angles"]), ("random angles", random_angles)):
            label = f"{method}, depth {p}, {kind}"
            probs = engine.probabilities(angles)
            keep = range(1 << problem.n) if method == "penalty" else \
                [m for m in range(1 << problem.n) if bin(m).count("1") == problem.k]
            cases.append({"label": label, "method": method, "angles": angles,
                          "probs": {str(m): float(probs[m]) for m in keep}})
            expected[label] = float(engine.expectation(angles)[0])
            sizes[label] = len(keep)
    trained = {run["p"]: run for run in demo["qaoa"] if run["method"] == "constrained"}

    payload = {"problem": {"n": demo["n"], "k": demo["k"], "lam": demo["lam"],
                           "p": [c["p"] for c in demo["candidates"]], "r": [c["r"] for c in demo["candidates"]],
                           "edges": [{key: e[key] for key in ("i", "j", "w", "c")} for e in demo["edges"]]},
               "cases": cases, "max_depth": max(trained)}
    with tempfile.TemporaryDirectory() as folder:
        data_path = Path(folder) / "cases.json"
        data_path.write_text(json.dumps(payload), encoding="utf-8")
        done = subprocess.run([node, "-e", DRIVER, str(ROOT / "web" / "qaoa-sim.js"), str(data_path)],
                              capture_output=True, text=True)
    if done.returncode != 0:
        print(done.stderr.strip() or "Node.js failed without a message.")
        return 1
    out = json.loads(done.stdout)

    worst = 0.0
    print(f"{demo['name']}: {demo['n']} relatives, {demo['k']} kits, {out['valid_plans']} valid plans, "
          f"{1 << demo['n']:,} bitstrings")
    print("1. Outcome probabilities and expected value, JavaScript against Qiskit")
    for row in out["cases"]:
        complete = row["compared"] == row["outcomes"] == sizes[row["label"]]
        gap = abs(row["expectation"] - expected[row["label"]])
        worst = max(worst, row["max_diff"], gap, 0.0 if complete else 1.0)
        print(f"   {row['label']}: largest difference in a probability {row['max_diff']:.1e}, "
              f"in the expected value {gap:.1e}" + ("" if complete else "  (outcomes missing)"))
    print("2. The page's tuning recipe against Qiskit's trained angles (constrained circuit)")
    recipe_worst = 0.0
    for p, run in sorted(trained.items()):
        mine = out["recipe"][str(p)]
        gaps = {key: abs(mine[key] - run[key]) for key in ("p_opt", "ratio", "quality")}
        recipe_worst = max(recipe_worst, gaps["p_opt"], gaps["ratio"])
        print(f"   depth {p}: chance of the best plan {100 * mine['p_opt']:.3f}% against {100 * run['p_opt']:.3f}%, "
              f"value / optimum {100 * mine['ratio']:.3f}% against {100 * run['ratio']:.3f}% "
              f"(differences {gaps['p_opt']:.1e} and {gaps['ratio']:.1e}; {mine['evals']} evaluations)")
    ok = worst <= TOLERANCE and recipe_worst <= RECIPE_TOLERANCE
    print(f"web/qaoa-sim.js {'agrees with' if worst <= TOLERANCE else 'DIFFERS from'} the Qiskit circuits "
          f"(largest difference {worst:.1e}, tolerance {TOLERANCE:.0e}); its tuning recipe "
          f"{'reaches' if recipe_worst <= RECIPE_TOLERANCE else 'DOES NOT reach'} Qiskit's result "
          f"(largest difference {recipe_worst:.1e}, tolerance {RECIPE_TOLERANCE:.0e}).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
