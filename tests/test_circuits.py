"""Circuit checks: Dicke state, kit-conserving mixer, and energy = objective."""
from math import comb

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import Operator, Statevector

from kinship.classical import feasible_table
from kinship.pedigree import generate_family
from kinship.problem import build_problem
from kinship.quantum.circuits import (
    constrained_qaoa_circuit, cost_layer, dicke_state, penalty_qaoa_circuit, scaled_ising, xy_ring_mixer,
)
from kinship.quantum.qaoa import QAOA, append_zero_start, distribution_metrics, interp_start


@pytest.fixture(scope="module")
def small():
    return build_problem(generate_family(11, n_candidates=6), k=2, name="test-6")


@pytest.mark.parametrize("n,k", [(2, 1), (3, 1), (4, 2), (5, 2), (6, 3), (7, 3), (8, 4), (9, 2), (10, 4)])
def test_dicke_circuit_prepares_the_dicke_state(n, k):
    probs = Statevector(dicke_state(n, k)).probabilities()
    amps = Statevector(dicke_state(n, k)).data
    weight = np.array([bin(i).count("1") for i in range(1 << n)])
    assert probs[weight != k].sum() == pytest.approx(0.0, abs=1e-12)
    assert probs[weight == k] == pytest.approx(1.0 / comb(n, k), abs=1e-12)
    # equal amplitudes, not only equal probabilities
    inside = amps[weight == k]
    assert np.allclose(inside, inside[0], atol=1e-10)


@pytest.mark.parametrize("n", [3, 4, 5, 6])
def test_xy_mixer_conserves_hamming_weight(n):
    unitary = Operator(xy_ring_mixer(n, 0.37)).data
    weight = np.array([bin(i).count("1") for i in range(1 << n)])
    leak = np.abs(unitary[weight[:, None] != weight[None, :]])
    assert leak.max() == pytest.approx(0.0, abs=1e-12)


def test_cost_layer_is_the_objective_as_a_phase(small):
    a, b, _, scale = scaled_ising(small.qubo())
    gamma = 0.83
    diag = np.diag(Operator(cost_layer(small.n, a, b, gamma)).data)
    values = small.qubo().all_values()
    _, _, const = small.qubo().ising()
    expected = np.exp(-1j * gamma * (values - const) / scale)
    ratio = diag / expected
    assert np.allclose(ratio, ratio[0], atol=1e-9)      # equal up to one global phase


def test_circuit_energy_equals_objective_for_every_input(small):
    """Estimator energy of each basis state equals the objective of that plan."""
    qubo = small.qubo()
    _, _, const = qubo.ising()
    op = qubo.operator(scale=1.0)
    estimator = StatevectorEstimator()
    pubs = []
    for mask in range(1 << small.n):
        qc = QuantumCircuit(small.n)
        for i in range(small.n):
            if (mask >> i) & 1:
                qc.x(i)
        pubs.append((qc, op))
    result = estimator.run(pubs).result()
    for mask in range(1 << small.n):
        energy = float(result[mask].data.evs) + const
        assert energy == pytest.approx(small.value(small.mask_to_x(mask)), abs=1e-9)


@pytest.mark.parametrize("reps", [1, 2])
def test_constrained_qaoa_only_outputs_plans_with_exactly_k_kits(small, reps):
    qc, _ = constrained_qaoa_circuit(small, reps)
    rng = np.random.default_rng(reps)
    bound = qc.assign_parameters(rng.uniform(-2, 2, qc.num_parameters))
    probs = Statevector(bound).probabilities()
    weight = np.array([bin(i).count("1") for i in range(1 << small.n)])
    assert probs[weight == small.k].sum() == pytest.approx(1.0, abs=1e-10)


def test_penalty_qaoa_can_break_the_kit_limit(small):
    qc, _ = penalty_qaoa_circuit(small, 1)
    probs = Statevector(qc.assign_parameters([0.4, 0.3])).probabilities()
    weight = np.array([bin(i).count("1") for i in range(1 << small.n)])
    assert probs[weight != small.k].sum() > 0.05


def test_estimator_expectation_matches_exact_distribution(small):
    engine = QAOA(small, "constrained", reps=1)
    theta = np.array([0.6, 0.9])
    probs = engine.probabilities(theta)
    exact = float(probs @ small.qubo().all_values())
    assert float(engine.expectation(theta)[0]) == pytest.approx(exact, abs=1e-8)


def test_sampler_counts_use_the_same_bit_convention(small):
    engine = QAOA(small, "constrained", reps=1)
    theta = np.array([0.6, 0.9])
    counts = engine.sample(theta, shots=2000, seed=1)
    assert all(bin(mask).count("1") == small.k for mask in counts)
    probs = engine.probabilities(theta)
    top = max(counts, key=counts.get)
    assert probs[top] > 1.0 / comb(small.n, small.k) * 0.5


def test_training_beats_random_and_warm_start_never_loses(small):
    table = feasible_table(small)
    d1 = QAOA(small, "constrained", reps=1)
    run1 = d1.train(maxiter=60)
    m1 = distribution_metrics(d1.probabilities(run1.angles), table)
    assert m1["valid_share"] == pytest.approx(1.0, abs=1e-9)
    assert run1.expectation > table.mean

    d2 = QAOA(small, "constrained", reps=2)
    start = append_zero_start(np.array(run1.angles))
    assert float(d2.expectation(start)[0]) == pytest.approx(run1.expectation, abs=1e-8)
    run2 = d2.train(warm=np.array(run1.angles), maxiter=60)
    assert run2.expectation >= run1.expectation - 1e-8
    assert len(interp_start(np.array(run1.angles))) == 4
