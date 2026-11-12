# Judge question bank

Short answers with the numbers behind them. Full tables: [BENCHMARKS.md](BENCHMARKS.md).

**Why quantum, when a classical solver handles this size?**
At our sizes it does, and we say so. The project shows a problem whose structure QAOA represents
directly (one ZZ rotation per couple link, the kit limit built into the circuit) and measures how
close it gets to exact answers.

**Did quantum beat classical?**
No. Brute force finds the best plan instantly, and simulated annealing found it in 100% of the
10-qubit and 92% of the 16-qubit families. A simple greedy heuristic reaches quality 0.78 on 16
qubits. Constrained QAOA beats the field officer's rule and random picks, not those: quality 0.50
against 0.27 and 0.24 on 16 qubits at depth 3.

**"32 times more often than random": is that a mean or a median?**
A mean of per-family ratios at 16 qubits and depth 3. The median is 14 and the families range from
5 to 116 times, so a few families carry the mean. At 10 qubits the mean is 12, the median 8 and the
range 1 to 41 times.

**Does a deeper circuit always help?**
For expected value, yes in our runs: quality did not fall from one depth to the next in any family,
because each depth starts from the angles of the one below. For the chance of the single best plan,
no: from depth 2 to depth 3 it falls in 9 of the 20 ten-qubit families and 2 of the 12 sixteen-qubit
families. The 10-qubit median goes from 4.6% to 4.2% while the mean rises from 4.6% to 5.9%. The
angles are tuned for expected value, not for that chance.

**What is new here?**
The problem framing and the weights derived from genetics: an exact pedigree engine that turns a
family tree into pair weights. The constrained QAOA method is borrowed from Cook, Eidenbenz and
Bärtschi and credited. We found no earlier quantum work on cascade screening; two searches cannot
prove there is none.

**Why not simply test the closest relatives?**
Because the value sits on couples. The rule "test the highest carrier probabilities" missed the
best plan in 98% of 10-relative families and 100% of 16-relative families, and reached 45% and 35%
of the best value. Breaking every tie in carrier probability in the rule's favour does not rescue
it: 48% and 38%, with the same miss rates. The rule is our stand-in for an unaided choice, not a
documented programme protocol.

**Why does a single negative test earn nothing in your objective?**
The objective counts confirmed at-risk couples, and confirming one needs both tests. A single
negative test does rule a couple out, which has real value, but valuing it belongs to the
step-by-step model where one result updates the next choice. We list that as a limitation.

**Why not test one partner first and the other only if positive?**
That is sensible when results return quickly. Our model covers the single-visit case. Step-by-step
testing is listed as a limitation and as the next model.

**How are the probabilities computed?**
By Mendel's rules on the family tree, given the affected child and a 5% population carrier rate.
The tree is a Bayesian network; marginals come from exact variable elimination, which also handles
loops from cousin marriages. The engine reproduces textbook values (parents 1, unaffected sibling
2/3, grandparent (1+q)/2 = 0.513, uncle 2/(4-q) = 0.503) and matches full enumeration of 3^10
genotype assignments. An independent Monte Carlo gene-dropping simulation
(`python -m kinship.validate_genetics`) agrees with it within sampling error.

**Is the data real?**
No. Families are synthetic and seeded. Carriers among testable relatives average 36% against 31%
in the 2002 study. No patient data is used.

**What keeps the answer at exactly k tests?**
The start state is a Dicke state with exactly k ones, and every mixer gate (XX+YY rotation) only
swaps a one with a zero. A test confirms no probability leaves the valid plans. On a noisy device
some shots break this, so we discard them and report how many survive.

**How is the Dicke state built?**
From gates, with the deterministic scheme of Bärtschi and Eidenbenz: order k*n gates and no helper
qubits. Qiskit 2.6 has no built-in version. It costs 144 CZ gates for 10 qubits and 4 kits, and 330
for 16 qubits and 5 kits, after transpilation.

**Why is penalty QAOA so much worse?**
The penalty term dominates the cost function, so the optimiser first learns the constraint. At
depth 3 on 16 qubits only 61% of its shots are valid and their quality is 0.26, against 0.24 for a
random valid plan. It also needs a ZZ rotation on every pair of qubits: 240 CZ gates per layer at 16
qubits against 46 for the constrained circuit.

**What happens on a real chip?**
We did not run on one. In an Aer noise model, at 0.1% two-qubit error 86% of constrained shots stay
valid and the chance of the best plan drops from 2.4% to 2.0%. At 1% error 37% stay valid and the
chance of the best plan is at the random level.

**How does it scale?**
One qubit per relative; a simulator reaches roughly 25 to 30 people. Larger networks split exactly
along connected components of the couple graph: networks of 48 relatives and 12 kits were solved to
the proven optimum with circuits of at most 9 qubits and a dynamic programme that shares out the
kits. The honest caveat: at that component size sampling finds each optimum easily.

**Is the quantum part doing real work?**
Yes. The plan handed to the field officer is a measured bitstring from the circuit, and the angles
are tuned on expectation values from the Estimator primitive. Remove the circuit and the method
samples valid plans uniformly: quality 0.24 instead of 0.50 on 16 qubits.

**How do you know the mapping is correct?**
Four tests: the Ising form equals the objective for every one of the 2^n inputs; the Estimator
energy of each basis state equals the objective; the cost layer is the diagonal matrix
exp(-i*gamma*F) up to a global phase and the scale factor; and a plain NumPy simulation of the whole
ansatz, sharing no circuit code, reproduces the probabilities of the Qiskit circuit.

**Is the live circuit on the website Qiskit?**
No. A browser cannot run Qiskit, so `web/qaoa-sim.js` re-implements both circuits in JavaScript:
the constrained one inside the 210 valid plans of the demonstration family, the penalty one on all
1,024 bitstrings. `python -m kinship.validate_web_sim` runs that file under Node.js and compares it
with the Qiskit circuits: at trained and random angles for depths 1 to 3 every outcome probability
agrees to within 1e-15. When a visitor marks relatives as absent or changes the kits, the page tunes
the angles itself with the recipe of the Python code (Nelder-Mead in place of COBYLA); on the full
family that recipe reaches Qiskit's result within 0.01 percentage points. Every number in the
report comes from the Qiskit code.

**Is the problem hard?**
With equal weights it is densest-k-subgraph, which is NP-hard, and the best known efficient
algorithm guarantees only about n^(1/4). That is a worst-case statement. Our family graphs are
sparse and split into small components, so these instances are easy for an exact dynamic programme.
We say so in the report.

**Is ranking relatives by genetic risk dangerous?**
It can be. The tool uses synthetic data, treats consent as an input, publishes no individual
scores, and is meant to support a counsellor's plan for one visit.

**How reproducible is it?**
Pinned requirements, fixed seeds, saved JSON results, 57 tests, and scripts that regenerate every
figure, the website data and the report. The full matrix takes about 8 minutes on 8 processes. A
second full run in a fresh clone reproduced every value; see [REPRODUCIBILITY.md](REPRODUCIBILITY.md).
That check was on one machine, so it says nothing about other platforms.
