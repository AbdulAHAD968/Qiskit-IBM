# Reproducibility check

The claim: a second full run of the experiments on the same package versions reproduces every value
in `results/*.json`. Only wall-clock and machine fields (`seconds`, `generated`, `platform`,
`workers`) are allowed to differ.

## How to repeat it

```bash
git clone https://github.com/AbdulAHAD968/Qiskit-IBM.git second-run
cd second-run
pip install -r requirements.txt
python -m kinship.evaluate all            # about 8 minutes on 8 processes
python -m kinship.validate_genetics       # about 1 minute, the Monte Carlo cross-check
cd ..
python -m kinship.compare_runs second-run/results     # run from the first copy of the repository
```

`compare_runs` walks every JSON file, ignores the timing fields, compares numbers with a relative
tolerance of 1e-9, and exits with status 1 if anything differs.

## Result

| When (12 November 2026, PKT) | Commit | Files compared | Differing values |
|---|---|---:|---:|
| 19:15 | `73d4c36`, before the review fixes | 10 | 0 |
| 20:07 | `56b84f7`, after the review fixes | 11 | 0 |

The second check also reran `python -m kinship.validate_genetics`, so it covers the Monte Carlo file
as well (the first check predates that file). In the second clone `git status` listed only
`results/benchmark.json` and `results/meta.json` as modified after the rerun, and every changed
line in them was a `seconds` or `generated` field; git reported the other nine result files as
unchanged. Commits after `56b84f7` changed documents, figures and styling only, not the code that
produces the results.

All runs used the same machine (Windows, Python 3.11.0, Qiskit 2.6.2, Qiskit Aer 0.18.2, 8 worker
processes). The check does not cover other operating systems, processors or package versions.

## What makes the runs repeatable

- Every family is generated from a fixed seed.
- The statevector simulation is deterministic, each worker process uses one thread, and the
  sampler and the noise simulation are seeded.
- COBYLA is deterministic for a given start.
- Choices between equal values (two identical siblings, two plans with the same value) are made by
  index with a tolerance of 1e-9, never by floating-point rounding noise.
