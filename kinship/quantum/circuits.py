"""Circuits for the two QAOA variants.

Constrained QAOA (main method)
    start state   Dicke state |D^n_k>: equal superposition of every plan that
                  uses exactly k kits, built from gates with the deterministic
                  scheme of Baertschi and Eidenbenz (O(kn) gates, no ancillas).
    cost layer    RZZ on every couple link, RZ on every relative.
    mixer         ring of XX+YY rotations. Each one swaps a tested and an
                  untested relative, so the number of kits never changes.

Penalty QAOA (baseline)
    start state   uniform superposition over all 2^n bitstrings.
    cost layer    objective minus A * (sum_i x_i - k)^2, which needs a ZZ
                  rotation on every pair of qubits.
    mixer         RX on every qubit.

The Dicke-state and XY-mixer design follows Cook, Eidenbenz and Baertschi,
"The Quantum Alternating Operator Ansatz on Maximum k-Vertex Cover" (2020).
The circuits here are written from the papers, not copied from any code base.
"""
from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.circuit.library import XXPlusYYGate

from ..problem import Qubo, ScreeningProblem


# --------------------------------------------------------------------------
# Dicke state
# --------------------------------------------------------------------------
def _ccry(qc: QuantumCircuit, theta: float, c1: int, c2: int, target: int) -> None:
    """Doubly-controlled RY from four CNOTs, using X RY(a) X = RY(-a)."""
    qc.ry(theta / 4, target)
    qc.cx(c1, target)
    qc.ry(-theta / 4, target)
    qc.cx(c2, target)
    qc.ry(theta / 4, target)
    qc.cx(c1, target)
    qc.ry(-theta / 4, target)
    qc.cx(c2, target)


def _split_cyclic_shift(qc: QuantumCircuit, n: int, k: int, first: int) -> None:
    """SCS_{n,k} block of Baertschi and Eidenbenz on qubits first .. first+k.

    For every l <= k it maps |0..0 1^l> to
    sqrt(l/n) |0..0 1^l> + sqrt((n-l)/n) |0..0 1^l 0>, i.e. it decides whether
    the last qubit of the block keeps its excitation.
    """
    last = first + k
    qc.cx(last - 1, last)
    qc.cry(2.0 * np.arccos(np.sqrt(1.0 / n)), last, last - 1)
    qc.cx(last - 1, last)
    for l in range(2, k + 1):
        qc.cx(last - l, last)
        _ccry(qc, 2.0 * np.arccos(np.sqrt(l / n)), last, last - l + 1, last - l)
        qc.cx(last - l, last)


def dicke_state(n: int, k: int) -> QuantumCircuit:
    """Prepare |D^n_k> from |0...0> using O(kn) gates and no ancilla qubits."""
    if not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n")
    qc = QuantumCircuit(n, name=f"Dicke({n},{k})")
    if k == 0:
        return qc
    qc.x(range(n - k, n))
    if k == n:
        return qc
    for l in range(n, k, -1):                 # blocks SCS_{l,k}, widest register first
        _split_cyclic_shift(qc, l, k, first=l - k - 1)
    for l in range(k, 1, -1):                 # blocks SCS_{l,l-1} on the first l qubits
        _split_cyclic_shift(qc, l, l - 1, first=0)
    return qc


# --------------------------------------------------------------------------
# Layers
# --------------------------------------------------------------------------
def ring_pairs(n: int) -> list[tuple[int, int]]:
    """Neighbouring pairs of a ring, ordered so that each sub-layer is parallel."""
    if n < 2:
        return []
    pairs = [(i, i + 1) for i in range(0, n - 1, 2)] + [(i, i + 1) for i in range(1, n - 1, 2)]
    if n > 2:
        pairs.append((n - 1, 0))
    return pairs


def xy_ring_mixer(n: int, beta) -> QuantumCircuit:
    """Parity-ordered XY ring mixer: exp(-i beta (XX+YY)/2) on each ring pair.

    Every gate conserves the Hamming weight, so the layer can never change the
    number of kits used.
    """
    qc = QuantumCircuit(n, name="XY ring")
    for a, b in ring_pairs(n):
        qc.append(XXPlusYYGate(2.0 * beta), [a, b])
    return qc


def cost_layer(n: int, a: np.ndarray, b: dict, gamma) -> QuantumCircuit:
    """exp(-i gamma H) for H = sum_i a_i Z_i + sum_{i<j} b_ij Z_i Z_j."""
    qc = QuantumCircuit(n, name="cost")
    for (i, j), coef in b.items():
        if abs(coef) > 1e-12:
            qc.rzz(2.0 * gamma * coef, i, j)
    for i in range(n):
        if abs(a[i]) > 1e-12:
            qc.rz(2.0 * gamma * a[i], i)
    return qc


def scaled_ising(qubo: Qubo):
    """Ising coefficients divided by their RMS, so that angles are of order one."""
    a, b, const = qubo.ising()
    coefs = np.array([*a, *b.values()], dtype=float)
    coefs = coefs[np.abs(coefs) > 1e-12]
    scale = float(np.sqrt(np.mean(coefs ** 2))) if coefs.size else 1.0
    return a / scale, {key: v / scale for key, v in b.items()}, const, scale


# --------------------------------------------------------------------------
# Full ansatz circuits
# --------------------------------------------------------------------------
def constrained_qaoa_circuit(problem: ScreeningProblem, reps: int, initial: str = "dicke"):
    """Dicke start, cost layers on the couple graph, XY ring mixers.

    ``initial`` may be "dicke" or "field" (start from the field officer's plan,
    which costs only k X gates). Returns the circuit and the Ising scale.
    """
    n = problem.n
    a, b, _, scale = scaled_ising(problem.qubo())
    gamma = ParameterVector("gamma", reps)
    beta = ParameterVector("beta", reps)
    qc = QuantumCircuit(n, name=f"constrained-QAOA(p={reps})")
    if initial == "dicke":
        qc.compose(dicke_state(n, problem.k), inplace=True)
    elif initial == "field":
        from ..classical import field_rule

        for i in np.flatnonzero(field_rule(problem)):
            qc.x(int(i))
    else:
        raise ValueError(f"unknown initial state {initial!r}")
    for layer in range(reps):
        qc.compose(cost_layer(n, a, b, gamma[layer]), inplace=True)
        qc.compose(xy_ring_mixer(n, beta[layer]), inplace=True)
    return qc, scale


def penalty_qaoa_circuit(problem: ScreeningProblem, reps: int, penalty: float | None = None):
    """Standard QAOA on the penalised objective. Returns the circuit and the Ising scale."""
    n = problem.n
    a, b, _, scale = scaled_ising(problem.penalty_qubo(penalty))
    gamma = ParameterVector("gamma", reps)
    beta = ParameterVector("beta", reps)
    qc = QuantumCircuit(n, name=f"penalty-QAOA(p={reps})")
    qc.h(range(n))
    for layer in range(reps):
        qc.compose(cost_layer(n, a, b, gamma[layer]), inplace=True)
        for q in range(n):
            qc.rx(2.0 * beta[layer], q)
    return qc, scale
