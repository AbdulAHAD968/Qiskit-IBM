"""QAOA training and sampling with Qiskit primitives.

Angles are tuned by SciPy's COBYLA on expectation values from the Estimator
primitive. Screening plans are read out with the Sampler primitive. Exact
statevector probabilities are used only to report metrics without shot noise.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from qiskit import transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import EstimatorV2, SamplerV2
from scipy.optimize import minimize

from ..classical import FeasibleTable
from ..problem import ScreeningProblem
from .circuits import constrained_qaoa_circuit, penalty_qaoa_circuit, scaled_ising


@dataclass
class QAOARun:
    method: str
    reps: int
    angles: list[float]                # [gamma_1..gamma_p, beta_1..beta_p]
    expectation: float                 # expected value of the trained objective
    evaluations: int
    seconds: float
    metrics: dict = field(default_factory=dict)


class QAOA:
    """One QAOA ansatz (constrained or penalty) for one screening problem."""

    def __init__(self, problem: ScreeningProblem, method: str = "constrained", reps: int = 1,
                 penalty: float | None = None, initial: str = "dicke", threads: int = 1):
        self.problem, self.method, self.reps = problem, method, reps
        if method == "constrained":
            self.qubo = problem.qubo()
            self.circuit, self.scale = constrained_qaoa_circuit(problem, reps, initial)
        elif method == "penalty":
            self.penalty = problem.default_penalty() if penalty is None else penalty
            self.qubo = problem.penalty_qubo(self.penalty)
            self.circuit, self.scale = penalty_qaoa_circuit(problem, reps, self.penalty)
        else:
            raise ValueError(f"unknown method {method!r}")
        _, _, self.offset, scale = scaled_ising(self.qubo)
        assert abs(scale - self.scale) < 1e-12
        self.operator = self.qubo.operator(self.scale)
        self._backend_options = {"method": "statevector", "max_parallel_threads": threads}
        self.backend = AerSimulator(**self._backend_options)
        self.isa = transpile(self.circuit, self.backend, optimization_level=1, seed_transpiler=7)
        self.estimator = EstimatorV2(options={"backend_options": self._backend_options})
        names = [p.name for p in self.isa.parameters]
        self._columns = [
            (int(nm[nm.index("[") + 1:-1]) + (0 if nm.startswith("gamma") else reps)) for nm in names
        ]
        self.evaluations = 0

    # ---- expectation values ----------------------------------------------
    def _bind_array(self, thetas: np.ndarray) -> np.ndarray:
        thetas = np.atleast_2d(np.asarray(thetas, dtype=float))
        return thetas[:, self._columns]

    def expectation(self, thetas) -> np.ndarray:
        """Expected objective value for one or many angle vectors (Estimator primitive)."""
        values = self._bind_array(thetas)
        self.evaluations += len(values)
        evs = self.estimator.run([(self.isa, self.operator, values)]).result()[0].data.evs
        return self.scale * np.atleast_1d(evs) + self.offset

    # ---- training ----------------------------------------------------------
    def train(self, warm: np.ndarray | None = None, maxiter: int = 150, grid=(16, 10)) -> QAOARun:
        """Tune the angles. Depth 1 starts from a grid, deeper circuits from ``warm``."""
        t0 = time.perf_counter()
        p = self.reps

        def negative(theta):
            return -float(self.expectation(theta)[0])

        if warm is None:
            if p != 1:
                raise ValueError("depth > 1 needs the trained angles of depth p-1 as a warm start")
            gam = np.linspace(-2.0, 2.0, grid[0])
            bet = np.linspace(0.15, np.pi - 0.15, grid[1])
            G, B = np.meshgrid(gam, bet, indexing="ij")
            points = np.column_stack([G.ravel(), B.ravel()])
            scores = self.expectation(points)
            starts = [points[t] for t in np.argsort(scores)[::-1][:2]]
            rhobeg = 0.15
        else:
            starts = [interp_start(warm), append_zero_start(warm)]
            rhobeg = 0.1
        best = None
        for start in starts:
            res = minimize(negative, start, method="COBYLA", options={"maxiter": maxiter, "rhobeg": rhobeg})
            if best is None or res.fun < best.fun:
                best = res
        return QAOARun(self.method, p, [float(v) for v in best.x], -float(best.fun),
                       self.evaluations, time.perf_counter() - t0)

    # ---- read-out ------------------------------------------------------------
    def bound(self, theta):
        values = self._bind_array(theta)[0]
        return self.isa.assign_parameters(dict(zip(self.isa.parameters, values)))

    def bound_logical(self, theta):
        """The untranspiled ansatz with angles bound, for hardware-style transpilation."""
        theta = np.asarray(theta, dtype=float)
        mapping = {}
        for prm in self.circuit.parameters:
            index = int(prm.name[prm.name.index("[") + 1:-1])
            mapping[prm] = theta[index] if prm.name.startswith("gamma") else theta[self.reps + index]
        return self.circuit.assign_parameters(mapping)

    def probabilities(self, theta) -> np.ndarray:
        """Exact outcome probabilities, indexed by integer mask (bit i = qubit i)."""
        return Statevector(self.bound(theta)).probabilities()

    def sample(self, theta, shots: int = 4096, seed: int = 0) -> dict[int, int]:
        """Measured plans as {mask: count}, using the Sampler primitive."""
        qc = self.bound(theta)
        qc.measure_all()
        sampler = SamplerV2(default_shots=shots, seed=seed, options={"backend_options": self._backend_options})
        counts = sampler.run([qc]).result()[0].data.meas.get_counts()
        return {int(bits, 2): c for bits, c in counts.items()}


def interp_start(prev: np.ndarray) -> np.ndarray:
    """INTERP warm start of Zhou et al. (2020): stretch depth-q angles to depth q+1."""
    prev = np.asarray(prev, dtype=float)
    q = len(prev) // 2

    def stretch(old):
        ext = np.concatenate([[0.0], old, [0.0]])
        return np.array([(i - 1) / q * ext[i - 1] + (q - i + 1) / q * ext[i] for i in range(1, q + 2)])

    return np.concatenate([stretch(prev[:q]), stretch(prev[q:])])


def append_zero_start(prev: np.ndarray) -> np.ndarray:
    """Depth q+1 start that reproduces the depth-q circuit exactly (new layer is the identity)."""
    prev = np.asarray(prev, dtype=float)
    q = len(prev) // 2
    return np.concatenate([prev[:q], [0.0], prev[q:], [0.0]])


def distribution_metrics(probs: np.ndarray, table: FeasibleTable) -> dict:
    """Metrics of an outcome distribution against the exact answer.

    valid_share   probability that a shot uses exactly k kits
    quality       expected value of valid shots, scaled so worst = 0 and best = 1
    ratio         expected value of valid shots divided by the optimum
    p_opt         probability that a single shot is an optimal plan
    p_near        probability that a single shot is within 5 percent of the optimum
    shots_95      shots needed to see an optimal plan with 95 percent probability
    """
    pv = probs[table.masks]
    valid = float(pv.sum())
    mean_valid = float(pv @ table.values / valid) if valid > 0 else table.worst
    opt = table.values >= table.best - 1e-12
    p_opt = float(pv[opt].sum())
    p_near = float(pv[table.values >= 0.95 * table.best].sum())
    return {
        "valid_share": valid,
        "mean_valid": mean_valid,
        "quality": table.quality(mean_valid),
        "ratio": mean_valid / table.best if table.best > 0 else 1.0,
        "p_opt": p_opt,
        "p_near": p_near,
        "shots_95": shots_needed(p_opt),
    }


def shots_needed(p: float, confidence: float = 0.95) -> float | None:
    if p < 1e-12:
        return None
    if p >= 1:
        return 1.0
    return float(np.log(1 - confidence) / np.log(1 - p))


def counts_metrics(counts: dict[int, int], problem: ScreeningProblem, table: FeasibleTable) -> dict:
    """Metrics from measured shots, plus the plan the tool would hand to the field team."""
    lookup = {int(m): float(v) for m, v in zip(table.masks, table.values)}
    shots = sum(counts.values())
    valid = {m: c for m, c in counts.items() if m in lookup}
    n_valid = sum(valid.values())
    out = {"shots": shots, "valid_share": n_valid / shots if shots else 0.0}
    if not valid:
        out.update({"mean_valid": None, "quality": None, "best_mask": None, "best_value": None,
                    "best_ratio": None, "p_opt": 0.0, "top": []})
        return out
    mean_valid = sum(lookup[m] * c for m, c in valid.items()) / n_valid
    best_value = max(lookup[m] for m in valid)
    best_mask = min(m for m in valid if lookup[m] >= best_value - 1e-12)      # deterministic among equal plans
    opt_hits = sum(c for m, c in valid.items() if lookup[m] >= table.best - 1e-12)
    top = sorted(valid.items(), key=lambda kv: -kv[1])[:8]
    out.update({
        "mean_valid": mean_valid,
        "quality": table.quality(mean_valid),
        "best_mask": int(best_mask),
        "best_value": lookup[best_mask],
        "best_ratio": lookup[best_mask] / table.best if table.best > 0 else 1.0,
        "p_opt": opt_hits / shots,
        "top": [{"mask": int(m), "share": c / shots, "value": lookup[m]} for m, c in top],
    })
    return out


def run_depth_ladder(problem: ScreeningProblem, table: FeasibleTable, method: str,
                     depths=(1, 2, 3), shots: int = 4096, seed: int = 0, maxiter: int = 150,
                     threads: int = 1, initial: str = "dicke") -> list[dict]:
    """Train depths 1..p in sequence, warm-starting each depth from the previous one."""
    rows, warm = [], None
    for p in depths:
        engine = QAOA(problem, method, reps=p, initial=initial, threads=threads)
        run = engine.train(warm=warm, maxiter=maxiter)
        warm = np.array(run.angles)
        exact = distribution_metrics(engine.probabilities(run.angles), table)
        sampled = counts_metrics(engine.sample(run.angles, shots=shots, seed=seed), problem, table)
        rows.append({
            "method": method, "p": p, "angles": run.angles, "expectation": run.expectation,
            "evaluations": run.evaluations, "seconds": round(run.seconds, 3),
            **exact,
            "sampled_valid_share": sampled["valid_share"], "sampled_p_opt": sampled["p_opt"],
            "sampled_best_ratio": sampled["best_ratio"], "sampled_best_mask": sampled["best_mask"],
            "sampled_top": sampled["top"],
        })
    return rows
