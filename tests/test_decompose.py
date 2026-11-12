"""Decomposition along the couple graph, the budget split, and the trade-off helpers."""
from itertools import product

import numpy as np
import pytest

from kinship.classical import feasible_table, milp_exact
from kinship.decompose import couple_components, pool_values, split_budget
from kinship.evaluate import _hypervolume, _pareto
from kinship.problem import ScreeningProblem, make_instance


def toy(n, k, edges, weights):
    return ScreeningProblem(
        name="toy", n=n, k=k, lam=1.0, p=np.full(n, 0.1), r=np.ones(n), edges=edges,
        w=np.array(weights, dtype=float), c=np.ones(len(edges)), kinds=["married"] * len(edges),
        labels=[f"P{i}" for i in range(n)], person_ids=list(range(n)),
    )


def test_split_budget_matches_enumeration():
    values = [[0.0, 1.0, 1.5], [0.0, 0.2, 2.0, 2.1], [0.0, 0.9]]
    total = 4
    budgets, best = split_budget(values, total)
    brute = max(
        sum(v[b] for v, b in zip(values, combo))
        for combo in product(*(range(len(v)) for v in values)) if sum(combo) == total
    )
    assert sum(budgets) == total
    assert best == pytest.approx(brute)
    assert sum(v[b] for v, b in zip(values, budgets)) == pytest.approx(brute)


def test_components_split_the_couple_graph():
    prob = toy(6, 2, [(0, 1), (1, 2), (4, 5)], [0.3, 0.2, 0.4])
    comps, singles, cut = couple_components(prob)
    assert comps == [[0, 1, 2], [4, 5]]
    assert singles == [3]
    assert cut == 0.0


def test_cut_weight_counts_only_links_between_final_components():
    # Triangle 0-1-2 with a tail 2-3. With at most three people per component the tail is cut.
    # The weakest link of the triangle is removed first but both its ends stay together,
    # so it is not lost and must not be counted.
    prob = toy(4, 2, [(0, 1), (1, 2), (0, 2), (2, 3)], [0.1, 0.5, 0.5, 0.2])
    comps, singles, cut = couple_components(prob, max_size=3)
    assert comps == [[0, 1, 2]]
    assert singles == [3]
    assert cut == pytest.approx(0.2)
    assert len(prob.restrict(comps[0], 2).edges) == 3


def test_exact_decomposition_equals_the_integer_programme():
    prob = make_instance("L", 0)
    comps, singles, cut = couple_components(prob, max_size=14)
    assert cut == 0.0
    tables = []
    for comp in comps:
        values = [0.0]
        for budget in range(1, min(len(comp), prob.k) + 1):
            values.append(feasible_table(prob.restrict(comp, budget)).best)
        tables.append(values)
    pool, _ = pool_values(prob, singles, prob.k)
    budgets, value = split_budget(tables + [pool], prob.k)
    _, exact, info = milp_exact(prob)
    assert info["proven_optimal"]
    assert sum(budgets) == prob.k
    assert value == pytest.approx(exact, abs=1e-9)


def test_pareto_front_and_hypervolume_on_a_hand_example():
    points = np.array([[3.0, 1.0], [2.0, 2.0], [1.0, 3.0], [1.0, 1.0], [2.0, 1.5]])
    assert sorted(_pareto(points).tolist()) == [0, 1, 2]
    # area dominated from the origin: 3*1 + 2*(2-1) + 1*(3-2)
    assert _hypervolume(points) == pytest.approx(6.0)
