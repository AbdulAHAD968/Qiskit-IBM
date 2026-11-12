# Video pitch and demo: script for 3 minutes

Hard limit 3:00. The storyboard below ends at 2:45. The narration is 362 words, which is about
2:25 at 150 words a minute, so there is room to pause while the screen changes.

## Before recording

1. Start the site: `python -m http.server 8000` in the repository folder, then open
   `http://localhost:8000` in a browser at 100% zoom, full screen.
2. Open a terminal in the repository folder with a large font. Run `python -m kinship.demo` once so
   the second run is warm.
3. Record the screen with microphone audio at 1080p (Windows: Win + Alt + R, or OBS).
4. Upload to Google Drive, set access to "Anyone with the link", and open the link in a private
   window to check it plays.

## Storyboard

| Time | On screen | Narration |
|---|---|---|
| 0:00 - 0:22 | Website hero, then scroll slowly to the four numbers in section 1 | "One home visit, four test kits: which relatives do we test? In Pakistan about five percent of people carry beta-thalassaemia. A child is affected only when both parents are carriers. Screening teams start from a family with an affected child and test the relatives, but field capacity is limited." |
| 0:22 - 0:45 | Section 2: the two pair cards, then the 2.6% against 26% card | "An at-risk couple can only be confirmed when both partners are tested. So the value sits on pairs of people, not individuals. Each grandparent alone is a carrier with probability one half, but both together only two point six percent. That makes this a pairwise optimisation problem with an exactly-k constraint." |
| 0:45 - 1:10 | Section 3 formula, then section 5: scroll through the circuit steps | "We maximise the expected number of at-risk couples found, subject to exactly k tests. That maps directly onto QAOA: one qubit per relative and one ZZ rotation per couple. We start in a Dicke state, built from gates, and use an XY mixer, so the circuit can only output plans with exactly k kits." |
| 1:10 - 1:25 | Section 6: architecture diagram | "Classical code builds the family, computes exact carrier probabilities and checks the answers. The Qiskit circuit, tuned with the Estimator and read out with the Sampler, proposes the plan." |
| 1:25 - 1:53 | Terminal: run `python -m kinship.demo`; then section 4 of the site: click "Field officer's rule", then "Constrained QAOA" | "Here is the live demo. One command builds a family, trains the circuit and measures plans. The simple rule, test the highest carrier probabilities, cannot confirm a single at-risk couple. The QAOA plan tests two siblings and the two cousins they may marry, and matches the exact optimum." |
| 1:53 - 2:26 | Section 7: quality charts, then the valid-shots bars, then linked families | "Across twenty and twelve seeded families, constrained QAOA beats random picks and the simple rule. At sixteen qubits one shot is the best plan thirty-two times more often than a random valid pick on average; the median is fourteen. Every shot is valid, while penalty QAOA wastes up to sixty-two percent of its shots. Networks of forty-eight relatives are solved to the proven optimum by splitting them into pieces of at most nine qubits, which shows a scaling route, not an advantage." |
| 2:26 - 2:41 | Section 8: limitations cards | "We do not claim a speedup. At these sizes brute force and simulated annealing win, family graphs are sparse, the data is synthetic, and everything runs on a simulator. Under one percent gate noise most shots are lost." |
| 2:41 - 2:45 | Section 9: team and repository link | "Code, results and the report are in the repository. Thank you." |

## Checklist

- [ ] Video is 3:00 or shorter.
- [ ] The demo command is visible and runs to the end.
- [ ] The family tree with the chosen relatives is shown.
- [ ] Limitations are stated out loud.
- [ ] The Drive link opens in a private window without signing in.
