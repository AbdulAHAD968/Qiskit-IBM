"""Linked families: split the network along the couple graph, then share out the kits.

One qubit per relative limits a single circuit to roughly 25 to 30 people on a
simulator. The objective, however, only ties two people together when they
form a couple. People in different connected components of the couple graph
interact through the kit budget alone, so a large network splits exactly:

1. find the connected components of the couple graph (relatives with no
   couple link go into one pool that is solved by sorting);
2. for every component and every budget b, find the best plan with b kits
   (this is where QAOA is used, on as many qubits as the component has people);
3. a small dynamic programme splits the total number of kits.

If a component is larger than the qubit limit, its weakest links are cut until
it fits. The cut weight is reported, and the final plan is always scored on the
full objective.
"""
from __future__ import annotations

import numpy as np

from .problem import ScreeningProblem


def _components(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in edges:
        parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for v in range(n):
        groups.setdefault(find(v), []).append(v)
    return sorted(groups.values(), key=lambda g: g[0])


def couple_components(problem: ScreeningProblem, max_size: int | None = None):
    """Return (components with at least two people, isolated people, weight of cut links)."""
    weights = problem.w * problem.c
    alive = [t for t in range(len(problem.edges)) if weights[t] > 0]
    while True:
        comps = _components(problem.n, [problem.edges[t] for t in alive])
        largest = max(comps, key=len)
        if max_size is None or len(largest) <= max_size:
            break
        inside = [t for t in alive if problem.edges[t][0] in largest]
        weakest = min(inside, key=lambda t: weights[t])
        alive.remove(weakest)
    # Only links between different final components are really lost: a removed
    # link whose two ends stay together is kept by ScreeningProblem.restrict.
    member = {v: ci for ci, comp in enumerate(comps) for v in comp}
    cut = float(sum(weights[t] for t, (i, j) in enumerate(problem.edges) if member[i] != member[j]))
    return [c for c in comps if len(c) > 1], [c[0] for c in comps if len(c) == 1], cut


def largest_component(problem: ScreeningProblem) -> int:
    comps, _, _ = couple_components(problem)
    return max((len(c) for c in comps), default=1)


def split_budget(values: list[list[float]], total: int) -> tuple[list[int], float]:
    """Dynamic programme: values[c][b] is the best value of block c with b kits."""
    n_blocks = len(values)
    best = np.full((n_blocks + 1, total + 1), -np.inf)
    choice = np.zeros((n_blocks + 1, total + 1), dtype=int)
    best[0, 0] = 0.0
    for c in range(1, n_blocks + 1):
        for t in range(total + 1):
            for b in range(min(t, len(values[c - 1]) - 1) + 1):
                cand = best[c - 1, t - b] + values[c - 1][b]
                if cand > best[c, t]:
                    best[c, t] = cand
                    choice[c, t] = b
    budgets, t = [], total
    for c in range(n_blocks, 0, -1):
        budgets.append(int(choice[c, t]))
        t -= budgets[-1]
    return budgets[::-1], float(best[n_blocks, total])


def pool_values(problem: ScreeningProblem, singles: list[int], total: int):
    """Best value and plan for the people without couple links: take the largest single terms."""
    order = sorted(singles, key=lambda i: -problem.h[i])
    values = [0.0]
    for b in range(1, min(len(order), total) + 1):
        values.append(values[-1] + float(problem.h[order[b - 1]]))
    return values, order
