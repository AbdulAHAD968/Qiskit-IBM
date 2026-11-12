"""Exact carrier probabilities on a pedigree.

Model: one autosomal recessive gene with alleles A (normal) and a (beta
thalassaemia). Genotype states are 0 = AA, 1 = Aa (carrier), 2 = aa (affected).

* Founders follow Hardy-Weinberg proportions for a population carrier rate.
* Children inherit one allele from each parent (Mendel's first law).
* Evidence: the index child is affected; everyone else is clinically
  unaffected, so cannot be aa.

The pedigree is a Bayesian network. Marginals are computed exactly by variable
elimination, which also handles the loops created by cousin marriages.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from .pedigree import Family

AA, CARRIER, AFFECTED = 0, 1, 2


def allele_frequency(carrier_rate: float) -> float:
    """Frequency q of allele a such that 2q(1-q) equals the carrier rate."""
    return float((1.0 - np.sqrt(1.0 - 2.0 * carrier_rate)) / 2.0)


def transmission_table() -> np.ndarray:
    """T[father, mother, child] = P(child genotype | parental genotypes)."""
    passes = np.array([0.0, 0.5, 1.0])           # P(parent passes allele a)
    T = np.zeros((3, 3, 3))
    for f in range(3):
        for m in range(3):
            T[f, m, 0] = (1 - passes[f]) * (1 - passes[m])
            T[f, m, 1] = passes[f] * (1 - passes[m]) + (1 - passes[f]) * passes[m]
            T[f, m, 2] = passes[f] * passes[m]
    return T


def _contract(factors, keep):
    """Multiply factors and sum out every variable that is not in ``keep``."""
    scope = sorted({v for vs, _ in factors for v in vs})
    local = {v: i for i, v in enumerate(scope)}
    args = []
    for vs, tab in factors:
        args += [tab, [local[v] for v in vs]]
    args.append([local[v] for v in keep])
    return tuple(keep), np.einsum(*args)


class PedigreeModel:
    """Exact posterior over genotypes for one :class:`Family`."""

    def __init__(self, family: Family, carrier_rate: float = 0.05, observed: dict | None = None):
        self.family = family
        self.carrier_rate = carrier_rate
        self.q = allele_frequency(carrier_rate)
        q = self.q
        prior = np.array([(1 - q) ** 2, 2 * q * (1 - q), q * q])
        T = transmission_table()
        observed = observed or {}
        self.factors: list[tuple[tuple[int, ...], np.ndarray]] = []
        for p in family.people:
            evidence = np.array([0.0, 0.0, 1.0]) if p.affected else np.array([1.0, 1.0, 0.0])
            if p.id in observed:                 # a test result from an earlier visit
                evidence = np.zeros(3)
                evidence[observed[p.id]] = 1.0
            if p.father is None or p.mother is None:
                self.factors.append(((p.id,), prior * evidence))
            else:
                self.factors.append(((p.father, p.mother, p.id), T))
                self.factors.append(((p.id,), evidence))
        self.order = self._elimination_order()

    def _elimination_order(self) -> list[int]:
        nb: dict[int, set[int]] = defaultdict(set)
        for vs, _ in self.factors:
            for v in vs:
                nb[v].update(u for u in vs if u != v)
        order = []
        while nb:
            v = min(nb, key=lambda u: (len(nb[u]), u))      # min-degree heuristic
            ns = nb.pop(v)
            for a in ns:
                nb[a].discard(v)
                nb[a].update(ns - {a})
            order.append(v)
        return order

    def marginal(self, query) -> np.ndarray:
        """Posterior joint distribution of the queried people (one axis each)."""
        query = tuple(query)
        factors = list(self.factors)
        for v in self.order:
            if v in query:
                continue
            involved = [f for f in factors if v in f[0]]
            if not involved:
                continue
            factors = [f for f in factors if v not in f[0]]
            scope = sorted({u for vs, _ in involved for u in vs if u != v})
            factors.append(_contract(involved, scope))
        _, table = _contract(factors, query)
        return table / table.sum()

    def carrier_prob(self, pid: int) -> float:
        return float(self.marginal((pid,))[CARRIER])

    def carrier_probs(self) -> np.ndarray:
        return np.array([self.carrier_prob(p.id) for p in self.family.people])

    def both_carriers(self, a: int, b: int) -> float:
        """P(a and b are both carriers | pedigree, evidence)."""
        return float(self.marginal((a, b))[CARRIER, CARRIER])

    def marginal_reference(self, query) -> np.ndarray:
        """The same marginal through NumPy's own contraction planner (cross-check for tests)."""
        people = sorted({v for vs, _ in self.factors for v in vs})
        if len(people) > 52:
            raise ValueError("reference contraction is limited to 52 people")
        local = {v: i for i, v in enumerate(people)}
        args = []
        for vs, tab in self.factors:
            args += [tab, [local[v] for v in vs]]
        args.append([local[v] for v in query])
        table = np.einsum(*args, optimize="greedy")
        return table / table.sum()

    def joint_bruteforce(self) -> np.ndarray:
        """Full joint posterior by direct enumeration. Only for small test pedigrees."""
        n = len(self.family.people)
        if n > 13:
            raise ValueError("brute-force joint is limited to 13 people")
        _, table = _contract(self.factors, list(range(n)))
        return table / table.sum()
