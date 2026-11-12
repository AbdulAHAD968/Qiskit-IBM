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
cd ..
python -m kinship.compare_runs second-run/results     # run from the first copy of the repository
```

`compare_runs` walks every JSON file, ignores the timing fields, compares numbers with a relative
tolerance of 1e-9, and exits with status 1 if anything differs.

## Result

| When (12 November 2026, PKT) | Commit | Files compared | Differing values |
|---|---|---:|---:|
| 19:15 | `73d4c36` | 10 | 0 |

Both runs used the same machine (Windows, Python 3.11.0, Qiskit 2.6.2, Qiskit Aer 0.18.2, 8 worker
processes). The check does not cover other operating systems, processors or package versions.

## What makes the runs repeatable

- Every family is generated from a fixed seed.
- The statevector simulation is deterministic, each worker process uses one thread, and the
  sampler and the noise simulation are seeded.
- COBYLA is deterministic for a given start.
- Choices between equal values (two identical siblings, two plans with the same value) are made by
  index with a tolerance of 1e-9, never by floating-point rounding noise.
