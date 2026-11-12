"""Check the website's in-browser simulator against the Qiskit circuit.

    python -m kinship.validate_web_sim        needs Node.js, a few seconds

web/qaoa-sim.js re-implements the constrained QAOA circuit inside the subspace
of valid plans, so that the website can run it live. This script runs that file
under Node.js on the demonstration family, at the trained angles and at seeded
random angles for every depth, and compares the probability of each valid plan
with the one from the Qiskit circuit. It also compares the expected value with
the Estimator primitive. Exit status 1 if anything differs by more than 1e-9,
2 if Node.js is not installed. Nothing is written to results/.
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
TOLERANCE = 1e-9

DRIVER = """
const fs = require("fs");
const { Sim } = require(process.argv[1]);
const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const sim = new Sim(data.problem);
const out = data.cases.map(function (c) {
  sim.run(c.angles);
  const pr = sim.probs();
  let diff = 0, known = 0;
  for (let s = 0; s < sim.N; s++) {
    const ref = c.probs[String(sim.masks[s])];
    if (typeof ref === "number") { known++; diff = Math.max(diff, Math.abs(pr[s] - ref)); }
  }
  return { label: c.label, plans: sim.N, compared: known, max_diff: diff, expectation: sim.expectation() };
});
console.log(JSON.stringify(out));
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

    cases, expected = [], {}
    for run in demo["qaoa"]:
        if run["method"] != "constrained":
            continue
        p = run["p"]
        engine = QAOA(problem, "constrained", reps=p)
        rng = np.random.default_rng(p)
        random_angles = [float(v) for v in np.concatenate([rng.uniform(-1.5, 1.5, p), rng.uniform(0.0, np.pi, p)])]
        for kind, angles in (("trained angles", run["angles"]), ("random angles", random_angles)):
            label = f"depth {p}, {kind}"
            probs = engine.probabilities(angles)
            valid = {str(m): float(probs[m]) for m in range(1 << problem.n) if bin(m).count("1") == problem.k}
            cases.append({"label": label, "angles": angles, "probs": valid})
            expected[label] = float(engine.expectation(angles)[0])

    payload = {"problem": {"n": demo["n"], "k": demo["k"], "lam": demo["lam"],
                           "p": [c["p"] for c in demo["candidates"]], "r": [c["r"] for c in demo["candidates"]],
                           "edges": [{key: e[key] for key in ("i", "j", "w", "c")} for e in demo["edges"]]},
               "cases": cases}
    with tempfile.TemporaryDirectory() as folder:
        data_path = Path(folder) / "cases.json"
        data_path.write_text(json.dumps(payload), encoding="utf-8")
        done = subprocess.run([node, "-e", DRIVER, str(ROOT / "web" / "qaoa-sim.js"), str(data_path)],
                              capture_output=True, text=True)
    if done.returncode != 0:
        print(done.stderr.strip() or "Node.js failed without a message.")
        return 1
    rows = json.loads(done.stdout)

    worst = 0.0
    print(f"{demo['name']}: {demo['n']} relatives, {demo['k']} kits, {rows[0]['plans']} valid plans")
    for row in rows:
        complete = row["compared"] == row["plans"] == len(cases[0]["probs"])
        gap = abs(row["expectation"] - expected[row["label"]])
        worst = max(worst, row["max_diff"], gap, 0.0 if complete else 1.0)
        print(f"  {row['label']}: largest difference in a plan probability {row['max_diff']:.1e}, "
              f"in the expected value {gap:.1e}" + ("" if complete else "  (plans missing)"))
    verdict = "agrees with" if worst <= TOLERANCE else "DIFFERS from"
    print(f"web/qaoa-sim.js {verdict} the Qiskit circuit (largest difference {worst:.1e}, tolerance {TOLERANCE:.0e}).")
    return 0 if worst <= TOLERANCE else 1


if __name__ == "__main__":
    raise SystemExit(main())
