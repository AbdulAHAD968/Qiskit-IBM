# Judge question bank

Short answers with the numbers behind them. Full tables: [BENCHMARKS.md](BENCHMARKS.md).

**Why quantum, when a classical solver handles this size?**
At our sizes it does, and we say so. The project shows a problem whose structure QAOA represents
directly (one ZZ rotation per couple link, the kit limit built into the circuit) and measures how
close it gets to exact answers.

**Did quantum beat classical?**
No. Brute force finds the best plan instantly, and simulated annealing found it in 100% of the
10-qubit and 92% of the 16-qubit families. Constrained QAOA beats the field officer's rule and
random picks: quality 0.50 against 0.27 and 0.24 on 16 qubits at depth 3.

**What is new here?**
The problem framing and the weights derived from genetics: an exact pedigree engine that turns a
family tree into pair weights. The constrained QAOA method is borrowed from Cook, Eidenbenz and
Baertschi and credited. We found no earlier quantum work on cascade screening; two searches cannot
prove there is none.

**Why not simply test the closest relatives?**
Because the value sits on couples. The rule "test the highest carrier probabilities" missed the
best plan in 98% of 10-relative families and 100% of 16-relative families, and reached 45% and 35%
of the best value. Breaking every tie in carrier probability in the rule's favour does not rescue
it: 48% and 38%, with the same miss rates. The rule is our stand-in for an unaided choice, not a
documented programme protocol.

**Why not test one partner first and the other only if positive?**
That is sensible when results return quickly. Our model covers the single-visit case. Step-by-step
testing is listed as a limitation and as the next model.

**How are the probabilities computed?**
By Mendel's rules on the family tree, given the affected child and a 5% population carrier rate.
The tree is a Bayesian network; marginals come from exact variable elimination, which also handles
loops from cousin marriages. The engine reproduces textbook values (parents 1, unaffected sibling
2/3, grandparent (1+q)/2 = 0.513, uncle 2/(4-q) = 0.503) and matches full enumeration of 3^10
genotype assignments.

**Is the data real?**
No. Families are synthetic and seeded. Carriers among testable relatives average 36% against 31%
in the 2002 study. No patient data is used.

**What keeps the answer at exactly k tests?**
The start state is a Dicke state with exactly k ones, and every mixer gate (XX+YY rotation) only
swaps a one with a zero. A test confirms no probability leaves the valid plans. On a noisy device
some shots break this, so we discard them and report how many survive.

**How is the Dicke state built?**
From gates, with the deterministic scheme of Baertschi and Eidenbenz: order k*n gates and no helper
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
Three tests: the Ising form equals the objective for every one of the 2^n inputs; the Estimator
energy of each basis state equals the objective; the cost layer is the diagonal matrix
exp(-i*gamma*F) up to a global phase.

**Is the problem hard?**
With equal weights it is densest-k-subgraph, which is NP-hard, and the best known efficient
algorithm guarantees only about n^(1/4). That is a worst-case statement. Our family graphs are
sparse and split into small components, so these instances are easy for an exact dynamic programme.
We say so in the report.

**Is ranking relatives by genetic risk dangerous?**
It can be. The tool uses synthetic data, treats consent as an input, publishes no individual
scores, and is meant to support a counsellor's plan for one visit.

**How reproducible is it?**
Pinned requirements, fixed seeds, saved JSON results, 47 tests, and scripts that regenerate every
figure, the website data and the report. The full matrix takes about 8 minutes on 8 processes.
