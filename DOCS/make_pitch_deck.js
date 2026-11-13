const pptxgen = require("pptxgenjs");
const path = require("path");
const REPO = path.resolve(__dirname, "..");
const FIG = (f) => path.join(REPO, "results/figures", f);

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.title = "Kinship: thalassaemia screening planned by a quantum circuit";
pres.author = "Syed Muhammad Saad Bukhari, Abdul Ahad, Faizan";
pres.theme = { headFontFace: "Cambria", bodyFontFace: "Calibri" };

const INK = "141413", CREAM = "FAF9F5", CARD = "EFE9DE", CORAL = "C2613F", TEAL = "2A8C7A",
  MUTED = "6C6A64", BODY = "3D3D3A", DARK2 = "252320", SOFT = "CFC9BF";
const H = "Cambria", B = "Calibri";

pres.defineSlideMaster({
  title: "LIGHT", background: { color: CREAM },
  objects: [{ text: { text: "Kinship  |  Qiskit Fall Fest 2026", options: { x: 0.5, y: 5.22, w: 5, h: 0.3, fontFace: B, fontSize: 10, color: MUTED, margin: 0 } } }],
  slideNumber: { x: 9.1, y: 5.22, w: 0.4, h: 0.3, fontFace: B, fontSize: 10, color: MUTED, align: "right" },
});
pres.defineSlideMaster({ title: "DARK", background: { color: INK } });

function title(s, t, sub, dark) {
  s.addText(t, { x: 0.5, y: 0.35, w: 9, h: 0.7, fontFace: H, fontSize: 32, bold: false, color: dark ? CREAM : INK, margin: 0, isTextBox: true });
  if (sub) s.addText(sub, { x: 0.5, y: 1.02, w: 9, h: 0.4, fontFace: B, fontSize: 15, color: dark ? SOFT : MUTED, margin: 0, isTextBox: true });
}
function card(s, x, y, w, h, fill) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill || CARD }, line: { color: fill || CARD }, rectRadius: 0.08 });
}
function stat(s, x, y, w, num, label, col) {
  s.addText(num, { x, y, w, h: 0.75, fontFace: H, fontSize: 40, color: col || INK, margin: 0, isTextBox: true });
  s.addText(label, { x, y: y + 0.78, w, h: 0.75, fontFace: B, fontSize: 13, color: BODY, margin: 0, valign: "top", isTextBox: true });
}

// 1. Title
let s = pres.addSlide({ masterName: "DARK" });
s.addText("Qiskit Fall Fest 2026  |  Healthcare", { x: 0.6, y: 0.6, w: 8, h: 0.35, fontFace: B, fontSize: 13, color: "E08A6C", bold: true, charSpacing: 2, margin: 0, isTextBox: true });
s.addText("Kinship", { x: 0.6, y: 1.05, w: 8, h: 1.3, fontFace: H, fontSize: 72, color: CREAM, margin: 0, isTextBox: true });
s.addText("One home visit. Four test kits. Which relatives do we test?", { x: 0.6, y: 2.4, w: 8.6, h: 0.5, fontFace: H, fontSize: 24, italic: true, color: SOFT, margin: 0, isTextBox: true });
s.addText("Planning thalassaemia cascade screening in Pakistan with a QAOA circuit that cannot break the kit limit", { x: 0.6, y: 3.05, w: 8.4, h: 0.6, fontFace: B, fontSize: 15, color: SOFT, margin: 0, isTextBox: true });
s.addText("Syed Muhammad Saad Bukhari  |  Abdul Ahad  |  Faizan", { x: 0.6, y: 4.35, w: 8.6, h: 0.35, fontFace: B, fontSize: 14, color: CREAM, bold: true, margin: 0, isTextBox: true });
s.addText("kinship.sevenlabs.site   |   github.com/AbdulAHAD968/Qiskit-IBM", { x: 0.6, y: 4.72, w: 8.6, h: 0.3, fontFace: B, fontSize: 12, color: "E08A6C", margin: 0, isTextBox: true });
s.addNotes("Saad opens. A child is diagnosed with thalassaemia. A field officer has four test kits for the family. Our tool picks the relatives to test, using a QAOA circuit that can never break the kit limit, and checks every plan against the exact optimum.");

// 2. Problem
s = pres.addSlide({ masterName: "LIGHT" });
title(s, "Thalassaemia runs in families", "Kits, lab capacity and home visits are limited, so every visit forces a choice");
[["5%", "of people in Pakistan carry beta-thalassaemia"], ["5,250", "children born with thalassaemia major each year (estimate)"],
 ["31%", "of tested relatives of a patient were carriers, against 0 of 397 controls"], ["48", "field officers cover all 36 districts of Punjab"]].forEach((d, i) => {
  const x = 0.5 + i * 2.3; card(s, x, 1.75, 2.1, 2.3); stat(s, x + 0.2, 1.95, 1.75, d[0], d[1], i === 0 ? CORAL : INK);
});
s.addText("A child is affected only when both parents are carriers. Screening starts from the relatives of a patient: cascade screening.", { x: 0.5, y: 4.3, w: 9, h: 0.6, fontFace: B, fontSize: 15, color: BODY, margin: 0, isTextBox: true });
s.addNotes("About 5% of people in Pakistan carry beta-thalassaemia, and around 5,250 children are born with thalassaemia major each year. Screening teams start from a family with an affected child and test the relatives, but kits and visits are limited: 48 field officers cover all 36 districts of Punjab. Sources: Ahmed et al. NEJM 2002, EJHG 2022.");

// 3. Insight: pairs
s = pres.addSlide({ masterName: "LIGHT" });
title(s, "The value sits on couples, not individuals", "An at-risk couple is confirmed only when both partners are tested");
card(s, 0.5, 1.65, 4.3, 1.9);
s.addShape(pres.shapes.RECTANGLE, { x: 1.2, y: 2.05, w: 0.7, h: 0.7, fill: { color: CORAL }, line: { color: CORAL } });
s.addShape(pres.shapes.LINE, { x: 1.9, y: 2.4, w: 1.4, h: 0, line: { color: MUTED, width: 1.5, dashType: "dash" } });
s.addShape(pres.shapes.OVAL, { x: 3.3, y: 2.05, w: 0.7, h: 0.7, fill: { color: CARD }, line: { color: INK, width: 1.5 } });
s.addText("One kit: no couple can be confirmed", { x: 0.7, y: 2.95, w: 3.9, h: 0.4, fontFace: B, fontSize: 14, color: BODY, align: "center", margin: 0, isTextBox: true });
card(s, 5.2, 1.65, 4.3, 1.9);
s.addShape(pres.shapes.RECTANGLE, { x: 5.9, y: 2.05, w: 0.7, h: 0.7, fill: { color: CORAL }, line: { color: CORAL } });
s.addShape(pres.shapes.LINE, { x: 6.6, y: 2.4, w: 1.4, h: 0, line: { color: CORAL, width: 3 } });
s.addShape(pres.shapes.OVAL, { x: 8.0, y: 2.05, w: 0.7, h: 0.7, fill: { color: CORAL }, line: { color: CORAL } });
s.addText("Two kits: an at-risk couple found", { x: 5.4, y: 2.95, w: 3.9, h: 0.4, fontFace: B, fontSize: 14, color: INK, bold: true, align: "center", margin: 0, isTextBox: true });
stat(s, 0.5, 3.8, 2.8, "98%", "of families where \u201Ctest the likeliest carriers\u201D misses the best plan", CORAL);
stat(s, 3.6, 3.8, 2.8, "2.6%", "chance both grandparents are carriers, not the 26% a product of singles gives", INK);
stat(s, 6.7, 3.8, 2.8, "45%", "of the best value reached by that simple rule, on average", INK);
s.addNotes("The key insight: an at-risk couple is only confirmed when both partners are tested. So the value of a plan sits on pairs of people. The obvious rule, test whoever is most likely to be a carrier, missed the best plan in 98% of our families. Pair risks are not products of single risks: each grandparent is a carrier with 51%, both together only 2.6%.");

// 4. Formulation
s = pres.addSlide({ masterName: "LIGHT" });
title(s, "A pairwise problem with a hard budget", "Exactly the shape QAOA encodes natively");
card(s, 0.5, 1.6, 9, 1.05, "FFFFFF");
const R = (t, c, o) => ({ text: t, options: Object.assign({ color: c }, o || {}) });
const SB = (t, c) => ({ text: t, options: { color: c, subscript: true } });
s.addText([R("maximise  ", MUTED), R("Σ c", CORAL, { bold: true }), SB("ij", CORAL), R(" w", CORAL, { bold: true }), SB("ij", CORAL), R(" x", CORAL, { bold: true }), SB("i", CORAL), R(" x", CORAL, { bold: true }), SB("j", CORAL),
  R("  +  λ Σ r", TEAL), SB("i", TEAL), R(" p", TEAL), SB("i", TEAL), R(" x", TEAL), SB("i", TEAL), R("      subject to  Σ x", INK), SB("i", INK), R(" = k", INK)],
  { x: 0.7, y: 1.7, w: 8.6, h: 0.85, fontFace: "Cambria", fontSize: 24, align: "center", valign: "middle", margin: 0, isTextBox: true });
[["x\u1D62", "1 if relative i is tested on this visit"], ["w\u1D62\u2C7C", "chance i and j are both carriers, computed exactly from the family tree"],
 ["c\u1D62\u2C7C", "chance the couple is real: 1 if married or engaged, lower for a possible match"], ["k", "the kits for this visit; absent relatives are fixed to 0"]].forEach((d, i) => {
  const y = 2.95 + i * 0.52;
  const base = d[0].charAt(0), idx = d[0].slice(1);
  s.addText(idx ? [{ text: base, options: { bold: true } }, { text: idx, options: { subscript: true, bold: true } }] : base, { x: 0.7, y, w: 0.9, h: 0.42, fontFace: "Cambria", fontSize: 18, color: CORAL, bold: true, margin: 0, isTextBox: true });
  s.addText(d[1], { x: 1.6, y, w: 7.8, h: 0.42, fontFace: B, fontSize: 15, color: BODY, margin: 0, valign: "middle", isTextBox: true });
});
s.addNotes("One yes-or-no decision per relative. Maximise the expected number of at-risk couples found, subject to exactly k tests. The weights come from an exact genetics engine on the family tree, cousin marriages included. That pairwise objective with a cardinality constraint is exactly the form QAOA encodes.");

// 5. The circuit
s = pres.addSlide({ masterName: "LIGHT" });
title(s, "A circuit that can only output valid plans", "One qubit per relative; the kit limit is built into the circuit, not a penalty");
[["Dicke state", "every plan with exactly k kits, built from gates"], ["Cost layer", "one ZZ rotation per couple, one Z per relative"],
 ["XY ring mixer", "swaps a tested and an untested relative"], ["Measure", "the best of 4,096 shots goes to the field officer"]].forEach((d, i) => {
  const x = 0.5 + i * 2.35;
  card(s, x, 1.7, 2.05, 1.6, i < 3 ? CORAL : INK);
  s.addText(d[0], { x: x + 0.15, y: 1.82, w: 1.75, h: 0.4, fontFace: H, fontSize: 18, color: CREAM, bold: true, margin: 0, isTextBox: true });
  s.addText(d[1], { x: x + 0.15, y: 2.25, w: 1.75, h: 0.95, fontFace: B, fontSize: 13, color: CREAM, margin: 0, valign: "top", isTextBox: true });
  if (i < 3) s.addShape(pres.shapes.RIGHT_TRIANGLE ? pres.shapes.CHEVRON : pres.shapes.CHEVRON, { x: x + 2.09, y: 2.37, w: 0.22, h: 0.26, fill: { color: MUTED }, line: { color: MUTED } });
});
s.addText("Cost and mixer repeat p = 1, 2, 3 times; COBYLA tunes the angles through the Qiskit Estimator", { x: 0.5, y: 3.42, w: 9, h: 0.35, fontFace: B, fontSize: 13, italic: true, color: MUTED, margin: 0, isTextBox: true });
stat(s, 0.5, 3.9, 2.6, "100%", "of shots use exactly k kits with our constrained circuit", CORAL);
stat(s, 3.5, 3.9, 2.6, "61%", "for standard penalty QAOA at 16 qubits", INK);
stat(s, 6.5, 3.9, 3.0, "6 + 10", "ZZ and XY gates per layer, against 45 for the penalty circuit (10 qubits)", INK);
s.addNotes("Abdul Ahad. One qubit per relative. We start in a Dicke state, an equal superposition of every plan with exactly four kits, built from gates because Qiskit has none built in (Baertschi and Eidenbenz). The cost layer puts one ZZ rotation on each couple link. The XY mixer swaps a tested and an untested relative, so the number of kits never changes. COBYLA tunes the angles through the Estimator, and the Sampler reads out plans. Standard penalty QAOA has to learn the kit rule; only 61% of its shots are valid at 16 qubits.");

// 6. Architecture
s = pres.addSlide({ masterName: "LIGHT" });
title(s, "The circuit proposes, classical code checks");
s.addImage({ path: path.join(REPO, "report/architecture.png"), x: 0.5, y: 1.05, w: 4.3, h: 4.03, altText: "System architecture in four stages" });
[["Prepare", "family generator, exact genetics engine, problem builder"], ["Quantum module", "Dicke state, cost layer, XY mixer; Estimator, COBYLA and Sampler in Qiskit 2.6 on Aer"],
 ["Check", "brute force and integer programme for the exact optimum; field rule, greedy, annealing, random; noise model"], ["Outputs", "screening plan, evaluation, report, and a live website whose circuit matches Qiskit to 1e-16"]].forEach((d, i) => {
  const y = 1.25 + i * 0.95;
  s.addShape(pres.shapes.OVAL, { x: 5.2, y: y + 0.05, w: 0.38, h: 0.38, fill: { color: i === 1 ? CORAL : INK }, line: { color: i === 1 ? CORAL : INK } });
  s.addText(String(i + 1), { x: 5.2, y: y + 0.05, w: 0.38, h: 0.38, fontFace: B, fontSize: 13, bold: true, color: CREAM, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(d[0], { x: 5.75, y, w: 3.8, h: 0.35, fontFace: H, fontSize: 17, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText(d[1], { x: 5.75, y: y + 0.35, w: 3.8, h: 0.55, fontFace: B, fontSize: 12.5, color: BODY, margin: 0, valign: "top", isTextBox: true });
});
s.addNotes("Four stages. Classical Python builds the instance and checks every answer against the exact optimum. The quantum module in Qiskit proposes the plans. 57 tests, pinned versions, fixed seeds, Docker image.");

// 7. Live demo
s = pres.addSlide({ masterName: "DARK" });
title(s, "Live demo", "kinship.sevenlabs.site", true);
s.addImage({ path: FIG("fig01_pedigree_plans.png"), x: 6.0, y: 0.35, w: 3.6, h: 4.57, altText: "Family tree: field rule plan against the QAOA plan" });
["Watch the family being measured live: superposition, then one plan", "Scroll: carrier probabilities, the field rule (0 couples), the QAOA plan (exact optimum)",
 "Scroll the circuit: 210 equal plans become an 8.31% chance of the best one", "Plan a visit: mark two cousins absent, the circuit re-plans in the browser"].forEach((t, i) => {
  const y = 1.7 + i * 0.78;
  s.addShape(pres.shapes.OVAL, { x: 0.5, y: y + 0.03, w: 0.4, h: 0.4, fill: { color: CORAL }, line: { color: CORAL } });
  s.addText(String(i + 1), { x: 0.5, y: y + 0.03, w: 0.4, h: 0.4, fontFace: B, fontSize: 14, bold: true, color: CREAM, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(t, { x: 1.1, y, w: 4.6, h: 0.65, fontFace: B, fontSize: 14, color: CREAM, margin: 0, valign: "top", isTextBox: true });
});
s.addNotes("Abdul Ahad runs the demo. 1. Overview: let the hero sit five seconds; each highlight is a real shot. 2. Scroll the hero: shading, field rule with zero couples, QAOA plan with two siblings and two cousins. 3. Circuit scroll: end on 8.31%. 4. Plan a visit: tap Cousin 1 and Cousin 2 absent; read the status line and the reason; press + for 5 kits. 5. Explore the circuit: penalty comparison. Backup: python -m kinship.demo.");

// 8. Results
s = pres.addSlide({ masterName: "LIGHT" });
title(s, "Measured against the exact answer, every time", "Noise-free simulation, 20 families of 10 relatives and 12 of 16, depth 1 to 3");
s.addImage({ path: FIG("fig03_quality_vs_depth.png"), x: 0.5, y: 1.55, w: 5.6, h: 2.39, altText: "Quality against QAOA depth" });
stat(s, 6.5, 1.55, 3.0, "0.50", "quality at 16 qubits, depth 3; random 0.24, field rule 0.27", CORAL);
stat(s, 6.5, 3.05, 3.0, "32\u00D7", "more often the best plan than a random pick (median 14\u00D7)", INK);
s.addText("Linked families of 48 relatives and 12 kits were solved to the proven optimum, with circuits of at most 9 qubits.", { x: 0.5, y: 4.3, w: 9, h: 0.55, fontFace: B, fontSize: 15, color: BODY, margin: 0, isTextBox: true });
s.addNotes("Faizan. Against the exact optimum: on 16 qubits constrained QAOA reaches quality 0.50, against 0.24 for random and 0.27 for the field rule, and one shot is the best plan 32 times more often than a random pick on average, median 14. Every shot is valid. Linked families of 48 people are solved to the proven optimum with circuits of at most 9 qubits.");

// 9. Limits
s = pres.addSlide({ masterName: "LIGHT" });
title(s, "What we do not claim", "Said before anyone asks");
[["No quantum speedup", "Brute force solves these sizes in milliseconds; annealing found the best plan in 92% of 16-qubit families"],
 ["Greedy beats QAOA", "Greedy reaches 0.78 at 16 qubits; QAOA beats random and the field rule, not the stronger heuristics"],
 ["Simulator only", "At 1% two-qubit noise only 37% of shots stay valid; the Dicke state alone costs 144 CZ gates"],
 ["Synthetic families", "Calibrated to a 2002 study; one gene, a perfect test, one visit, and no patient data"]].forEach((d, i) => {
  const x = 0.5 + (i % 2) * 4.6, y = 1.6 + Math.floor(i / 2) * 1.7;
  card(s, x, y, 4.4, 1.5);
  s.addText(d[0], { x: x + 0.25, y: y + 0.15, w: 3.9, h: 0.4, fontFace: H, fontSize: 18, bold: true, color: i === 0 ? CORAL : INK, margin: 0, isTextBox: true });
  s.addText(d[1], { x: x + 0.25, y: y + 0.58, w: 3.9, h: 0.8, fontFace: B, fontSize: 13.5, color: BODY, margin: 0, valign: "top", isTextBox: true });
});
s.addNotes("We do not claim a speedup. We show a problem QAOA represents directly, a circuit that cannot break the kit limit, and an honest comparison against exact answers. This is a method study on a new, real problem.");

// 10. Next steps
s = pres.addSlide({ masterName: "LIGHT" });
title(s, "Where this goes next");
[["Ask a thalassaemia centre", "whether kits, lab slots or officer time is the real limit"], ["Step-by-step testing", "one result updates the next choice, beyond a single visit"],
 ["Calibrate on programme data", "real family structures from the Punjab project"], ["Run on IBM hardware", "the 10-qubit instance with angles trained on the simulator"]].forEach((d, i) => {
  const y = 1.3 + i * 0.9;
  s.addShape(pres.shapes.OVAL, { x: 0.5, y: y + 0.05, w: 0.45, h: 0.45, fill: { color: TEAL }, line: { color: TEAL } });
  s.addText(String(i + 1), { x: 0.5, y: y + 0.05, w: 0.45, h: 0.45, fontFace: B, fontSize: 15, bold: true, color: CREAM, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(d[0], { x: 1.15, y, w: 8.3, h: 0.35, fontFace: H, fontSize: 18, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText(d[1], { x: 1.15, y: y + 0.37, w: 8.3, h: 0.35, fontFace: B, fontSize: 14, color: BODY, margin: 0, isTextBox: true });
});
s.addNotes("Next: confirm the binding constraint with a thalassaemia centre, model step-by-step testing, calibrate families against programme data, and run the smallest instance on a real IBM processor.");

// 11. Close
s = pres.addSlide({ masterName: "DARK" });
s.addText("Four kits, two couples, the exact optimum", { x: 0.6, y: 1.2, w: 8.8, h: 1.0, fontFace: H, fontSize: 36, color: CREAM, margin: 0, isTextBox: true });
s.addText("A real screening decision, written as a circuit that cannot break the rules, and checked against the exact answer every time.", { x: 0.6, y: 2.25, w: 8.6, h: 0.8, fontFace: B, fontSize: 17, color: SOFT, margin: 0, isTextBox: true });
[["Live site", "kinship.sevenlabs.site"], ["Code", "github.com/AbdulAHAD968/Qiskit-IBM"], ["Team", "Syed Muhammad Saad Bukhari, Abdul Ahad, Faizan"]].forEach((d, i) => {
  s.addText(d[0], { x: 0.6, y: 3.45 + i * 0.45, w: 1.4, h: 0.35, fontFace: B, fontSize: 13, bold: true, color: "E08A6C", margin: 0, isTextBox: true });
  s.addText(d[1], { x: 2.0, y: 3.45 + i * 0.45, w: 7.4, h: 0.35, fontFace: B, fontSize: 14, color: CREAM, margin: 0, isTextBox: true });
});
s.addNotes("Thank you. Then questions: see DOCS/PITCH.md for the answers.");

pres.writeFile({ fileName: path.join(REPO, "DOCS/Kinship_Pitch_Deck.pptx") }).then((f) => console.log("wrote", f));
