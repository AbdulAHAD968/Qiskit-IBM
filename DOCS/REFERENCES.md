# Sources and credits

## Pakistan context

1. Ahmed S, Saleem M, Modell B, Petrou M. Screening extended families for genetic hemoglobin
   disorders in Pakistan. N Engl J Med. 2002;347(15):1162-1168. doi:10.1056/NEJMsa013234
   - About 5% of the population carries beta-thalassaemia; about 5,250 affected births a year (estimate).
   - 15 families: 10 with an index case, 5 controls. Index families: 183 of 591 tested were carriers
     (31%). Control families: 0 of 397. 17 of 214 married couples were both carriers (8%).
   - Among 350 randomly selected pregnant women there were 17 carriers (5%) and no at-risk couple.
2. Ahmed S, Jafri H, Faran M, Ahmed WN, Rashid Y, Ehsan Y, Ahmed M. Cascade screening for
   beta-thalassaemia in Pakistan: relatives' experiences of a decision support intervention in
   routine practice. Eur J Hum Genet. 2022;30(4):406-412. doi:10.1038/s41431-021-00974-y
   - Punjab Thalassaemia Prevention Project: nine regional centres, all 36 districts, 48 field
     officers; uptake of cascade testing described as low.
3. National Institute of Population Studies and ICF. Pakistan Demographic and Health Survey
   2017-18. Islamabad and Rockville; 2019. Figures as reported in Iqbal S, Zakar R, Fischer F,
   Zakar MZ. Consanguineous marriages and their association with women's reproductive health and
   fertility behavior in Pakistan. BMC Women's Health. 2022;22:118. doi:10.1186/s12905-022-01704-2
   - 49.6% of ever-married women married to a first cousin; about 64% to a relative.
4. Dawn, 11 March 2026: National Assembly passes the Islamabad Capital Territory compulsory
   thalassaemia screening bill, https://www.dawn.com/news/1980653. Associated Press of Pakistan,
   11 May 2026: passage by the Senate,
   https://www.app.com.pk/national/5-private-member-bills-smoothly-sail-through-senate/.
   - Premarital screening reports through the Nikah registrar; screening and counselling of patients'
     blood relatives. Presidential assent could not be confirmed at the time of writing.

## Methods

5. Cook J, Eidenbenz S, Bärtschi A. The Quantum Alternating Operator Ansatz on Maximum k-Vertex
   Cover. IEEE QCE 2020, 83-92. arXiv:1910.13483. Source of the constrained design: Dicke start
   state and XY mixer.
6. Bärtschi A, Eidenbenz S. Deterministic Preparation of Dicke States. FCT 2019, Lecture Notes in
   Computer Science, 126-139. arXiv:1904.07358. Source of the Dicke-state circuit.
7. Farhi E, Goldstone J, Gutmann S. A Quantum Approximate Optimization Algorithm. 2014.
   arXiv:1411.4028
8. Hadfield S, Wang Z, O'Gorman B, Rieffel EG, Venturelli D, Biswas R. From the Quantum Approximate
   Optimization Algorithm to a Quantum Alternating Operator Ansatz. Algorithms. 2019;12(2):34.
   doi:10.3390/a12020034
9. Wang Z, Rubin NC, Dominy JM, Rieffel EG. XY mixers: analytical and numerical results for the
   quantum alternating operator ansatz. Phys Rev A. 2020;101:012320. arXiv:1904.09314. Source of the
   parity-ordered ring mixer.
10. Zhou L, Wang S-T, Choi S, Pichler H, Lukin MD. Quantum Approximate Optimization Algorithm:
    Performance, Mechanism, and Implementation on Near-Term Devices. Phys Rev X. 2020;10:021067.
    arXiv:1812.01041. Source of the INTERP warm start.
11. Kotil A, Pelofske E, Riedmüller S, Egger DJ, Eidenbenz S, Koch T, Woerner S. Quantum
    approximate multi-objective optimization. Nat Comput Sci. 2025;5:1168-1177. arXiv:2503.22797.
    Idea behind the trade-off sweep.
12. Bhaskara A, Charikar M, Chlamtac E, Feige U, Vijayaraghavan A. Detecting high log-densities: an
    O(n^1/4) approximation for densest k-subgraph. STOC 2010, 201-210. arXiv:1001.2891
13. Manurangsi P. Almost-polynomial ratio ETH-hardness of approximating densest k-subgraph. STOC
    2017, 954-961. arXiv:1611.05991. The arXiv version was revised by the author in October 2026:
    it now states the result under a different assumption ("Almost-ETH") because, according to the
    author's note, the assumptions of the published version no longer hold. We therefore quote only
    NP-hardness and the n^(1/4) approximation guarantee and do not rely on this conditional result.

## Software

| Package | Version | Used for |
|---|---|---|
| Qiskit | 2.6.2 | circuits, `SparsePauliOp`, `XXPlusYYGate`, transpiler, `Statevector` |
| Qiskit Aer | 0.18.2 | `EstimatorV2`, `SamplerV2`, statevector and density-matrix simulation, noise model |
| NumPy | 2.4.6 | arrays, exact pedigree inference |
| SciPy | 1.17.1 | COBYLA optimiser, HiGHS integer programme (`scipy.optimize.milp`) |
| Matplotlib | 3.11.2 | figures |
| python-docx | 1.2.0 | report generation |
| pytest | 9.2.0 | tests |

## Code credits

All code in this repository was written for this project. The circuits were written from the
papers above; no tutorial or third-party code was copied.

AI assistance: an AI coding assistant was used to help write code and draft text. Every number in
the report and on the website is produced by running the code in this repository.
