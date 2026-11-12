# Problem statement

**Domain:** Healthcare (allocation of limited medical equipment and staff time).

**Problem in one sentence.** For one home visit with k test kits, choose which relatives of a
thalassaemia patient to test so that the expected number of at-risk couples identified is as
large as possible.

## Motivation

- Thalassaemia major appears only when both parents are carriers. About 5% of people in
  Pakistan carry beta-thalassaemia, and one estimate puts affected births at about 5,250 a year [1].
- Screening the relatives of an affected child (cascade screening) is far more productive than
  screening at random: 31% of tested relatives in such families were carriers against 0 of
  397 in control families, and 8% of married couples in those families were both carriers [1].
- Relatives marry each other: 49.6% of ever-married women in the 2017-18 Demographic and
  Health Survey were married to a first cousin [3]. At-risk couples therefore cluster inside families.
- Capacity is limited. The Punjab Thalassaemia Prevention Project covers 36 districts with 48 field
  officers and reports low uptake of cascade testing [2]. A 2026 bill passed by the National Assembly
  and the Senate would make screening and counselling of patients' blood relatives a duty in the
  Islamabad Capital Territory [4].

**Users.** Field officers planning one visit; programme managers spreading kits across families.

## Why it is an optimisation problem

An at-risk couple can be confirmed only when both partners are tested. One test can rule a couple out,
but it can never confirm one.
The value of a plan therefore sits on pairs of people, and the pair probabilities cannot be built
from single-person probabilities: each grandparent of an affected child is a carrier with
probability 0.51, but both together only with probability 0.026.

## Formulation

| Element | Definition |
|---|---|
| Decision variable `x_i` | 1 if relative i is tested in this visit, otherwise 0 |
| Pair weight `w_ij` | probability that i and j are both carriers, from the family tree |
| Link strength `c_ij` | probability that the couple link is real: 1 for married or engaged, lower for a possible future match between cousins |
| Single weight `p_i` | probability that i is a carrier |
| Relevance `r_i` | 1.0 unmarried or engaged adult, 0.7 married adult, 0.5 child, 0.1 elder |

```
maximise    F(x) = sum over couples (i,j) of  c_ij * w_ij * x_i * x_j   +   lambda * sum over i of  r_i * p_i * x_i
subject to  sum over i of x_i = k,     x_i in {0, 1}
```

- **Objective.** The first term is the expected number of at-risk couples found. It is exact for
  married and engaged couples. The second term is a small reward for single carriers found
  (lambda = 0.05).
- **Constraint.** Exactly k people are tested. No weight is negative, so using every kit is never
  worse than using fewer. People who are absent or decline are fixed to 0.
  The affected child and the parents (obligate carriers) are not decision variables.
- **What is not valued.** The objective counts confirmed at-risk couples only. The reassurance from
  one negative test, which rules a couple out, earns nothing; this belongs to the step-by-step
  model listed as a limitation.
- **Measurable outcome.** Expected at-risk couples found per visit; every method is scored against
  the exact optimum.

## Test instances

| Size | Relatives (qubits) | Kits | Valid plans | Used for |
|---|---:|---:|---:|---|
| S | 10 | 4 | 210 | brute force, noise study, worked example |
| M | 16 | 5 | 4,368 | main simulator results, trade-off curve |
| L | 48 in 4 linked families | 12 | about 7 × 10^10 | exact integer programme, decomposition |

All families are synthetic and seeded. No patient data is used.

## Quantum approach

QAOA in Qiskit. One qubit per relative, a ZZ rotation per couple link, and a start state and mixer
(Dicke state, XY ring mixer) that can only produce plans with exactly k kits. A penalty QAOA is the
baseline. Brute force, an integer programme, the field officer's rule, a greedy heuristic and
simulated annealing are the classical references.

References are listed in [REFERENCES.md](REFERENCES.md).
