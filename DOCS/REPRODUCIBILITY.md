# Reproducibility check

Two questions, with two different answers.

1. **Same machine.** A second full run reproduces every value in `results/*.json`. Only wall-clock
   and machine fields (`seconds`, `generated`, `platform`, `workers`) differ.
2. **Another platform.** A run in the Docker image (Linux) reproduces the classical and exact
   results, every circuit gate count and every QAOA result at depths 1 and 2, but **not every
   depth-3 number**. The conclusions are the same; some averages move. Details below.

The numbers in the report, the README and the website are those of the committed run (Windows).

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

`compare_runs` walks every JSON file, ignores the timing fields, compares numbers with a tolerance
of 1e-9 (absolute for values up to 1, relative above), and exits with status 1 if anything differs.

## Same machine

| When (12 November 2026, PKT) | Commit | Files compared | Differing values |
|---|---|---:|---:|
| 19:15 | `73d4c36`, before the review fixes | 10 | 0 |
| 20:07 | `56b84f7`, after the review fixes | 11 | 0 |

The second check also reran `python -m kinship.validate_genetics`, so it covers the Monte Carlo file
as well (the first check predates that file). In the second clone `git status` listed only
`results/benchmark.json` and `results/meta.json` as modified after the rerun, and every changed
line in them was a `seconds` or `generated` field; git reported the other nine result files as
unchanged. Commits after `56b84f7` changed documents, figures, the website and checks, not the code
that produces the results.

Both runs used one machine (Windows, Python 3.11.0, Qiskit 2.6.2, Qiskit Aer 0.18.2, 8 worker
processes).

## Another platform: the Docker image

The image built from this repository (Linux, Python 3.11.18, the same package versions) ran the
tests, the demo and the full experiment matrix on 12 November 2026 at 22:00 PKT. Its result files
are kept in `results/linux_container/`, so the comparison can be repeated:

```bash
python -m kinship.compare_runs results/linux_container
```

**Identical in the container**

- the 57 tests pass, and the demo prints the same plan with the same quality and probabilities;
- `genetics.json`, `genetics_montecarlo.json` and `gate1.json`: 0 differing values;
- every classical baseline, every two-qubit gate count, the trade-off front, and the decomposition
  result (the proven optimum on all three networks);
- every constrained-QAOA result at depths 1 and 2.

**Different in the container**

- **Constrained QAOA at depth 3.** 13 of the 96 constrained runs end at different angles; the other
  83 agree to 1e-6 in expected value. The 13 are the 12 runs that used the whole optimiser budget
  (two starts of 150 COBYLA iterations) and one more. A run that stops at the iteration limit has
  not converged, so its end point depends on rounding differences between platforms. In 10 of the
  13 the container reached the higher expected value.
- **Penalty QAOA.** Most runs differ in late digits (20 of 96 agree to 1e-6). The averages move by
  less than one percentage point.
- **Circuit depth after transpilation** differs by up to about 5% (970 against 920 layers for the
  16-qubit depth-3 constrained circuit). The two-qubit gate counts are the same.
- **Noise study.** The constrained rows agree within 0.3 percentage points. The largest difference
  is the share of valid shots of penalty QAOA at depth 2 (65.4% against 67.5% at 0.05% error).

| Number | Committed run (Windows) | Docker run (Linux) |
|---|---:|---:|
| Quality, constrained QAOA, depth 3, 10 qubits | 0.624 | 0.629 |
| Quality, constrained QAOA, depth 3, 16 qubits | 0.504 | 0.501 |
| Best plan per shot, depth 3, 10 qubits | 5.91% | 5.83% |
| Best plan per shot, depth 3, 16 qubits | 0.98% | 0.68% |
| Gain over random, mean, 10 qubits | 12.1 | 11.9 |
| Gain over random, median, 10 qubits | 8.2 | 8.5 |
| Gain over random, mean, 16 qubits | 32.4 | 24.5 |
| Gain over random, median, 16 qubits | 14.4 | 14.4 |
| Largest gain in one family, 16 qubits | 116 | 57 |
| Penalty QAOA, valid shots at depth 3, 10 qubits | 85.9% | 86.3% |
| Penalty QAOA, valid shots at depth 3, 16 qubits | 61.4% | 61.4% |
| Ablation, Dicke start, best plan per shot at depth 3 | 5.20% | 4.92% |
| Ablation, field-rule start, best plan per shot at depth 3 | 0.096% | 0.70% |

**What this means.** The conclusions do not change: constrained QAOA beats random picks and the
field officer's rule, does not beat greedy or simulated annealing, and never breaks the kit limit;
penalty QAOA stays near random; the cheaper start state fails. The depth-3 averages, however, are
one platform's run of an optimiser that often stops at its iteration limit. The mean gain at 16
qubits is the most sensitive number: 32 in the committed run, 24 in the container, with the same
median of 14. A larger iteration budget would be the fix; we did not rerun with one.

Other processors, other operating systems and other package versions were not tried. The image was
built from commit `0623e52`; the experiment code has not changed since.

## What makes the runs repeatable on one machine

- Every family is generated from a fixed seed.
- The statevector simulation is deterministic, each worker process uses one thread, and the
  sampler and the noise simulation are seeded.
- COBYLA is deterministic for a given start on a given machine.
- Choices between equal values (two identical siblings, two plans with the same value) are made by
  index with a tolerance of 1e-9, never by floating-point rounding noise.
