"""The screening problem: objective, exactly-k rule and the Ising mapping.

Decision variable  x_i = 1 if relative i is tested in this visit, else 0.

    maximise   F(x) = sum_{(i,j) in C} c_ij * w_ij * x_i x_j  +  lambda * sum_i r_i p_i x_i
    subject to sum_i x_i = k

    w_ij  probability that i and j are both carriers (from the pedigree)
    c_ij  probability that the couple link is real (1 for married or engaged)
    p_i   probability that i is a carrier
    r_i   relevance of learning the carrier status of i

The first term is the expected number of at-risk couples identified: a couple
is only resolved when both partners are tested, which is why the value sits on
pairs and the problem is quadratic.

Bit convention used everywhere: index i of x, qubit i, and bit i of an integer
mask all refer to the same relative.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import numpy as np

from . import CARRIER_RATE, DEFAULT_LAMBDA
from .genetics import PedigreeModel
from .pedigree import Family, generate_family, generate_linked_families

SIZES = {
    "S": {"n": 10, "k": 4, "seed_base": 1000},
    "M": {"n": 16, "k": 5, "seed_base": 2000},
    "L": {"families": 4, "n_each": 12, "k": 12, "seed_base": 3000},
}


@dataclass
class Qubo:
    """f(x) = sum_{i<j} Q[i,j] x_i x_j + sum_i lin[i] x_i + const, to be maximised."""

    Q: np.ndarray
    lin: np.ndarray
    const: float = 0.0

    @property
    def n(self) -> int:
        return len(self.lin)

    def value(self, x) -> float:
        x = np.asarray(x, dtype=float)
        return float(x @ np.triu(self.Q, 1) @ x + self.lin @ x + self.const)

    def all_values(self) -> np.ndarray:
        """Value of every bitstring, indexed by integer mask (bit i = x_i)."""
        n = self.n
        idx = np.arange(1 << n, dtype=np.int64)
        bits = [((idx >> i) & 1).astype(np.float64) for i in range(n)]
        out = np.full(1 << n, self.const, dtype=np.float64)
        for i in range(n):
            if self.lin[i] != 0.0:
                out += self.lin[i] * bits[i]
            for j in range(i + 1, n):
                if self.Q[i, j] != 0.0:
                    out += self.Q[i, j] * bits[i] * bits[j]
        return out

    def ising(self):
        """Coefficients (a, b, const) with f = const + sum_i a_i z_i + sum_{i<j} b_ij z_i z_j.

        Uses x_i = (1 - z_i) / 2, so that qubit state |1> means "tested".
        """
        n = self.n
        a = -0.5 * self.lin.astype(float).copy()
        b: dict[tuple[int, int], float] = {}
        const = self.const + 0.5 * float(self.lin.sum())
        for i in range(n):
            for j in range(i + 1, n):
                q = float(self.Q[i, j])
                if q == 0.0:
                    continue
                b[(i, j)] = q / 4.0
                a[i] -= q / 4.0
                a[j] -= q / 4.0
                const += q / 4.0
        return a, b, const

    def operator(self, scale: float = 1.0):
        """SparsePauliOp H with f(x) = scale * <x|H|x> + const (const from :meth:`ising`)."""
        from qiskit.quantum_info import SparsePauliOp

        a, b, _ = self.ising()
        terms = [("Z", [i], a[i] / scale) for i in range(self.n) if abs(a[i]) > 1e-15]
        terms += [("ZZ", [i, j], c / scale) for (i, j), c in b.items() if abs(c) > 1e-15]
        if not terms:
            terms = [("I", [0], 0.0)]
        return SparsePauliOp.from_sparse_list(terms, num_qubits=self.n)


@dataclass
class ScreeningProblem:
    name: str
    n: int
    k: int
    lam: float
    p: np.ndarray                       # carrier probability per candidate
    r: np.ndarray                       # relevance per candidate
    edges: list[tuple[int, int]]        # couple links between candidates, i < j
    w: np.ndarray                       # P(both carriers) per edge
    c: np.ndarray                       # link strength per edge
    kinds: list[str]                    # married | engaged | potential
    labels: list[str]
    person_ids: list[int]
    family: Family | None = None
    meta: dict = field(default_factory=dict)

    # ---- weights ---------------------------------------------------------
    @property
    def W(self) -> np.ndarray:
        """Symmetric matrix of effective couple weights c_ij * w_ij."""
        M = np.zeros((self.n, self.n))
        for (i, j), w, c in zip(self.edges, self.w, self.c):
            M[i, j] += w * c
            M[j, i] += w * c
        return M

    @property
    def h(self) -> np.ndarray:
        return self.lam * self.r * self.p

    # ---- objective -------------------------------------------------------
    def couples_found(self, x) -> float:
        x = np.asarray(x, dtype=float)
        return float(0.5 * x @ self.W @ x)

    def carriers_found(self, x) -> float:
        """Relevance-weighted expected number of carriers found."""
        return float((self.r * self.p) @ np.asarray(x, dtype=float))

    def value(self, x) -> float:
        return self.couples_found(x) + self.lam * self.carriers_found(x)

    def is_feasible(self, x) -> bool:
        return int(np.sum(x)) == self.k

    def qubo(self) -> Qubo:
        return Qubo(np.triu(self.W, 1), self.h.copy(), 0.0)

    def default_penalty(self) -> float:
        """A penalty weight above the largest gain any single extra test can bring."""
        return float(1.1 * np.max(self.h + self.W.sum(axis=1)))

    def penalty_qubo(self, strength: float | None = None) -> Qubo:
        """F(x) - A * (sum_i x_i - k)^2 written as a QUBO (uses x_i^2 = x_i)."""
        A = self.default_penalty() if strength is None else strength
        Q = np.triu(self.W, 1) - 2.0 * A * np.triu(np.ones((self.n, self.n)), 1)
        lin = self.h - A * (1.0 - 2.0 * self.k)
        return Qubo(Q, lin, -A * self.k * self.k)

    # ---- helpers ---------------------------------------------------------
    def mask_to_x(self, mask: int) -> np.ndarray:
        return np.array([(mask >> i) & 1 for i in range(self.n)], dtype=int)

    def feasible_masks(self) -> np.ndarray:
        masks = [sum(1 << i for i in comb) for comb in combinations(range(self.n), self.k)]
        return np.array(masks, dtype=np.int64)

    def describe(self, x) -> list[str]:
        return [self.labels[i] for i in range(self.n) if x[i]]

    # ---- persistence -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name, "n": self.n, "k": self.k, "lam": self.lam,
            "p": [round(float(v), 10) for v in self.p],
            "r": [float(v) for v in self.r],
            "edges": [list(e) for e in self.edges],
            "w": [round(float(v), 10) for v in self.w],
            "c": [float(v) for v in self.c],
            "kinds": self.kinds, "labels": self.labels, "person_ids": self.person_ids,
            "family": self.family.to_dict() if self.family else None,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScreeningProblem":
        return cls(
            name=d["name"], n=d["n"], k=d["k"], lam=d["lam"],
            p=np.array(d["p"]), r=np.array(d["r"]),
            edges=[tuple(e) for e in d["edges"]], w=np.array(d["w"]), c=np.array(d["c"]),
            kinds=d["kinds"], labels=d["labels"], person_ids=d["person_ids"],
            family=Family.from_dict(d["family"]) if d.get("family") else None,
            meta=d.get("meta", {}),
        )

    def save(self, path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path) -> "ScreeningProblem":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def with_lambda(self, lam: float) -> "ScreeningProblem":
        d = self.to_dict()
        d["lam"] = lam
        return ScreeningProblem.from_dict(d)

    def restrict(self, idx: list[int], k: int, name: str = "") -> "ScreeningProblem":
        """Sub-problem on a subset of candidates; couple links leaving the subset are dropped."""
        pos = {old: new for new, old in enumerate(idx)}
        keep = [t for t, (i, j) in enumerate(self.edges) if i in pos and j in pos]
        return ScreeningProblem(
            name=name or f"{self.name}-sub", n=len(idx), k=k, lam=self.lam,
            p=self.p[idx], r=self.r[idx],
            edges=[tuple(sorted((pos[self.edges[t][0]], pos[self.edges[t][1]]))) for t in keep],
            w=self.w[keep], c=self.c[keep], kinds=[self.kinds[t] for t in keep],
            labels=[self.labels[i] for i in idx], person_ids=[self.person_ids[i] for i in idx],
            family=None, meta={"parent": self.name},
        )


def build_problem(
    family: Family, k: int, lam: float = DEFAULT_LAMBDA,
    carrier_rate: float = CARRIER_RATE, name: str = "",
) -> ScreeningProblem:
    """Turn a family into an optimisation instance using the exact pedigree engine."""
    model = PedigreeModel(family, carrier_rate)
    cand = family.candidates()
    idx = {pid: t for t, pid in enumerate(cand)}
    p = np.array([model.carrier_prob(pid) for pid in cand])
    r = np.array([family.relevance(pid) for pid in cand])
    edges, w, c, kinds = [], [], [], []
    for cp in family.couples:
        if cp.a in idx and cp.b in idx:
            edges.append(tuple(sorted((idx[cp.a], idx[cp.b]))))
            w.append(model.both_carriers(cp.a, cp.b))
            c.append(cp.strength)
            kinds.append(cp.kind)
    return ScreeningProblem(
        name=name, n=len(cand), k=k, lam=lam, p=p, r=r, edges=edges,
        w=np.array(w, dtype=float), c=np.array(c, dtype=float), kinds=kinds,
        labels=[family.people[pid].label for pid in cand], person_ids=cand, family=family,
        meta={"carrier_rate": carrier_rate, "seed": family.seed},
    )


def make_instance(size: str, index: int, lam: float = DEFAULT_LAMBDA) -> ScreeningProblem:
    """Seeded instance ``index`` of size S, M or L."""
    cfg = SIZES[size]
    seed = cfg["seed_base"] + index
    if size == "L":
        fam = generate_linked_families(seed, cfg["families"], cfg["n_each"])
    else:
        fam = generate_family(seed, cfg["n"])
    return build_problem(fam, cfg["k"], lam, name=f"{size}-{index:02d}")
