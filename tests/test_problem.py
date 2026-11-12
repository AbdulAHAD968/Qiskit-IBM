"""Objective, exactly-k rule, Ising mapping and the classical references."""
import numpy as np
import pytest

from kinship.classical import (
    brute_force, feasible_table, field_rule, greedy, milp_exact, relevance_rule, simulated_annealing,
)
from kinship.pedigree import generate_family
from kinship.problem import build_problem, make_instance


@pytest.fixture(scope="module")
def small():
    return build_problem(generate_family(11, n_candidates=7), k=3, name="test-7")


def test_instance_has_requested_size():
    for seed in range(5):
        prob = build_problem(generate_family(seed, n_candidates=10), k=4)
        assert prob.n == 10 and len(prob.p) == 10
        assert np.all((prob.p >= 0) & (prob.p <= 1))
        assert np.all((prob.w >= 0) & (prob.w <= 1))


def test_generation_is_deterministic():
    a, b = make_instance("S", 3), make_instance("S", 3)
    assert a.to_dict() == b.to_dict()


def test_objective_counts_a_couple_only_when_both_are_tested(small):
    i, j = small.edges[0]
    one = np.zeros(small.n, dtype=int)
    one[i] = 1
    both = one.copy()
    both[j] = 1
    assert small.couples_found(one) == 0.0
    assert small.couples_found(both) == pytest.approx(small.w[0] * small.c[0])


def test_ising_form_equals_objective_for_every_input(small):
    qubo = small.qubo()
    a, b, const = qubo.ising()
    values = qubo.all_values()
    for mask in range(1 << small.n):
        x = small.mask_to_x(mask)
        z = 1 - 2 * x
        ising = const + a @ z + sum(c * z[i] * z[j] for (i, j), c in b.items())
        assert ising == pytest.approx(small.value(x), abs=1e-12)
        assert values[mask] == pytest.approx(small.value(x), abs=1e-12)


def test_operator_diagonal_equals_objective(small):
    qubo = small.qubo()
    _, _, const = qubo.ising()
    diag = np.real(np.diag(qubo.operator(scale=2.5).to_matrix()))
    assert 2.5 * diag + const == pytest.approx(qubo.all_values(), abs=1e-10)


def test_penalty_keeps_feasible_values_and_never_rewards_cheating(small):
    pen = small.penalty_qubo()
    values = pen.all_values()
    table = feasible_table(small)
    assert values[table.masks] == pytest.approx(table.values, abs=1e-10)
    assert int(np.argmax(values)) in set(int(m) for m in table.optimal_masks())


def test_brute_force_agrees_with_integer_program():
    for index in range(4):
        prob = make_instance("S", index)
        _, best = brute_force(prob)
        x, value, info = milp_exact(prob)
        assert info["proven_optimal"]
        assert prob.is_feasible(x)
        assert value == pytest.approx(best, abs=1e-9)


def test_heuristics_return_valid_plans(small):
    rng = np.random.default_rng(0)
    table = feasible_table(small)
    for x in (field_rule(small), relevance_rule(small), greedy(small), simulated_annealing(small, rng)):
        assert small.is_feasible(x)
        assert small.value(x) <= table.best + 1e-12


def test_restrict_keeps_internal_links_only(small):
    idx = [0, 1, 2, 3]
    sub = small.restrict(idx, k=2)
    assert sub.n == 4
    for (i, j) in sub.edges:
        assert 0 <= i < j < 4
