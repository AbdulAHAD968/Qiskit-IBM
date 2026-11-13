# Kinship: pitch book

Qiskit Fall Fest 2026, final round. What to say, what to show, and how to answer the hard questions.

[Live site](https://kinship.sevenlabs.site/) | [GitHub repo](https://github.com/AbdulAHAD968/Qiskit-IBM) | [Video](https://drive.google.com/file/d/11Vun5EijHmykErL0_m3xQiPCX5_Lap2u/view?usp=sharing)

## The one-line pitch

> A child is diagnosed with thalassaemia. A field officer has four test kits for the family. Our tool picks the relatives to test, using a QAOA circuit that can never break the kit limit, and checks every plan against the exact optimum.

**Our honest position:** we do not claim a speedup. We show a real problem that QAOA represents directly, a circuit that cannot break the kit limit, and an honest comparison against exact answers.

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
