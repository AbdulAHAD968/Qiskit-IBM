"""Noise study on a simulator.

No real quantum processor was used in this project. The numbers produced here
come from Qiskit Aer with a simple, explicit noise model:

* depolarising error ``e2`` after every two-qubit CZ gate,
* depolarising error ``e2 / 10`` after every SX or X gate (RZ is virtual),
* symmetric readout error ``2 * e2`` on every qubit.

Circuits are first transpiled to the basis {RZ, SX, X, CZ}. The noise turns
some shots into plans that do not use exactly k kits. Those shots are thrown
away and the surviving share is reported.
"""
from __future__ import annotations

from qiskit import transpile
from qiskit.transpiler import CouplingMap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

BASIS = ["rz", "sx", "x", "cz"]


def make_noise_model(e2: float) -> NoiseModel | None:
    if e2 <= 0:
        return None
    model = NoiseModel(basis_gates=BASIS)
    model.add_all_qubit_quantum_error(depolarizing_error(e2 / 10.0, 1), ["sx", "x"])
    model.add_all_qubit_quantum_error(depolarizing_error(e2, 2), ["cz"])
    ro = min(2.0 * e2, 0.5)
    model.add_all_qubit_readout_error(ReadoutError([[1 - ro, ro], [ro, 1 - ro]]))
    return model


def hardware_circuit(logical, line: bool = False, seed: int = 1):
    """Transpile to the {RZ, SX, X, CZ} basis, all-to-all or on a line of qubits."""
    coupling = CouplingMap.from_line(logical.num_qubits) if line else None
    return transpile(logical, basis_gates=BASIS, coupling_map=coupling,
                     optimization_level=3, seed_transpiler=seed)


def resources(logical, line: bool = False, seed: int = 1) -> dict:
    tq = hardware_circuit(logical, line, seed)
    ops = tq.count_ops()
    return {"depth": int(tq.depth()), "two_qubit": int(ops.get("cz", 0)),
            "two_qubit_depth": int(tq.depth(lambda inst: inst.operation.num_qubits == 2)),
            "gates": int(sum(v for k, v in ops.items() if k not in ("measure", "barrier")))}


def noisy_counts(logical, e2: float, shots: int = 4096, seed: int = 0, line: bool = False) -> dict[int, int]:
    """Sample a bound logical circuit under the noise model. Returns {mask: count}."""
    qc = logical.copy()
    qc.measure_all()
    tq = hardware_circuit(qc, line, seed=1)
    model = make_noise_model(e2)
    if model is None:
        backend = AerSimulator(method="statevector", max_parallel_threads=1)
    else:
        backend = AerSimulator(method="density_matrix", noise_model=model, max_parallel_threads=1)
    counts = backend.run(tq, shots=shots, seed_simulator=seed).result().get_counts()
    return {int(bits, 2): c for bits, c in counts.items()}
