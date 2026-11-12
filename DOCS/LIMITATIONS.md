# Limitations, what did not work, and ethics

The numbers below come from `results/*.json`. The full tables are in [BENCHMARKS.md](BENCHMARKS.md).

## What we do not claim

**We do not claim a quantum speedup.** We show a problem QAOA represents directly, a circuit that
cannot break the kit limit, and a comparison against exact answers.

## Limitations

1. **A classical solver wins at these sizes.** Brute force gives the exact answer for the 10- and
   16-qubit instances in milliseconds. Simulated annealing found the best plan in 100% of the
   10-qubit and 92% of the 16-qubit benchmark families.
2. **Family graphs are sparse.** The couple graph splits into small connected components: the largest
   one has 3.7 people on average for 10 relatives (at most 8) and 5.2 for 16 relatives (at most 9).
   An exact dynamic programme over those components solves the problem, so worst-case hardness results for
   densest-k-subgraph do not apply to these instances. A denser match graph would be harder.
3. **Expected quality is modest.** At depth 3 constrained QAOA reaches quality 0.62 on 10 qubits and
   0.50 on 16 qubits. A classical greedy heuristic reaches 0.86 and 0.78. QAOA beats the field
   officer's rule (0.42 and 0.27) and random valid plans (0.31 and 0.24), not the stronger heuristics.
4. **Sampling flatters small instances.** With 4,096 shots and only 210 or 4,368 valid plans, even
   uniform sampling usually contains the best plan. We report the chance per shot and the expected
   quality, not the best of all shots.
5. **Simulator only.** No real quantum processor was used. Results are noise-free unless stated.
6. **The noise model is generic.** Uniform depolarising errors, all-to-all connectivity, no error
   mitigation. On a line of qubits the circuits need considerably more two-qubit gates
   (see section 4 of the benchmark report).
7. **Depth is limited to 3**, and angles are tuned per instance with COBYLA. We did not study
   parameter transfer between families. More depth does not help every family: from depth 2 to
   depth 3 the chance that one shot is the best plan falls in 9 of the 20 ten-qubit families and 2
   of the 12 sixteen-qubit families (10-qubit median 4.6% to 4.2%, while the mean rises from 4.6%
   to 5.9%). The angles are tuned for expected value, which did not fall with depth in any family.
8. **Synthetic families.** Families are generated, not observed. The generator is calibrated loosely
   to one study from 2002: 36% carriers among testable relatives against 31% in that study.
   The share of couples who are both carriers does not match it well (2.3% excluding the index
   parents, 26% including them, against 8% in much larger real families).
9. **Simple genetics.** One gene, standard recessive inheritance, a perfect test, no new mutations.
10. **Assumed weights.** The relevance weights, the 0.5 first-cousin marriage rate shared among
    eligible cousins, and lambda = 0.05 are our assumptions. They were not reviewed by a practitioner.
11. **One visit only.** The model chooses everyone before any result is known. Real programmes may
    test one partner first and the other only if the first is a carrier. The objective counts
    confirmed at-risk couples only; the reassurance from one negative test, which rules a couple
    out, is not valued.
12. **The trade-off result is one instance.** It is an illustration, not a general claim.
13. **The hybrid loop is expensive.** Tuning the angles for one 16-qubit family took about 670
    expectation evaluations, each of which would itself need thousands of shots on a real device,
    to choose among 4,368 plans that brute force lists directly.
14. **Assumed constraint and baseline.** We assume that the kit budget of a visit is the binding
    limit; laboratory slots, officer time or the willingness of relatives may bind instead. The
    "field officer's rule" is our stand-in for an unaided choice, not a documented programme
    protocol. Its poor result does not depend on tie-breaking: with every tie in carrier
    probability broken in its favour it reaches 48% and 38% of the best value and still misses the
    best plan in 98% and 100% of families.
15. **Greedy depends on tie-breaking.** Its first pick sees no couple yet, so genetically identical
    relatives tie. Ties are broken by index. Breaking them the other way changes greedy's result in
    17 and 13 of the 50 families per size, by up to 54% of the best value, and its mean from 85% to
    89% (10 relatives) and from 84% to 79% (16 relatives).

## What did not work

| Attempt | Result |
|---|---|
| Penalty QAOA (standard mixer, penalty term) | Quality of valid shots 0.34 and 0.26 at depth 3, against 0.31 and 0.24 for a random valid plan. 14% and 39% of shots break the kit limit at depth 3; 49% and 62% at depth 1. |
| Starting constrained QAOA from the field officer's plan instead of the Dicke state | Needs only k X gates, but at depth 3 the chance of the best plan was 0.096% against 5.2% for the Dicke start. The ring mixer cannot spread one basis state far in three layers. |
| Splitting linked families family by family (development note, not in the saved results) | Cut the couple links that cross families and lost about a third of the value on the first network we tried. Replaced by the exact split along connected components of the couple graph. |
| Constrained QAOA under noise | The Dicke start state alone needs 144 CZ gates on 10 qubits. At 1% two-qubit error only 37% of shots still use exactly k kits, and the chance of the best plan falls to the random level (0.57% against 0.56%). |
| Trade-off curve on the first instance we tried, M-00 (development note, not in the saved results) | The exact front had only three plans and QAOA sampling was no better than random sampling. We then fixed a selection rule (largest exact front) and report that instance, stating the rule. |

## Ethics

- A tool that ranks relatives by genetic risk can stigmatise people. Carrier status is sensitive
  where it can affect marriage prospects.
- All data in this project is synthetic. No patient data is used.
- Consent is an input of the model: anyone who declines is fixed to "not tested".
- The tool produces a plan for one visit to support a counsellor. It publishes no individual scores
  and is not meant to decide who may marry.
- Any real use would need the approval of the screening programme and an ethics committee, and
  data protection for family trees.

## Next steps

1. Ask a thalassaemia centre whether kits, laboratory slots or officer time is the real limit, and
   which couples should count.
2. Model step-by-step testing, where one result updates the next choice.
3. Calibrate the family generator against programme data.
4. Run the smallest instance on a real IBM processor with angles trained on the simulator.
