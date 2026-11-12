"""Classical references: exact answers and the heuristics a field team would use."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .problem import ScreeningProblem


@dataclass
class FeasibleTable:
    """Every valid plan (exactly k tests) with its objective value."""

    masks: np.ndarray
    values: np.ndarray

    @property
    def best(self) -> float:
        return float(self.values.max())

    @property
    def worst(self) -> float:
        return float(self.values.min())

    @property
    def mean(self) -> float:
        return float(self.values.mean())

    @property
    def best_mask(self) -> int:
        return int(self.masks[int(np.argmax(self.values))])

    def optimal_masks(self, tol: float = 1e-12) -> np.ndarray:
        return self.masks[self.values >= self.best - tol]

    def quality(self, value: float) -> float:
        """Scale a value so the worst valid plan is 0 and the best is 1."""
        span = self.best - self.worst
        return 1.0 if span <= 0 else float((value - self.worst) / span)


def feasible_table(problem: ScreeningProblem) -> FeasibleTable:
    """Brute force: enumerate all C(n, k) valid plans. Exact for S and M sizes."""
    masks = problem.feasible_masks()
    W, h = problem.W, problem.h
    bits = ((masks[:, None] >> np.arange(problem.n)) & 1).astype(np.float64)
    values = 0.5 * np.einsum("si,ij,sj->s", bits, W, bits) + bits @ h
    return FeasibleTable(masks, values)


def brute_force(problem: ScreeningProblem):
    table = feasible_table(problem)
    return problem.mask_to_x(table.best_mask), table.best


def _top_k(scores: np.ndarray, k: int) -> np.ndarray:
    order = np.lexsort((np.arange(len(scores)), -scores))     # ties broken by index
    x = np.zeros(len(scores), dtype=int)
    x[order[:k]] = 1
    return x


def field_rule(problem: ScreeningProblem) -> np.ndarray:
    """The field officer's rule: test the k people with the highest carrier probability."""
    return _top_k(problem.p, problem.k)


def relevance_rule(problem: ScreeningProblem) -> np.ndarray:
    """A sharper individual rule: rank by relevance times carrier probability."""
    return _top_k(problem.r * problem.p, problem.k)


def tie_break_range(problem: ScreeningProblem, scores: np.ndarray, tol: float = 1e-9):
    """Best and worst value of a top-k rule over every way of breaking ties in the scores.

    Scores within ``tol`` of the k-th largest count as tied. Returns
    (best value, worst value, True if there is a tie at the cut-off).
    The rules above break ties by index, which is arbitrary; this bracket shows
    how much that choice can matter.
    """
    k = problem.k
    kth = np.sort(scores)[::-1][k - 1]
    forced = [i for i in range(problem.n) if scores[i] > kth + tol]
    tied = [i for i in range(problem.n) if abs(scores[i] - kth) <= tol]
    need = k - len(forced)
    values = []
    for extra in combinations(tied, need):
        x = np.zeros(problem.n, dtype=int)
        x[forced + list(extra)] = 1
        values.append(problem.value(x))
    return max(values), min(values), len(tied) > need


def greedy(problem: ScreeningProblem) -> np.ndarray:
    """Add, one at a time, the person with the largest marginal gain."""
    W, h = problem.W, problem.h
    x = np.zeros(problem.n, dtype=int)
    for _ in range(problem.k):
        gain = h + W @ x
        gain[x == 1] = -np.inf
        x[int(np.argmax(gain))] = 1
    return x


def random_plan(problem: ScreeningProblem, rng: np.random.Generator) -> np.ndarray:
    x = np.zeros(problem.n, dtype=int)
    x[rng.choice(problem.n, size=problem.k, replace=False)] = 1
    return x


def simulated_annealing(
    problem: ScreeningProblem, rng: np.random.Generator, sweeps: int = 150,
    t_start: float | None = None, t_end: float | None = None,
) -> np.ndarray:
    """Simulated annealing with swap moves, so every state uses exactly k kits."""
    W, h = problem.W, problem.h
    n, k = problem.n, problem.k
    if k == 0 or k == n:
        return np.full(n, int(k == n))
    x = random_plan(problem, rng)
    cur = problem.value(x)
    best_x, best = x.copy(), cur
    scale = float(np.max(h + W.sum(axis=1))) or 1.0
    t0 = t_start if t_start is not None else 0.5 * scale
    t1 = t_end if t_end is not None else 0.005 * scale
    steps = sweeps * n
    for t in range(steps):
        temp = t0 * (t1 / t0) ** (t / max(steps - 1, 1))
        i = int(rng.choice(np.flatnonzero(x == 1)))
        j = int(rng.choice(np.flatnonzero(x == 0)))
        delta = (h[j] + W[j] @ x - W[j, i]) - (h[i] + W[i] @ x)
        if delta >= 0 or rng.random() < np.exp(delta / temp):
            x[i], x[j] = 0, 1
            cur += delta
            if cur > best + 1e-12:
                best_x, best = x.copy(), cur
    return best_x


def milp_exact(problem: ScreeningProblem, time_limit: float = 60.0):
    """Exact integer-programming solve (HiGHS through SciPy). Used for the L size.

    The products x_i x_j are linearised with y_e <= x_i and y_e <= x_j, which is
    tight because every couple weight is non-negative.
    """
    n, m = problem.n, len(problem.edges)
    weights = problem.w * problem.c
    cost = -np.concatenate([problem.h, weights])
    rows, lo, hi = [], [], []
    for e, (i, j) in enumerate(problem.edges):
        for node in (i, j):
            row = np.zeros(n + m)
            row[n + e] = 1.0
            row[node] = -1.0
            rows.append(row)
            lo.append(-np.inf)
            hi.append(0.0)
    card = np.zeros(n + m)
    card[:n] = 1.0
    rows.append(card)
    lo.append(problem.k)
    hi.append(problem.k)
    res = milp(
        c=cost,
        constraints=LinearConstraint(np.array(rows), np.array(lo), np.array(hi)),
        integrality=np.concatenate([np.ones(n), np.zeros(m)]),
        bounds=Bounds(np.zeros(n + m), np.ones(n + m)),
        options={"time_limit": time_limit},
    )
    x = np.round(res.x[:n]).astype(int)
    return x, problem.value(x), {"status": int(res.status), "message": res.message, "proven_optimal": res.status == 0}
