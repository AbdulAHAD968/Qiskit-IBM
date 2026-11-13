# Kinship: pitch book

Qiskit Fall Fest 2026, final round. What to say, what to show, and how to answer the hard questions.

[Live site](https://kinship.sevenlabs.site/) | [GitHub repo](https://github.com/AbdulAHAD968/Qiskit-IBM) | [Video](https://drive.google.com/file/d/11Vun5EijHmykErL0_m3xQiPCX5_Lap2u/view?usp=sharing)

## The one-line pitch

> A child is diagnosed with thalassaemia. A field officer has four test kits for the family. Our tool picks the relatives to test, using a QAOA circuit that can never break the kit limit, and checks every plan against the exact optimum.

**Our honest position:** we do not claim a speedup. We show a real problem that QAOA represents directly, a circuit that cannot break the kit limit, and an honest comparison against exact answers.

## The main point

Say these three things, in this order, and everything else supports them.

1. **The problem is real and it is about pairs.** In cascade screening, a test only confirms an at-risk couple when both partners are tested. So choosing who to test is a choice of pairs under a fixed number of kits, and the obvious rule (test the likeliest carriers) gets it wrong in 98% of our families.
2. **That problem is exactly what QAOA is built for.** Yes-or-no decisions with values on pairs map one to one onto qubits and ZZ rotations. The kit limit is enforced by the circuit itself, so every single shot is a usable plan.
3. **We checked every answer.** Every plan the circuit gives is compared with the exact optimum, simple rules, strong classical heuristics and noise. QAOA beats random picks and the field rule, and we say plainly that classical solvers still win at this size.

## The technical aspect, explained

Use the short version in the pitch. Use the full version when a judge asks "how exactly does it work?".

**Short version (30 seconds):**

> We turn the family tree into exact pair weights with a Bayesian genetics engine. The objective becomes an Ising Hamiltonian, one ZZ term per couple. The circuit starts in a Dicke state with exactly k ones, applies the cost layer, then an XY mixer that only swaps a one with a zero, so the kit count never changes. COBYLA tunes the angles through the Qiskit Estimator, the Sampler gives 4,096 plans, and we keep the best one.

**Full version, step by step:**

1. **Family to probabilities (`kinship/genetics.py`).** The family tree is a Bayesian network over genotypes (AA, carrier, affected), one gene, Mendel's rules, founders at a 5% carrier rate. We condition on the affected child and compute every probability exactly by variable elimination, which also handles the loops that cousin marriages create. Output: each relative's carrier probability p<sub>i</sub>, and each couple's probability w<sub>ij</sub> that both are carriers. These are joint probabilities, not products: two grandparents are 51% each but only 2.6% together. Checked against textbook values, full enumeration, and an independent Monte Carlo simulation.

2. **Probabilities to an optimisation problem (`kinship/problem.py`).** A binary variable x<sub>i</sub> per relative. Maximise F(x) = Σ c<sub>ij</sub> w<sub>ij</sub> x<sub>i</sub> x<sub>j</sub> + λ Σ r<sub>i</sub> p<sub>i</sub> x<sub>i</sub> subject to Σ x<sub>i</sub> = k. The first term is the expected number of at-risk couples confirmed; c<sub>ij</sub> is the chance the couple is real (1 if married, lower for a possible future match); the second term is a small reward (λ = 0.05) for single carriers found. With equal weights this is densest-k-subgraph, which is NP-hard in general.

3. **Problem to a Hamiltonian.** Substitute x<sub>i</sub> = (1 − z<sub>i</sub>)/2, so qubit state |1⟩ means "test this relative". F becomes a constant plus Σ a<sub>i</sub> Z<sub>i</sub> + Σ b<sub>ij</sub> Z<sub>i</sub>Z<sub>j</sub>, with b<sub>ij</sub> = c<sub>ij</sub>w<sub>ij</sub>/4. Only couples get a ZZ term, so the circuit is as sparse as the family. Coefficients are divided by their root mean square so the angles are of order one. A test checks that this Hamiltonian equals F on every one of the 2<sup>n</sup> inputs.

4. **The start state (`kinship/quantum/circuits.py`).** A Dicke state |D<sup>n</sup><sub>k</sub>⟩: the equal superposition of all C(n, k) plans with exactly k kits (210 for 10 relatives and 4 kits). Qiskit has no built-in one, so we build it from gates with the deterministic scheme of Bärtschi and Eidenbenz: split-and-cyclic-shift blocks of CNOTs and controlled RY rotations, order k·n gates and no helper qubits. A test confirms it prepares the exact state.

5. **One QAOA layer.** The cost layer e<sup>−iγH</sup> is RZZ(2γb<sub>ij</sub>) on each couple and RZ(2γa<sub>i</sub>) on each relative: it changes only the phase of each plan, in proportion to its value. The mixer is a ring of `XXPlusYYGate` rotations applied in parity order. Each one moves amplitude between |01⟩ and |10⟩ on two neighbours, which preserves the number of ones, so the circuit never leaves the valid plans. Mixing turns those phase differences into probability: good plans grow, bad plans shrink. We repeat the layer p = 1, 2 or 3 times.

6. **Training and read-out (`kinship/quantum/qaoa.py`).** The Aer Estimator primitive returns the expected objective for given angles, and SciPy's COBYLA maximises it. Depth 1 starts from the best points of a 16 by 10 grid; deeper circuits start from the tuned shallower angles (the INTERP rule and an identity layer), so a deeper circuit never starts worse. The Aer Sampler then measures 4,096 shots; the best measured valid plan is the one handed to the field officer.

7. **The baseline it is compared with.** Standard penalty QAOA: start from all 2<sup>n</sup> bitstrings, RX mixer, and subtract A(Σx<sub>i</sub> − k)<sup>2</sup> with A = 1.1 × the largest gain of one extra test. The penalty needs a ZZ rotation on every pair of qubits (45 per layer for 10 qubits against 6 for ours) and the optimiser spends its effort on the constraint, so 39% of its shots break the kit limit at 16 qubits.

8. **How we judge every result (`kinship/classical.py`, `kinship/evaluate.py`).** The exact optimum by brute force (and an integer programme with HiGHS for large networks), plus the field rule, a relevance rule, greedy, simulated annealing and random valid plans. Three metrics: quality (expected value of a shot, scaled so the worst plan is 0 and the best is 1), the chance that one shot is the best plan, and the share of shots that use exactly k kits. Fixed seeds, 20 and 12 families, depths 1 to 3.

9. **Noise and scale (`kinship/quantum/noise.py`, `kinship/decompose.py`).** Circuits are transpiled to RZ, SX, X and CZ and run under a depolarising noise model; shots without exactly k ones are discarded and counted. For large linked families the couple graph splits into connected components that interact only through the kit budget: QAOA solves each component for each budget, and a dynamic programme shares out the kits exactly.

10. **The website (`web/qaoa-sim.js`).** A browser cannot run Qiskit, so the same two circuits are re-implemented in JavaScript (the constrained one inside the 210 valid plans, the penalty one on all 1,024 bitstrings). A script runs it under Node.js against the Qiskit circuit, and every probability agrees to 1e-15. Every number in the report comes from the Qiskit code.

**Who explains which part:** Saad takes steps 1 and 2 (the problem and the genetics), Abdul Ahad takes steps 3 to 7 (the quantum part), Faizan takes steps 8 to 10 (evaluation, noise, scale and the website).

## Talk track (about 4 minutes)

Saad opens and frames the problem, Abdul Ahad does the quantum method and the live demo, Faizan closes with results and limits.

### 1. The problem (40 s)

> About 5% of people in Pakistan carry beta-thalassaemia, and around 5,250 children are born with thalassaemia major each year. A child gets it only when both parents are carriers. Screening teams start from a family with an affected child and test the relatives, but kits and visits are limited: 48 field officers cover all 36 districts of Punjab.

> The key insight: an at-risk couple is only confirmed when both partners are tested. So the value of a plan sits on pairs of people. The obvious rule, test whoever is most likely to be a carrier, missed the best plan in 98% of our families.

### 2. The formulation (30 s)

> One yes-or-no decision per relative. Maximise the expected number of at-risk couples found, subject to exactly k tests. The weights come from an exact genetics engine on the family tree, cousin marriages included. That pairwise objective is exactly the form QAOA encodes.

### 3. The quantum method (50 s)

> One qubit per relative. We start in a Dicke state, an equal superposition of every plan with exactly four kits, built from gates because Qiskit has none built in. The cost layer puts one ZZ rotation on each couple link. The XY mixer swaps a tested and an untested relative, so the number of kits never changes. COBYLA tunes the angles through the Estimator, and the Sampler reads out plans.

> Standard penalty QAOA has to learn the kit rule: at 16 qubits only 61% of its shots use the right number of kits. Ours: 100%, by construction.

### 4. Live demo (60 s)

See the demo script below.

### 5. Results and limits (40 s)

> Against the exact optimum: on 16 qubits constrained QAOA reaches quality 0.50, against 0.24 for random and 0.27 for the field rule, and one shot is the best plan 32 times more often than a random pick on average. Every shot is valid. Linked families of 48 people are solved to the proven optimum with circuits of at most 9 qubits.

> What we do not claim: brute force solves these sizes in milliseconds, greedy reaches 0.78, and we ran on a simulator only. This is a method study on a new, real problem, checked honestly.

## Demo script

1. **Overview page.** Let the hero sit for 5 seconds: the family is measured live, each relative in superposition, then collapsing to one plan. Say: "Each of these is a real shot from the circuit."
2. **Scroll the hero.** Carrier probabilities fill each person. Then the field rule lights up: zero couples. Then the QAOA plan: two siblings and the two cousins they may marry, the exact optimum.
3. **Scroll the circuit scene.** 210 equal bars. Cost layer: colours fan out, heights stay. Mixer: good plans grow. End on 8.31%.
4. **Plan a visit page.** Tap Cousin 1 and Cousin 2 as absent. Point at the status line, then the new plan and its reason: the married aunt and uncle plus Cousin 3 and Sibling 3, still the exact optimum. Press + for 5 kits.
5. **Open "Explore the circuit".** Show the penalty comparison: shots that break the kit limit against 100% valid.
6. **Results page,** one tab only if asked.

**Backup:** if the site is slow, run `python -m kinship.demo`; it prints the same plan in about 20 seconds.

## Website map: what to open, and when

The site has five pages, the tabs at the top. Every link below opens the right page and scrolls to the section. Open the site before the pitch starts, at full screen, and keep this list beside you.

### During the talk

| When you say | Open | What to point at |
|---|---|---|
| The opening line | [Overview](https://kinship.sevenlabs.site/#/) | The family tree at the top. Wait 5 seconds: relatives glow in superposition, then one plan lights up. The caption under the tree names the shot. |
| "Every relative has a carrier probability" | Overview, scroll the hero slowly | The shading fills each person by their carrier probability. |
| "The obvious rule fails" | Overview, keep scrolling | The field rule lights three siblings and an aunt: zero couples. Then the QAOA plan: two siblings and two cousins, the exact optimum. |
| The problem in Pakistan | [Overview, the problem](https://kinship.sevenlabs.site/#problem) | The four numbers: 5%, 5,250, 31%, 49.6%. |
| "The value sits on couples" | [Overview, pairs](https://kinship.sevenlabs.site/#pairs) | The two pair cards, then 2.6% against the struck-out 26%. |
| "Every shot is a plan" | [Overview, live shots](https://kinship.sevenlabs.site/#feed) | The rows of qubits streaming in, and the running best-plan rate heading to about 8%. |
| The quantum method | [Overview, the circuit](https://kinship.sevenlabs.site/#flow) | Scroll through it: 210 equal bars, the cost layer changes colours only, the mixer grows the good plans, the readout ends on 8.31%. |
| The live demo | [Plan a visit](https://kinship.sevenlabs.site/#/plan) | Tap Cousin 1 and Cousin 2. Point at the status line, the new plan, and its "Why" line. Press + for 5 kits. |
| "Why the kit limit is built in" | Plan a visit, open "Explore the circuit", scroll to the bottom | The penalty circuit's shots spill onto 3 and 5 kits; ours stay 100% on 4. |
| Results | [Results](https://kinship.sevenlabs.site/#/results) | The four headline numbers. Use the topic tabs only if asked. |
| Limits | [Limits and team](https://kinship.sevenlabs.site/#/about) | The "No quantum speedup" card at the top. |

### When a judge asks

| Question | Open | What to point at |
|---|---|---|
| Why not just test the closest relatives? | [Results](https://kinship.sevenlabs.site/#/results), tab "Against simple rules" | One dot per family: the field rule sits far left of 100%. |
| Did quantum beat classical? | Results, tab "QAOA against random" | Constrained QAOA above random and the field rule; then say greedy and annealing do better. |
| Why constrained and not standard QAOA? | [Plan a visit](https://kinship.sevenlabs.site/#/plan), "Explore the circuit", the last panel | Valid shots 100% against 90% at depth 3; switch to depth 1 to show about half the penalty shots wasted. |
| Is the quantum part doing real work? | Plan a visit, "Explore the circuit", then "Measure 100 shots" | The best plan comes up far more often than 1 in 210. |
| What does the optimiser do? | Plan a visit, "Explore the circuit", the landscape | Pick depth 1 and press "Tune the angles here": the path climbs to Qiskit's marked optimum. |
| What happens on a real chip? | Results, tab "Under noise" | Valid shots falling as two-qubit error rises to 1%. |
| What does the circuit cost? | Results, tab "Kit limit and cost" | CZ gate counts; the Dicke state is the expensive part. |
| How does it scale? | Results, tab "Trade-off and scaling" | Linked families: decomposition plus QAOA reaches 100% of the proven optimum. |
| How are the probabilities computed? | [How it works, formulation](https://kinship.sevenlabs.site/#formulation) | Open "Show the variables, the genetics checks and the test instances": engine values against textbook values. |
| What is the exact objective? | How it works, formulation | The formula at the top. |
| How is the circuit built? | [How it works, quantum method](https://kinship.sevenlabs.site/#method) | Scroll the four steps beside the circuit diagram; the playhead moves with them. |
| Show the architecture | [How it works, architecture](https://kinship.sevenlabs.site/#architecture) | The diagram of the eight parts. |
| Compare all the plans for one family | [How it works, live plan](https://kinship.sevenlabs.site/#demo) | Switch between field rule, relevance rule, greedy, QAOA and exact. |
| Is the data real? Is this ethical? | [Limits and team](https://kinship.sevenlabs.site/#/about) | The "Synthetic families" and "Ethics" cards. |
| Can we reproduce it? | Limits and team, scroll to the bottom | The four commands and the GitHub link. |

**If the network fails:** the whole site runs from the repository. Run `python -m http.server 8000` in the repo folder and open `http://localhost:8000`.

## Numbers to know by heart

| What | Number |
|---|---|
| Carrier rate in Pakistan | about 5% |
| Field rule misses the best plan | 98% (10 relatives), 100% (16) |
| Grandparents: each a carrier, both together | 51% each, 2.6% joint (not 26%) |
| Valid plans, demo family (10 relatives, 4 kits) | 210 |
| Chance one shot is the best plan, demo family, depth 3 | 8.31% against 0.48% random |
| Quality at 16 qubits, depth 3 | 0.50 (random 0.24, field rule 0.27, greedy 0.78) |
| Gain over random, 16 qubits | 32x mean, 14x median |
| Valid shots | 100% constrained, 61% penalty (16 qubits) |
| Dicke state cost | 144 CZ gates (10 qubits), 330 (16) |
| Noise, 1% two-qubit error | 37% of shots still valid |
| Linked families | 48 relatives, 12 kits, at most 9 qubits per circuit |
| Tests | 57, and the browser circuit matches Qiskit to 1e-16 |

## Counter questions

Answer in one breath, give the number, stop. If you do not know, say so and say what you would check.

### On quantum

**Why quantum, when a classical solver handles this size?**
At our sizes it does, and we say so. The problem is pairwise yes-or-no decisions under a cardinality constraint, which QAOA represents natively: one ZZ rotation per couple, and the constraint built into the circuit. We measured how close it gets to the exact answer every time.

**Did quantum beat classical?**
No. Brute force is instant, simulated annealing found the best plan in 92% of 16-qubit families, and greedy reaches 0.78. QAOA beats the field rule and random picks. We report that openly.

**Is the quantum part doing real work or is it decoration?**
Real work. The plan given to the field officer is a measured bitstring from the circuit. Remove the circuit and you get a uniform random valid plan: quality 0.24 instead of 0.50.

**Why the constrained mixer instead of standard QAOA?**
Standard QAOA needs a penalty term, so the optimiser spends its effort learning the constraint: 39% of its shots are invalid at 16 qubits, and its valid shots are near random (0.26 against 0.24). The penalty also needs a rotation on every pair of qubits. The Dicke start and XY mixer keep 100% of shots valid. The design follows Cook, Eidenbenz and Bartschi, and we credit it.

**How do you know the mapping is correct?**
Tests check that the Ising form equals the objective for all 2^n inputs, that the Estimator energy of each basis state equals the objective, and that an independent NumPy simulation reproduces the Qiskit probabilities.

**What about a real quantum computer?**
We did not run on hardware. In an Aer noise model, at 0.1% two-qubit error 86% of shots stay valid; at 1% only 37% do and the advantage over random disappears. The Dicke state alone costs 144 CZ gates, so this needs better hardware or error mitigation.

**Does going deeper always help?**
Expected quality never fell with depth. The chance of the single best plan sometimes did, because the angles are tuned for expected value, not for that chance.

**How does it scale?**
One qubit per relative; simulators reach 25 to 30 people. Large networks split exactly along the couple graph: 48 relatives solved with circuits of at most 9 qubits plus a dynamic programme for the kits. At that size each piece is easy, so this is a scaling route, not an advantage.

**Is the problem actually hard?**
In general yes: with equal weights it is densest-k-subgraph, which is NP-hard. Our family graphs are sparse, so these instances are easy for an exact method. We say that in the report.

**Is the website circuit really Qiskit?**
No, a browser cannot run Qiskit. It is our JavaScript re-implementation, and a script checks it against the Qiskit circuit: every probability agrees to 1e-15. Every number in the report comes from the Qiskit code.

### On the problem and data

**Why not just test the closest relatives?**
Because the value is in couples. That rule missed the best plan in 98% of families and reached only 45% of the best value, even with ties broken in its favour.

**Is the data real?**
No. It is synthetic and seeded, calibrated loosely to the 2002 Pakistani study (36% carriers against 31%). No patient data is used anywhere.

**How are the carrier probabilities computed?**
Exactly, by Mendel's rules on the family tree as a Bayesian network, including loops from cousin marriages. It reproduces textbook values (sibling 2/3, grandparent about 1/2), and an independent Monte Carlo check agrees.

**Why not test one partner first, then the other only if positive?**
Sensible when results come back fast. We model one visit where everyone is chosen up front. Step-by-step testing is our listed next model.

**Is the kit really the limit, not lab time or staff?**
We assume kits per visit are the binding limit; a programme would have to confirm it. Any single budget fits the same exactly-k formulation.

**Who would actually use this?**
Field officers planning a home visit, and programme managers spreading kits across families, for example in the Punjab Thalassaemia Prevention Project and under the new Islamabad screening law.

**Is ranking relatives by genetic risk ethical?**
It can stigmatise people, so the tool uses synthetic data, treats consent as an input, publishes no individual scores, and supports a counsellor's plan for one visit. Real use needs ethics approval.

### On the work itself

**What is new here?**
The problem framing and the exact genetics-to-weights engine. We found no earlier quantum work on cascade screening. The constrained QAOA method itself is borrowed and credited.

**Can we reproduce it?**
Yes: pinned versions, fixed seeds, saved results, 57 tests, one command per step, and a Docker image. Depth-3 numbers move slightly across platforms, and that is documented.

**Did you use AI tools?**
Yes. An AI coding assistant helped write code and text, and we disclose it in the README and the report. Every number comes from running our code, and we can explain every part.

**What would you do next?**
Confirm the binding constraint with a thalassaemia centre, model step-by-step testing, calibrate against programme data, and run the smallest instance on a real IBM processor.

## Do and do not

- Lead with the family, not the maths.
- Say the limitation before they ask. It earns trust.
- Never say "quantum is faster" or "quantum advantage".
- Never say the data is real.
- Keep answers under 20 seconds. Give one number, then stop.
