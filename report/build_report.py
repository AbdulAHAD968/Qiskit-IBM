"""Build report/Kinship_QAOA_Report.docx from the saved results.

    python report/build_report.py

Every number in the report is read from results/*.json, so the document always
matches the repository. Run `python -m kinship.evaluate all` and
`python -m kinship.plots` first if the results or figures are missing.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401  (kept for readers who want landscape tables)
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIG = RESULTS / "figures"
OUT = ROOT / "report" / "Kinship_QAOA_Report.docx"
REPO = "https://github.com/AbdulAHAD968/Qiskit-IBM"

NAVY = RGBColor(0x18, 0x4F, 0x95)
INK2 = RGBColor(0x52, 0x51, 0x4E)
FONT = "Calibri"
MONO = "Consolas"


def load(name):
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


R = {name: load(name) for name in
     ("meta", "genetics", "gate1", "benchmark", "circuits", "noise", "ablation", "tradeoff", "decomposition", "demo")}
_mc_path = RESULTS / "genetics_montecarlo.json"
MC = json.loads(_mc_path.read_text(encoding="utf-8")) if _mc_path.exists() else None
if R["meta"].get("quick"):
    raise SystemExit("results/ holds a reduced --quick run. Run `python -m kinship.evaluate all` before building the report.")


def bench(size, method, p=None):
    return next(r for r in R["benchmark"]["summary"] if r["size"] == size and r["method"] == method and r["p"] == p)


def circ(size, method, p, line=False):
    topo = "line" if line else "all-to-all"
    return next(r for r in R["circuits"]["rows"]
                if r["size"] == size and r["method"] == method and r["p"] == p and r["topology"] == topo)


def noise(method, p, e2):
    return next(r for r in R["noise"]["summary"] if r["method"] == method and r["p"] == p and abs(r["e2"] - e2) < 1e-12)


def pct(v, digits=0):
    return f"{100 * v:.{digits}f}%"


def pct_small(v):
    return f"{100 * v:.{3 if v < 0.001 else 2 if v < 0.01 else 1}f}%"


# --------------------------------------------------------------------------
# document helpers
# --------------------------------------------------------------------------
doc = Document()
TOKEN = re.compile(r"(\*\*.+?\*\*|\*.+?\*|_\{.+?\}|\^\{.+?\}|`.+?`)")


def set_font(run, name=FONT, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def rich(paragraph, text, size=None, color=None, bold=None):
    """Add text with light markup: **bold**, *italic*, _{sub}, ^{sup}, `code`."""
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            set_font(paragraph.add_run(part[2:-2]), size=size, bold=True, color=color)
        elif part.startswith("_{"):
            run = paragraph.add_run(part[2:-1])
            set_font(run, size=size, color=color, bold=bold)
            run.font.subscript = True
        elif part.startswith("^{"):
            run = paragraph.add_run(part[2:-1])
            set_font(run, size=size, color=color, bold=bold)
            run.font.superscript = True
        elif part.startswith("`"):
            set_font(paragraph.add_run(part[1:-1]), name=MONO, size=(size or 10.5) - 1, color=color)
        elif part.startswith("*") and part.endswith("*"):
            set_font(paragraph.add_run(part[1:-1]), size=size, italic=True, color=color, bold=bold)
        else:
            set_font(paragraph.add_run(part), size=size, color=color, bold=bold)
    return paragraph


def para(text, size=None, align=None, after=6, before=0, color=None, keep=False):
    p = doc.add_paragraph()
    rich(p, text, size=size, color=color)
    fmt = p.paragraph_format
    fmt.space_after, fmt.space_before = Pt(after), Pt(before)
    fmt.keep_with_next = keep
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def heading(text, level=1):
    p = doc.add_heading(level=level)
    set_font(p.add_run(text), size=15 if level == 1 else 12, bold=True, color=NAVY if level == 1 else RGBColor(11, 11, 11))
    fmt = p.paragraph_format
    fmt.space_before, fmt.space_after, fmt.keep_with_next = Pt(16 if level == 1 else 10), Pt(5), True
    return p


def bullets(items, style="List Bullet"):
    for item in items:
        p = doc.add_paragraph(style=style)
        rich(p, item)
        p.paragraph_format.space_after = Pt(3)


def shade(cell, fill):
    props = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    props.append(shd)


def borders(table, color="C3C2B7", size=4, inside=True):
    props = table._tbl.tblPr
    node = OxmlElement("w:tblBorders")
    edges = ["top", "left", "bottom", "right"] + (["insideH", "insideV"] if inside else [])
    for edge in edges:
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(size))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        node.append(e)
    props.append(node)


def cell_margins(table, top=50, bottom=50, left=90, right=90):
    props = table._tbl.tblPr
    node = OxmlElement("w:tblCellMar")
    for edge, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:w"), str(value))
        e.set(qn("w:type"), "dxa")
        node.append(e)
    props.append(node)


def table(header, rows, widths, align=None, size=9, caption=None):
    if caption:
        cp = para(caption, size=9, after=3, before=6, color=INK2, keep=True)
        for run in cp.runs:
            run.font.italic = True
    t = doc.add_table(rows=1, cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    borders(t)
    cell_margins(t)
    align = align or ["l"] * len(header)

    def fill(cells, values, bold=False, fill_color=None):
        for i, (cell, value) in enumerate(zip(cells, values)):
            cell.width = Cm(widths[i])
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if align[i] == "r" else WD_ALIGN_PARAGRAPH.LEFT
            rich(p, str(value), size=size, bold=bold or None)
            if fill_color:
                shade(cell, fill_color)

    fill(t.rows[0].cells, header, bold=True, fill_color="F1F0EC")
    repeat = OxmlElement("w:tblHeader")          # repeat the header row when a table breaks across pages
    repeat.set(qn("w:val"), "true")
    t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        fill(t.add_row().cells, row)
    for row in t.rows[:2]:                       # never leave a header row alone at the foot of a page
        for cell in row.cells:
            cell.paragraphs[0].paragraph_format.keep_with_next = True
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)
    return t


def callout(title, lines):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    borders(t, color="9EC5F4", size=6, inside=False)
    cell_margins(t, top=120, bottom=120, left=180, right=180)
    cell = t.rows[0].cells[0]
    shade(cell, "EEF4FC")
    p = cell.paragraphs[0]
    set_font(p.add_run(title), size=10.5, bold=True, color=NAVY)
    p.paragraph_format.space_after = Pt(4)
    for line in lines:
        q = cell.add_paragraph()
        rich(q, line, size=10)
        q.paragraph_format.space_after = Pt(3)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def figure(path, caption, width=16.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(path), width=Cm(width))
    c = para(caption, size=9, align="center", after=10, color=INK2)
    for run in c.runs:
        run.font.italic = True


def figures_side_by_side(items, width=7.9):
    t = doc.add_table(rows=1, cols=len(items))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, (path, caption) in zip(t.rows[0].cells, items):
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(path), width=Cm(width))
        q = cell.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rich(q, caption, size=9, color=INK2)
        for run in q.runs:
            run.font.italic = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def code(lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.6)
        set_font(p.add_run(line), name=MONO, size=9)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def link(paragraph, url, text, size=None):
    rel = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    node = OxmlElement("w:hyperlink")
    node.set(qn("r:id"), rel)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        fonts.set(qn(attr), FONT)
    props.append(fonts)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "184F95")
    props.append(color)
    under = OxmlElement("w:u")
    under.set(qn("w:val"), "single")
    props.append(under)
    if size:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size * 2)))
        props.append(sz)
    run.append(props)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    run.append(t)
    node.append(run)
    paragraph._p.append(node)


def page_number_footer(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("Kinship Screening with QAOA  |  page "), size=8.5, color=INK2)
    run = p.add_run()
    set_font(run, size=8.5, color=INK2)
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            node = OxmlElement("w:fldChar")
            node.set(qn("w:fldCharType"), kind)
        else:
            node = OxmlElement("w:instrText")
            node.set(qn("xml:space"), "preserve")
            node.text = text
        run._r.append(node)


# --------------------------------------------------------------------------
# page set-up and styles
# --------------------------------------------------------------------------
section = doc.sections[0]
section.page_width, section.page_height = Cm(21.0), Cm(29.7)
section.left_margin = section.right_margin = Cm(2.3)
section.top_margin, section.bottom_margin = Cm(2.2), Cm(2.2)
page_number_footer(section)
normal = doc.styles["Normal"]
normal.font.name, normal.font.size = FONT, Pt(10.5)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
normal.paragraph_format.line_spacing = 1.12
for name in ("List Bullet", "List Number"):
    doc.styles[name].font.name = FONT
    doc.styles[name].font.size = Pt(10.5)
doc.core_properties.title = "Kinship Screening with QAOA"
doc.core_properties.subject = "Qiskit Fall Fest 2026 Hackathon, Healthcare domain"
doc.core_properties.author = "Syed Muhammad Saad Bukhari, Abdul Ahad, Faizan"
doc.core_properties.keywords = "QAOA, Qiskit, thalassaemia, cascade screening, quantum optimisation"
doc.core_properties.comments = "Generated by report/build_report.py from results/*.json"
doc.core_properties.created = doc.core_properties.modified = datetime.now(timezone.utc).replace(tzinfo=None)
doc.core_properties.last_modified_by = "Syed Muhammad Saad Bukhari, Abdul Ahad, Faizan"

# --------------------------------------------------------------------------
# numbers used in the text
# --------------------------------------------------------------------------
G = R["gate1"]["summary"]
GEN = R["genetics"]
CAL = GEN["calibration"]
checks = {c["relation"]: c for c in GEN["checks"]}
cS3, cM3 = bench("S", "constrained", 3), bench("M", "constrained", 3)
pS3, pM3 = bench("S", "penalty", 3), bench("M", "penalty", 3)
pS1, pM1 = bench("S", "penalty", 1), bench("M", "penalty", 1)
rS, rM = bench("S", "random"), bench("M", "random")
fS, fM = bench("S", "field"), bench("M", "field")
gS, gM = bench("S", "greedy"), bench("M", "greedy")
aS, aM = bench("S", "annealing"), bench("M", "annealing")
DEC = R["decomposition"]
max_q = max(r["max_qubits"] for r in DEC["rows"])
dec_runs = sum(r["qaoa_runs"] for r in DEC["rows"])
dec_all_opt = all(r["decomposed_qaoa"]["optimal"] for r in DEC["rows"])
ABL = {(r["initial"], r["p"]): r for r in R["ablation"]["summary"]}
TR = R["tradeoff"]
DEMO = R["demo"]
dq = [q for q in DEMO["qaoa"] if q["method"] == "constrained"][-1]
dpen = [q for q in DEMO["qaoa"] if q["method"] == "penalty"][-1]
n1c = noise("constrained", 1, 0.01)
n0c = noise("constrained", 1, 0.0)
n1p = noise("penalty", 1, 0.01)
n5c = noise("constrained", 1, 0.001)
META = R["meta"]
total_seconds = sum(META["seconds"].values())
TIE_S, TIE_M = G["S"]["field"]["tie_break"], G["M"]["field"]["tie_break"]
GT_S, GT_M = G["S"]["greedy"]["tie_break"], G["M"]["greedy"]["tie_break"]
TRAIN_EVALS = round(sum(bench("M", "constrained", depth)["evaluations"]["mean"] for depth in (1, 2, 3)), -1)

# --------------------------------------------------------------------------
# title block
# --------------------------------------------------------------------------
p = para("QISKIT FALL FEST 2026 HACKATHON  |  DOMAIN: HEALTHCARE", size=9, after=4, color=NAVY)
p.runs[0].font.bold = True
p = para("Kinship Screening with QAOA", size=26, after=2)
p.runs[0].font.bold = True
para("Whom to test in thalassaemia cascade screening when kits are limited: a quantum optimisation study in Qiskit",
     size=13, after=8, color=INK2)
p = para("**Team:** Syed Muhammad Saad Bukhari, Abdul Ahad, Faizan", size=10.5, after=2)
p = para("**Repository:** ", size=10.5, after=2)
link(p, REPO, REPO.replace("https://", ""), size=10.5)
para("**Date:** 12 November 2026.  **Software:** Qiskit %s, Qiskit Aer %s, Python %s. Simulator only."
     % (META["qiskit"], META["qiskit_aer"], META["python"]), size=10.5, after=10)

callout("Summary", [
    "For one home visit with k test kits, which relatives of a thalassaemia patient should be tested? We choose "
    "exactly k people to maximise the expected number of at-risk couples identified. An at-risk couple is confirmed only when "
    "both partners are tested, so the value sits on pairs of people and the problem is a quadratic binary "
    "optimisation with a cardinality constraint. That is the form QAOA represents directly.",
    "We implement a constrained QAOA in Qiskit (Dicke start state built from gates, XY ring mixer) that can only "
    "output plans with exactly k kits, compare it with a penalty QAOA baseline, and score both against exact answers "
    "and against the obvious rule of thumb: test the relatives most likely to be carriers.",
    f"**The simple rule fails.** Testing the highest carrier probabilities misses the best plan in "
    f"{pct(G['S']['field']['miss_rate'])} of 10-relative families and {pct(G['M']['field']['miss_rate'])} of "
    f"16-relative families, reaching {pct(G['S']['field']['ratio']['mean'])} and {pct(G['M']['field']['ratio']['mean'])} "
    "of the best value.",
    f"**Constrained QAOA works as designed.** Every shot uses exactly k kits. At depth 3 its quality is "
    f"{cS3['quality']['mean']:.2f} on 10 qubits and {cM3['quality']['mean']:.2f} on 16 qubits, against "
    f"{rS['quality']['mean']:.2f} and {rM['quality']['mean']:.2f} for a random valid plan. Family by family, one shot "
    f"is the best plan on average {cS3['p_opt_gain']['mean']:.0f} and {cM3['p_opt_gain']['mean']:.0f} times more often "
    f"than a random valid pick (median {cS3['p_opt_gain']['median']:.0f} and {cM3['p_opt_gain']['median']:.0f} times). "
    f"Penalty QAOA stays near random ({pS3['quality']['mean']:.2f} and {pM3['quality']['mean']:.2f}) and wastes "
    f"{pct(1 - pM3['valid_share']['mean'])} of its shots on invalid plans at 16 qubits.",
    f"**It scales by decomposition.** Networks of {DEC['rows'][0]['n']} relatives and {DEC['rows'][0]['k']} kits are "
    f"solved to the proven optimum with circuits of at most {max_q} qubits. The pieces are small enough for sampling "
    "to find each optimum easily, so this shows a scaling route, not an advantage.",
    "**No speedup is claimed.** Brute force and simulated annealing solve these sizes; section 6 lists what did not "
    "work, with numbers.",
])

# --------------------------------------------------------------------------
# 1. Problem and users
# --------------------------------------------------------------------------
heading("1. Problem and users")
para("Beta-thalassaemia major is an inherited blood disorder. A child is affected only when both parents carry the "
     "gene. About 5% of people in Pakistan are carriers, and one estimate puts births of children with "
     "thalassaemia major at about 5,250 a year [1]. Patients depend on regular blood transfusions for life.",
     align="justify")
para("The most efficient way to find at-risk couples is cascade screening: start from a family that already has an "
     "affected child and test the relatives. In the study that introduced the approach in Pakistan, 183 of 591 "
     "tested relatives in such families were carriers (31%) against none of 397 in control families, and 17 "
     "of 214 married couples in those families were both carriers (8%) [1]. Marriage inside the family drives "
     "this concentration: in the 2017-18 Demographic and Health Survey 49.6% of ever-married women were "
     "married to a first cousin, and about 64% to a relative of some kind [3].", align="justify")
para("Field capacity is limited. The Punjab Thalassaemia Prevention Project covers all 36 districts of Punjab from "
     "nine regional centres with 48 field officers, and reports low uptake of cascade testing among relatives [2]. "
     "The legal duty is growing: in 2026 the National Assembly and the Senate passed a compulsory thalassaemia "
     "screening bill for the Islamabad Capital Territory that asks for premarital screening reports and for "
     "screening and counselling of patients' blood relatives [4].", align="justify")
para("**The decision.** On every home visit a field officer has k test kits for one extended family and must choose "
     "who is tested. An at-risk couple can be confirmed only when both partners are tested (one test can rule a "
     "couple out, but never confirm one), so the value of a plan sits on "
     "pairs of people, and the natural rule, test whoever is most likely to be a carrier, spends kits on people "
     "whose partners go untested. We call that rule the field officer's rule; it is our stand-in for an unaided "
     "choice, not a documented protocol of any programme. We assume that the number of kits for a visit is the "
     "binding limit, which a programme would have to confirm (section 6). **Users:** field officers planning one "
     "visit, and programme managers spreading kits across families.", align="justify")
para("**Originality.** We searched for earlier work applying quantum optimisation to cascade screening or to test "
     "allocation on family trees and found none; two searches cannot prove that none exists. The closest published "
     "work studies QAOA on a closely related graph problem with the same exactly-k constraint, maximum k-vertex "
     "cover [5]. The "
     "problem framing and the weights derived from genetics are ours; the constrained QAOA design is borrowed and "
     "credited.", align="justify")

# --------------------------------------------------------------------------
# 2. Formulation
# --------------------------------------------------------------------------
heading("2. Formulation")
table(["Element", "Definition"], [
    ["Decision variable x_{i}", "1 if relative i is tested in this visit, otherwise 0"],
    ["Pair weight w_{ij}", "Probability that i and j are both carriers, computed from the family tree"],
    ["Link strength c_{ij}", "Probability that the couple link is real: 1 for married or engaged couples, lower for a "
                             "possible future match between unmarried cousins"],
    ["Single weight p_{i}", "Probability that i is a carrier"],
    ["Relevance r_{i}", "How much knowing matters: 1.0 unmarried or engaged adult, 0.7 married adult, 0.5 child, "
                        "0.1 elder"],
    ["Objective", "Expected number of at-risk couples found, plus λ = %.2f times the relevance-weighted number "
                  "of carriers found" % META["lambda"]],
    ["Constraint", "Exactly k people are tested. Relatives who are absent or decline are fixed to 0"],
], widths=[4.2, 12.2], caption="Table 1. Decision variables, objective and constraint.")
p = para("", align="center", after=2, before=2)
rich(p, "maximise   F(x) = ∑_{(i,j) ∈ C} c_{ij} w_{ij} x_{i} x_{j}  +  λ ∑_{i} r_{i} p_{i} x_{i}"
        "      subject to   ∑_{i} x_{i} = k,   x_{i} ∈ {0, 1}", size=12)
for run in p.runs:
    run.font.name = "Cambria Math"
para("", after=2)
para("The first term is not a proxy. For a married or engaged couple it is exactly the probability that the visit "
     "identifies them as an at-risk couple: both tested and both carriers. For a possible future match the term is "
     "multiplied by c_{ij}, the probability that the match happens; each unmarried person marries at most one cousin, "
     "so the first-cousin marriage rate of 0.5 is shared equally among the eligible cousins. The second term is a "
     "small reward for each single carrier found. The affected child and the two parents are not decision variables: "
     "the child is diagnosed and the parents are obligate carriers. No weight is negative, so using all k kits is "
     "never worse than using fewer, which is why the constraint is written as an equality. The objective counts "
     "confirmed at-risk couples only: the reassurance from a single negative test, which rules a couple out, is not "
     "valued.", align="justify")
para("**Where the weights come from.** A pedigree engine (`genetics.py`) treats the family tree as a Bayesian network "
     "over genotypes: one gene, standard recessive inheritance, founders in Hardy-Weinberg proportions for a 5% "
     "carrier rate. The affected child is known to have two copies and everyone else is known not to. The "
     "probabilities p_{i} and w_{ij} are computed exactly by variable elimination, which also handles the loops "
     "created by cousin marriages. Table 2 compares the engine with textbook values. The test suite also checks it "
     "against full enumeration of all 3^{10} genotype assignments on a family with a cousin marriage.",
     align="justify")
if MC:
    para(f"As a second, independent check, a Monte Carlo simulation that drops alleles down the tree and keeps only "
         f"the simulated families that match the evidence (`validate_genetics.py`) was compared with the engine on "
         f"{len(MC['cases'])} families. Over {MC['comparisons']} carrier and couple probabilities the largest deviation "
         f"is {MC['max_abs_z']:.1f} standard errors, and {pct(MC['share_above_2'])} of them lie beyond two standard "
         "errors, where about 5% is expected by chance.", align="justify")
rows = []
for c in GEN["checks"]:
    textbook = c["textbook"] + (f" (exact: {c['formula']})" if c.get("formula") else "")
    rows.append([c["relation"], textbook, f"{c['computed']:.4f}"])
table(["Relative of the affected child", "Textbook value", "Engine"], rows, widths=[7.4, 6.0, 3.0],
      align=["l", "l", "r"], caption="Table 2. Pedigree engine against textbook values (q is the allele frequency, "
                                     f"{GEN['allele_frequency']:.4f}).")
para(f"The last row is the reason the problem is quadratic. Each grandparent alone is a carrier with probability "
     f"{checks['Grandparent']['computed']:.3f}, but both together only with probability "
     f"{checks['Both grandparents carriers (joint)']['computed']:.3f}, because the father's single copy almost surely "
     "came from one of them. Pair values cannot be assembled from single-person probabilities.", align="justify")
para("**Test instances.** All families are synthetic and seeded (`pedigree.py`); no patient data is used. The generator "
     "builds three or four generations around one affected child. With probability 0.6 the parents are first cousins, "
     "with probability 0.4 one paternal and one maternal sibling are married to each other (an exchange marriage), "
     "and unmarried cousins of opposite sex are linked as engaged or as possible matches.", align="justify")
table(["Size", "Relatives (qubits)", "Kits k", "Valid plans", "Used for"], [
    ["S", "10", "4", "210", "brute force, noise study, worked example"],
    ["M", "16", "5", "4,368", "main simulator results, trade-off curve"],
    ["L", "48 in 4 linked families", "12", "about 7 × 10^{10}", "exact integer programme, decomposition"],
], widths=[1.3, 4.2, 1.6, 2.9, 6.4], align=["l", "r", "r", "r", "l"], caption="Table 3. Seeded test instances.")
para(f"**Calibration.** Across {CAL['families']} synthetic families the average carrier probability among testable "
     f"relatives is {pct(CAL['carrier_share_candidates'])}, against 31% of tested relatives in [1]. Among married "
     f"couples other than the index parents the average probability that both are carriers is "
     f"{pct(CAL['couples_both_carriers_excluding_index_parents'], 1)}; counting the index parents it is "
     f"{pct(CAL['couples_both_carriers_all_married'])}, against 8% of all married couples in the much larger "
     "families of [1]. The calibration is approximate and is listed as a limitation.", align="justify")
para("**Measures.** Every method is scored against the exact optimum by four numbers: *quality*, the expected value of "
     "a measured valid plan scaled so that the worst valid plan is 0 and the best is 1 (shots that break the kit "
     "limit are discarded first); the *probability that one shot is the best plan*, counted over all shots; the "
     "*share of shots that use exactly k kits*; and the value of a plan divided by the optimum.", align="justify")

# --------------------------------------------------------------------------
# 3. Quantum method
# --------------------------------------------------------------------------
heading("3. Quantum method")
table(["Problem piece", "Quantum piece", "Qiskit building block"], [
    ["Is relative i tested?", "Qubit i; state |1> means tested", "`QuantumCircuit`"],
    ["Couple weight c_{ij} w_{ij}", "ZZ rotation on qubits i and j", "`rzz`, `SparsePauliOp`"],
    ["Single weight", "Z rotation on qubit i", "`rz`"],
    ["Exactly k tests", "Dicke start state and XY ring mixer", "`cx`, `cry`, `ry`, `XXPlusYYGate`"],
    ["Tuning the angles", "Classical optimiser loop", "Aer `EstimatorV2` with SciPy COBYLA"],
    ["Reading out plans", "Sampling the circuit", "Aer `SamplerV2`"],
], widths=[4.6, 5.9, 5.9], caption="Table 4. How the problem is represented in the algorithm.")
para("**Mapping.** With x_{i} = (1 - z_{i}) / 2 the objective becomes F = const + ∑_{i} a_{i} z_{i} + "
     "∑_{i<j} b_{ij} z_{i} z_{j}, with b_{ij} = c_{ij} w_{ij} / 4 and a_{i} = -λ r_{i} p_{i} / 2 - "
     "∑_{j} c_{ij} w_{ij} / 4. The cost layer applies RZZ(2γ b_{ij}) on every couple link and "
     "RZ(2γ a_{i}) on every qubit; coefficients are divided by their root mean square so that useful angles are "
     "of order one. A test confirms that the Estimator energy of each of the 2^{n} basis states equals the objective "
     "of that plan, and that the cost layer is the diagonal matrix exp(-iγF), up to a global phase and the "
     "scale factor.", align="justify")
para("**Why QAOA.** The objective is a sum over pairs of yes-or-no decisions, which is the form QAOA encodes natively "
     "[7]: one two-qubit rotation per couple link and no helper qubits. The algorithm is hybrid and shallow, so it "
     "runs on a simulator at our sizes. The exactly-k rule fits the quantum alternating operator ansatz, in which the "
     "start state and the mixer keep the state inside the feasible set [8].", align="justify")
para("**Constrained QAOA, the main method.** The start state is the Dicke state, the equal superposition of all "
     "C(n, k) plans with exactly k ones. Qiskit 2.6 has no built-in Dicke state, so `circuits.py` builds it from gates "
     "with the deterministic scheme of Bärtschi and Eidenbenz [6] (order kn gates, no helper qubits), using CNOT, "
     "controlled RY and a doubly controlled RY written with four CNOTs. The mixer is a ring of XX+YY rotations applied "
     "in parity order [9]. Each rotation swaps a tested and an untested neighbour, so the number of ones, and with it "
     "the number of kits, never changes. The design follows Cook, Eidenbenz and Bärtschi [5]. Tests confirm that the "
     "circuit prepares the Dicke state exactly for sizes up to n = 10 and that no probability leaves the valid plans.",
     align="justify")
para("**Penalty QAOA, the baseline.** Standard QAOA starts from the uniform superposition over all 2^{n} bitstrings, "
     "uses RX mixers and subtracts A(∑_{i} x_{i} - k)^{2} from the objective. A is set to 1.1 times the largest "
     "gain any single extra test can bring, which is enough to keep the constrained optimum as the global optimum of "
     "the penalised function (checked by a test). The penalty needs a ZZ rotation on every pair of qubits.",
     align="justify")
para("**Training and read-out.** Angles are tuned by SciPy's COBYLA on expectation values from the Aer Estimator "
     "primitive. Depth 1 starts from a 16 by 10 grid over the two angles. Depth p + 1 starts from the tuned depth-p "
     "angles, once stretched by the INTERP rule [10] and once with an added identity layer, so a deeper circuit never "
     "starts worse than the shallower one. Plans are read out with the Aer Sampler primitive (4,096 shots); the best "
     "measured valid plan is the one handed to the field officer. Exact statevector probabilities are used only to "
     "report metrics without shot noise. The quantum computation is therefore material: the delivered plan is a "
     "measured bitstring of the circuit.", align="justify")
para("**How hard is the problem?** With equal weights it is the densest-k-subgraph problem, which is NP-hard; the best "
     "known polynomial-time algorithm guarantees only a factor of about n^{1/4} [12]. Stronger conditional hardness "
     "results exist [13], but their author revised the underlying complexity assumption in 2026, so we do not lean on "
     "them. These are worst-case statements about general graphs, and section 6 reports that our family graphs are far "
     "from the worst case.", align="justify")
para("**Assumptions and limits of the quantum part.** Results are noise-free statevector simulations unless stated. "
     "Depth is limited to p = 3. No error mitigation is used. The noise study assumes all-to-all connectivity. No real "
     "quantum processor was used.", align="justify")

# --------------------------------------------------------------------------
# 4. Architecture and implementation
# --------------------------------------------------------------------------
heading("4. Architecture and implementation")
para("Classical code prepares the weights, tunes the circuit and checks the answers. The quantum circuit is the step "
     "that proposes screening plans (Figure 1).", align="justify")
figure(ROOT / "report" / "architecture.png", "Figure 1. System architecture in eight parts. Part 5 is the quantum "
       "component, built, tuned and sampled through Qiskit primitives.")
table(["Module", "Role"], [
    ["`kinship/pedigree.py`", "Seeded synthetic families with cousin and exchange marriages; layout for drawing"],
    ["`kinship/genetics.py`", "Exact carrier and couple probabilities by variable elimination"],
    ["`kinship/problem.py`", "Objective, exactly-k rule, QUBO and Ising mapping, instance files"],
    ["`kinship/classical.py`", "Brute force, integer programme (HiGHS via SciPy), field rule, greedy, simulated annealing"],
    ["`kinship/quantum/circuits.py`", "Dicke state, cost layer, XY ring mixer, both QAOA circuits"],
    ["`kinship/quantum/qaoa.py`", "Angle tuning with the Estimator, read-out with the Sampler, metrics"],
    ["`kinship/quantum/noise.py`", "Transpilation to RZ, SX, X, CZ and the Aer noise model"],
    ["`kinship/decompose.py`", "Split along the couple graph; dynamic programme over kit budgets"],
    ["`kinship/evaluate.py`, `plots.py`", "Experiment runner with fixed seeds; every figure from saved results"],
    ["`kinship/validate_genetics.py`", "Independent Monte Carlo check of the genetics engine"],
    ["`kinship/demo.py`", "One-command demonstration on one family"],
    ["`kinship/compare_runs.py`", "Compares the result files of two runs, ignoring timing fields"],
    ["`tests/`", "57 checks: genetics values, objective, Ising mapping, circuits, decomposition"],
], widths=[5.4, 11.0], caption="Table 5. Modules of the repository.")
para("**How to run.** With Python 3.11 or later:", after=3)
code(["pip install -r requirements.txt",
      "python -m kinship.demo            # one family, one plan, about 20 seconds",
      "python -m kinship.evaluate all    # every number in this report",
      "python -m kinship.plots           # every figure",
      "pytest                            # 57 checks"])
para(f"**Reproducibility.** Versions are pinned, seeds are fixed, raw results are saved as JSON, and the figures, the "
     f"website data and this report are generated from those files by scripts. The full experiment matrix took "
     f"{total_seconds / 60:.0f} minutes on {META['workers']} processes of a laptop, and a second full run in a fresh "
     "clone of the repository reproduced every value in the result files. **Interpretable output.** The demo "
     "prints the plan in plain language, names the relatives to test, reports the expected number of at-risk couples "
     "found and its percentage of the best plan, and draws the family tree with the chosen relatives highlighted "
     "(section 5.3).", align="justify")

# --------------------------------------------------------------------------
# 5. Results
# --------------------------------------------------------------------------
heading("5. Results")
heading("5.1 The problem is not trivial", level=2)
rows = []
for size in ("S", "M"):
    for key, label in (("field", "Field officer's rule"), ("relevance", "Relevance-weighted rule"),
                       ("greedy", "Greedy"), ("annealing", "Simulated annealing")):
        s = G[size][key]
        rows.append([f"{size} ({G[size]['n']} relatives, {G[size]['k']} kits)", label,
                     pct(s["ratio"]["mean"]), pct(s["ratio"]["min"]), pct(s["miss_rate"])])
table(["Size", "Rule", "Value / optimum, mean", "Worst family", "Misses the best plan"], rows,
      widths=[4.4, 4.6, 3.0, 2.2, 2.2], align=["l", "l", "r", "r", "r"],
      caption=f"Table 6. Classical rules against the exact optimum on {R['gate1']['n_instances']} seeded families per size.")
para(f"The field officer's rule missed the best plan in {pct(G['S']['field']['miss_rate'])} of the 10-relative families "
     f"and in {pct(G['M']['field']['miss_rate'])} of the 16-relative families. It spends kits on grandparents and "
     "siblings whose partners are not tested. Weighting by relevance helps a little. Greedy selection does much better, "
     "and simulated annealing with swap moves finds the best plan in almost every family (Figure 2). On average "
     f"{pct(G['S']['couple_share_of_optimum']['mean'])} (10 relatives) and "
     f"{pct(G['M']['couple_share_of_optimum']['mean'])} (16 relatives) of the best plan's value comes from the couple "
     "term. The "
     f"rule breaks ties in carrier probability arbitrarily, and a tie at the cut-off occurs in "
     f"{TIE_S['families_with_tie']} and {TIE_M['families_with_tie']} of the {R['gate1']['n_instances']} families. Even "
     f"with every tie broken in its favour the rule reaches only {pct(TIE_S['best_ratio']['mean'])} and "
     f"{pct(TIE_M['best_ratio']['mean'])} of the best value and misses the best plan in "
     f"{pct(TIE_S['best_miss_rate'])} and {pct(TIE_M['best_miss_rate'])} of the families. Greedy is more fragile: its "
     f"first pick sees no couple yet, and breaking ties the other way changes its result in "
     f"{GT_S['families_changed']} and {GT_M['families_changed']} of the {R['gate1']['n_instances']} families, by up to "
     f"{pct(max(GT_S['largest_change'], GT_M['largest_change']))} of the best value (mean "
     f"{pct(GT_S['other_ratio']['mean'])} and {pct(GT_M['other_ratio']['mean'])} instead of "
     f"{pct(G['S']['greedy']['ratio']['mean'])} and {pct(G['M']['greedy']['ratio']['mean'])}).", align="justify")
figure(FIG / "fig02_field_rule_gap.png", "Figure 2. Value of each rule's plan divided by the best plan. One dot per "
       "seeded family; the black bar and the number are the mean.")

heading("5.2 QAOA against the references", level=2)
rows = []
for size in ("S", "M"):
    for method, label in (("random", "Random valid plan"), ("field", "Field officer's rule"), ("greedy", "Greedy"),
                          ("annealing", "Simulated annealing")):
        b = bench(size, method)
        rows.append([size, label, "", f"{b['quality']['mean']:.3f}",
                     pct_small(b["p_opt"]["mean"]) if "p_opt" in b else "", "100%",
                     f"{b['shots_95']['median']:,.0f}" if "shots_95" in b else ""])
    for method, label in (("constrained", "**Constrained QAOA**"), ("penalty", "Penalty QAOA")):
        for depth in (1, 2, 3):
            b = bench(size, method, depth)
            rows.append([size, label, str(depth), f"{b['quality']['mean']:.3f} ± {b['quality']['std']:.3f}",
                         pct_small(b["p_opt"]["mean"]), pct(b["valid_share"]["mean"]),
                         f"{b['shots_95']['median']:,.0f}"])
table(["Size", "Method", "p", "Quality", "Best plan per shot", "Valid shots", "Shots for 95%"], rows,
      widths=[1.1, 4.6, 0.9, 3.4, 2.5, 1.9, 2.0], align=["l", "l", "r", "r", "r", "r", "r"], size=8.5,
      caption=f"Table 7. Mean over {cS3['instances']} size-S and {cM3['instances']} size-M families, noise-free. "
              "Quality: 0 = worst valid plan, 1 = best, computed over valid shots. Best plan per shot: counted over "
              "all shots. Shots for 95%: shots needed to see the best plan with 95% probability (median).")
para(f"Constrained QAOA improves with depth on both sizes (Figures 3 and 4). At depth 3 its quality is "
     f"{cS3['quality']['mean']:.2f} on 10 qubits and {cM3['quality']['mean']:.2f} on 16 qubits, against "
     f"{rS['quality']['mean']:.2f} and {rM['quality']['mean']:.2f} for a random valid plan and "
     f"{fS['quality']['mean']:.2f} and {fM['quality']['mean']:.2f} for the field officer's rule. The chance that one "
     f"shot is the best plan rises to {pct_small(cS3['p_opt']['mean'])} and {pct_small(cM3['p_opt']['mean'])}. Family "
     f"by family that is on average {cS3['p_opt_gain']['mean']:.0f} and {cM3['p_opt_gain']['mean']:.0f} times the "
     f"chance of a random valid pick, with medians of {cS3['p_opt_gain']['median']:.0f} and "
     f"{cM3['p_opt_gain']['median']:.0f} times, so a few families carry the mean. Every shot "
     "uses exactly k kits. In every instance the best of the 4,096 measured plans was the exact optimum; at these "
     "sizes that alone is a weak statement (section 6), which is why the table reports per-shot numbers.",
     align="justify")
para(f"Penalty QAOA learns the constraint before it learns the objective. Its share of valid shots grows from "
     f"{pct(pS1['valid_share']['mean'])} to {pct(pS3['valid_share']['mean'])} on 10 qubits and from "
     f"{pct(pM1['valid_share']['mean'])} to {pct(pM3['valid_share']['mean'])} on 16 qubits, but the quality of those "
     f"valid shots stays near random ({pS3['quality']['mean']:.2f} and {pM3['quality']['mean']:.2f}). Constrained QAOA "
     f"does not beat the stronger classical heuristics: greedy reaches {gS['quality']['mean']:.2f} and "
     f"{gM['quality']['mean']:.2f}, and simulated annealing finds the optimum in {pct(aS['optimal_share'])} and "
     f"{pct(aM['optimal_share'])} of these families.", align="justify")
figure(FIG / "fig03_quality_vs_depth.png", "Figure 3. Quality against QAOA depth. Whiskers: one standard deviation "
       "over families.", width=15.0)
figure(FIG / "fig04_probability_of_best_plan.png", "Figure 4. Probability that a single shot is the best plan "
       "(log scale).", width=15.0)

heading("5.3 A worked example", level=2)
fld = DEMO["plans"]["field"]
para(f"Figure 5 shows instance {DEMO['name']}, chosen by a fixed rule (the size-S instance with the largest optimum "
     f"among those with at least five couple links), not by QAOA performance. The field officer's rule tests "
     f"{', '.join(fld['labels'])}: {fld['couples']:.3f} expected at-risk couples, {pct(fld['ratio'])} of the best "
     f"plan. The best plan measured from the constrained QAOA circuit tests {', '.join(dq['best']['labels'])}: "
     f"{dq['best']['couples']:.3f} expected at-risk couples, which equals the exact optimum. One shot is the best "
     f"plan with probability {pct(dq['p_opt'], 1)}, against {pct(DEMO['random']['p_opt'], 2)} for a random valid plan.",
     align="justify")
figure(FIG / "fig01_pedigree_plans.png", "Figure 5. One family, two plans. The field rule tests people whose partners "
       "are not tested; the QAOA plan tests both partners of the possible matches between siblings and cousins.", width=13.4)

heading("5.4 Circuit cost", level=2)
rows = []
for size in ("S", "M"):
    d = circ(size, "dicke_only", 0)
    rows.append([f"{size} ({d['n']} qubits)", "Dicke start state alone", "", str(d["two_qubit"]), str(d["depth"]),
                 str(circ(size, "dicke_only", 0, line=True)["two_qubit"])])
    for method, label in (("constrained", "Constrained QAOA"), ("penalty", "Penalty QAOA")):
        for depth in (1, 3):
            c = circ(size, method, depth)
            rows.append([f"{size} ({c['n']} qubits)", label, str(depth), str(c["two_qubit"]), str(c["depth"]),
                         str(circ(size, method, depth, line=True)["two_qubit"])])
table(["Size", "Circuit", "p", "CZ gates, all-to-all", "Depth", "CZ gates, line of qubits"], rows,
      widths=[2.8, 4.8, 0.9, 3.0, 1.6, 3.3], align=["l", "l", "r", "r", "r", "r"],
      caption="Table 8. Circuit size after transpilation to RZ, SX, X, CZ at optimisation level 3 (first instance of "
              "each size).")
cS1, cS3c, pS1c, pS3c = (circ("S", "constrained", 1), circ("S", "constrained", 3), circ("S", "penalty", 1),
                         circ("S", "penalty", 3))
cM1, cM3c, pM1c, pM3c = (circ("M", "constrained", 1), circ("M", "constrained", 3), circ("M", "penalty", 1),
                         circ("M", "penalty", 3))
para(f"The constrained circuit pays a fixed price for its start state: {circ('S', 'dicke_only', 0)['two_qubit']} CZ "
     f"gates on 10 qubits and {circ('M', 'dicke_only', 0)['two_qubit']} on 16. After that each layer is cheap, about "
     f"{(cS3c['two_qubit'] - cS1['two_qubit']) // 2} and {(cM3c['two_qubit'] - cM1['two_qubit']) // 2} CZ gates, "
     f"against {(pS3c['two_qubit'] - pS1c['two_qubit']) // 2} and {(pM3c['two_qubit'] - pM1c['two_qubit']) // 2} for "
     f"the penalty circuit, which needs a rotation on every pair of qubits. With all-to-all connectivity the "
     f"constrained circuit therefore has fewer CZ gates at depth 3 on 16 qubits ({cM3c['two_qubit']} against "
     f"{pM3c['two_qubit']}), but it is about twice as deep ({cM3c['depth']} against {pM3c['depth']} layers), and on a "
     f"line of qubits it also needs more CZ gates ({circ('M', 'constrained', 3, line=True)['two_qubit']:,} against "
     f"{circ('M', 'penalty', 3, line=True)['two_qubit']:,}).", align="justify")

heading("5.5 Under noise", level=2)
para(f"We ran the 10-qubit circuits on Aer with a depolarising error after every CZ gate, a tenth of that on "
     f"single-qubit gates and a readout error at twice the CZ rate ({R['noise']['instances']} families, "
     f"{R['noise']['shots']:,} shots). The error rates quoted are the depolarising probability of the CZ gate. "
     "Shots without exactly k ones are discarded and the surviving share is reported (Figure 6). For constrained QAOA "
     f"at depth 1 the share of valid shots falls from 100% to {pct(n5c['valid_share']['mean'])} at 0.1% error and "
     f"to {pct(n1c['valid_share']['mean'])} at 1%; the quality of the surviving shots falls from "
     f"{n0c['quality']['mean']:.2f} to {n1c['quality']['mean']:.2f}, and the chance of the best plan from "
     f"{pct_small(n0c['p_opt']['mean'])} to {pct_small(n1c['p_opt']['mean'])}, the level of a random valid pick "
     f"({pct_small(n0c['random_p_opt']['mean'])}). Penalty QAOA is shallower but starts from "
     f"{pct(noise('penalty', 1, 0.0)['valid_share']['mean'])} valid shots and its quality stays close to the random "
     f"level throughout ({n1p['quality']['mean']:.2f} at 1% error against "
     f"{n1p['random_quality']['mean']:.2f} for a random valid plan). These numbers come from sampled shots on "
     f"{R['noise']['instances']} families, so they differ slightly from the exact {cS3['instances']}-family values of "
     "Table 7. No real quantum processor was used.", align="justify")
figure(FIG / "fig06_noise.png", "Figure 6. Noise sweep on the 10-qubit instances: valid shots, quality of valid "
       "shots, and chance of the best plan.")

heading("5.6 Trade-off curve and linked families", level=2)
para(f"**Couples against carriers.** Sweeping λ over {len(TR['lambdas'])} values trades at-risk couples found "
     f"against single carriers found. On instance {TR['instance']} (chosen by a fixed rule: the largest exact front "
     f"among the size-M instances) the exact trade-off front has {TR['front_points']['exact']} plans. The "
     f"{TR['total_shots']:,} QAOA shots of the sweep contained {TR['front_points']['qaoa_found']} of them and covered "
     f"{pct(TR['hypervolume']['qaoa_ratio'], 1)} of the area under the front; uniform random sampling of valid plans "
     f"with the same number of shots found {TR['front_points']['random_found_mean']:.1f} on average and covered "
     f"{pct(TR['hypervolume']['random_ratio_mean'], 1)} (Figure 7). The idea of approximating a front from QAOA "
     "samples follows [11]. This is one instance, so it is an illustration and not a general claim.", align="justify")
r0 = DEC["rows"][0]
para(f"**Linked families.** One qubit per relative limits a single circuit to roughly 25 to 30 people on a simulator. "
     "People in different connected components of the couple graph interact only through the kit budget, so a large "
     "network splits exactly. QAOA is run on every component with at least three people, for every budget that "
     "leaves a real choice; pairs and people without couple links are handled in closed form; and a dynamic programme "
     "shares out the kits. "
     f"On {DEC['instances']} networks of {r0['n']} relatives and {r0['k']} kits the largest component had {max_q} "
     f"people, so no circuit needed more than {max_q} qubits; QAOA ran {dec_runs} times, and "
     + ("every network reached the optimum proven by an integer programme" if dec_all_opt else
        "not every network reached the proven optimum")
     + f" (Figure 8). The field officer's rule reached {pct(DEC['summary']['field']['mean'])} and greedy "
     f"{pct(DEC['summary']['greedy']['mean'])}. At this component size sampling finds each optimum easily, so the result "
     "shows a scaling route and not an advantage.", align="justify")
figures_side_by_side([
    (FIG / "fig07_tradeoff.png", "Figure 7. Couples found against carriers found."),
    (FIG / "fig09_decomposition.png", "Figure 8. Linked families: value divided by the proven optimum."),
])

# --------------------------------------------------------------------------
# 6. Limitations
# --------------------------------------------------------------------------
heading("6. Limitations and what did not work")
bullets([
    f"**No quantum speedup.** Brute force gives the exact answer for the 10- and 16-qubit instances in milliseconds, and "
    f"simulated annealing found the best plan in {pct(aM['optimal_share'])} of the 16-qubit families. At these sizes a "
    "classical solver wins. This is a method study on a new problem.",
    f"**The hybrid loop is expensive.** Tuning the angles for one 16-qubit family took about {TRAIN_EVALS:.0f} "
    "expectation evaluations, each of which would itself need thousands of shots on a real device, to choose among "
    "4,368 plans that brute force lists directly.",
    f"**Family graphs are sparse.** The couple graph splits into small pieces: its largest connected component has "
    f"{G['M']['largest_component']['mean']:.1f} people on average in the 16-relative families (at most "
    f"{G['M']['largest_component']['max']:.0f}). An exact dynamic programme over those pieces solves the problem, so "
    "worst-case hardness results for densest-k-subgraph do not apply to these instances. A denser match graph, for "
    "example a large group of unmarried cousins, would be harder.",
    f"**Expected quality is modest.** At depth 3 constrained QAOA reaches {cM3['quality']['mean']:.2f} on 16 qubits "
    f"while greedy reaches {gM['quality']['mean']:.2f}. QAOA beats the field rule and random picks, not the stronger "
    "classical heuristics.",
    f"**Penalty QAOA barely beats random.** Its valid shots score {pM3['quality']['mean']:.2f} against "
    f"{rM['quality']['mean']:.2f} for a random valid plan on 16 qubits, and {pct(1 - pM3['valid_share']['mean'])} of "
    "its shots break the kit limit at depth 3. We did not tune the penalty weight beyond the principled choice in "
    "section 3.",
    f"**A cheaper start state failed.** Starting from the field officer's plan instead of the Dicke state needs only k "
    f"X gates, but at depth 3 its chance of the best plan was {pct_small(ABL[('field', 3)]['p_opt']['mean'])} against "
    f"{pct_small(ABL[('dicke', 3)]['p_opt']['mean'])} for the Dicke start, and its quality "
    f"{ABL[('field', 3)]['quality']['mean']:.2f} against {ABL[('dicke', 3)]['quality']['mean']:.2f} "
    f"({R['ablation']['instances']} size-S instances). The ring mixer cannot spread one basis state far in three layers.",
    f"**Noise costs most of the shots.** The Dicke start state alone needs {circ('S', 'dicke_only', 0)['two_qubit']} CZ "
    f"gates on 10 qubits. At 1% two-qubit error only {pct(n1c['valid_share']['mean'])} of constrained shots still "
    "use exactly k kits and the chance of the best plan is back at the random level.",
    f"**Simulator only, generic noise.** No real quantum processor was used. The noise model is a uniform depolarising "
    f"model with all-to-all connectivity; on a line of qubits the depth-1 circuit grows from "
    f"{circ('S', 'constrained', 1)['two_qubit']} to {circ('S', 'constrained', 1, line=True)['two_qubit']} CZ gates.",
    "**Sampling flatters small instances.** With 4,096 shots and only 210 or 4,368 valid plans, even uniform sampling "
    "usually contains the best plan. We therefore report the chance per shot and the expected quality, not the best of "
    "all shots.",
    f"**Synthetic families and simple genetics.** Families are generated, not observed, and calibrated loosely to one "
    f"study from 2002 ({pct(CAL['carrier_share_candidates'])} carriers among testable relatives against 31%). The "
    "model has one gene, standard inheritance and a perfect test. The relevance weights and match probabilities are our "
    "assumptions and were not reviewed by a practitioner.",
    "**One visit only.** The model chooses everyone before any result is known. Real programmes may test one partner "
    "first and the other only if the first is a carrier; step-by-step testing is the natural next model.",
    "**Assumed constraint and baseline.** We assume that the kit budget of a visit is the binding limit; laboratory "
    "slots, officer time or the willingness of relatives may bind instead. The field officer's rule is our stand-in "
    "for an unaided choice, not a documented programme protocol.",
])

# --------------------------------------------------------------------------
# 7. Ethics
# --------------------------------------------------------------------------
heading("7. Ethics")
para("A tool that ranks relatives by genetic risk can stigmatise people, and carrier status is sensitive in a society "
     "where it can affect marriage prospects. This project uses synthetic data only. Consent is an input of the model: "
     "anyone who declines is fixed to not tested. The tool produces a plan for one visit to support a counsellor, "
     "publishes no individual scores, and is not meant to decide who may marry. Any real use would need the approval "
     "of the screening programme and of an ethics committee, and data protection for the family trees.",
     align="justify")

# --------------------------------------------------------------------------
# 8. Credits and references
# --------------------------------------------------------------------------
heading("8. Credits and references")
para(f"**Software.** Qiskit {META['qiskit']}, Qiskit Aer {META['qiskit_aer']}, NumPy {META['numpy']}, SciPy "
     f"{META['scipy']} (COBYLA and the HiGHS integer programme), Matplotlib, python-docx, pytest; Python "
     f"{META['python']}.", align="justify")
para("**Methods.** The constrained QAOA design (Dicke start state, XY mixer) follows [5]; the Dicke-state circuit "
     "follows [6]; the parity-ordered ring mixer follows [9]; the INTERP warm start follows [10]; the trade-off sweep "
     "borrows the idea of [11]. The circuits were written from the papers. No tutorial or third-party code was copied "
     "into the repository.", align="justify")
para("**AI assistance.** An AI coding assistant was used to help write code and draft text. Every number in this "
     "report is produced by running the code in the repository.", align="justify")
references = [
    "Ahmed S, Saleem M, Modell B, Petrou M. Screening extended families for genetic hemoglobin disorders in Pakistan. "
    "N Engl J Med. 2002;347(15):1162-1168. doi:10.1056/NEJMsa013234",
    "Ahmed S, Jafri H, Faran M, Ahmed WN, Rashid Y, Ehsan Y, Ahmed M. Cascade screening for beta-thalassaemia in "
    "Pakistan: relatives' experiences of a decision support intervention in routine practice. Eur J Hum Genet. "
    "2022;30(4):406-412. doi:10.1038/s41431-021-00974-y",
    "National Institute of Population Studies and ICF. Pakistan Demographic and Health Survey 2017-18. Islamabad and "
    "Rockville; 2019. Figures as reported in Iqbal S, Zakar R, Fischer F, Zakar MZ. BMC Women's Health. 2022;22:118. "
    "doi:10.1186/s12905-022-01704-2",
    "Dawn, 11 March 2026: report on the National Assembly passing the Islamabad Capital Territory compulsory "
    "thalassaemia screening bill, dawn.com/news/1980653. Associated Press of Pakistan, 11 May 2026: report on its "
    "passage by the Senate, app.com.pk/national/5-private-member-bills-smoothly-sail-through-senate. Presidential "
    "assent could not be confirmed at the time of writing.",
    "Cook J, Eidenbenz S, Bärtschi A. The Quantum Alternating Operator Ansatz on Maximum k-Vertex Cover. IEEE "
    "International Conference on Quantum Computing and Engineering (QCE) 2020, 83-92. arXiv:1910.13483",
    "Bärtschi A, Eidenbenz S. Deterministic Preparation of Dicke States. Fundamentals of Computation Theory (FCT) "
    "2019, Lecture Notes in Computer Science, 126-139. arXiv:1904.07358",
    "Farhi E, Goldstone J, Gutmann S. A Quantum Approximate Optimization Algorithm. 2014. arXiv:1411.4028",
    "Hadfield S, Wang Z, O'Gorman B, Rieffel EG, Venturelli D, Biswas R. From the Quantum Approximate Optimization "
    "Algorithm to a Quantum Alternating Operator Ansatz. Algorithms. 2019;12(2):34. doi:10.3390/a12020034",
    "Wang Z, Rubin NC, Dominy JM, Rieffel EG. XY mixers: analytical and numerical results for the quantum alternating "
    "operator ansatz. Phys Rev A. 2020;101:012320. arXiv:1904.09314",
    "Zhou L, Wang S-T, Choi S, Pichler H, Lukin MD. Quantum Approximate Optimization Algorithm: Performance, "
    "Mechanism, and Implementation on Near-Term Devices. Phys Rev X. 2020;10:021067. arXiv:1812.01041",
    "Kotil A, Pelofske E, Riedmüller S, Egger DJ, Eidenbenz S, Koch T, Woerner S. Quantum approximate multi-objective "
    "optimization. Nat Comput Sci. 2025;5:1168-1177. arXiv:2503.22797",
    "Bhaskara A, Charikar M, Chlamtac E, Feige U, Vijayaraghavan A. Detecting high log-densities: an O(n^1/4) "
    "approximation for densest k-subgraph. STOC 2010, 201-210. arXiv:1001.2891",
    "Manurangsi P. Almost-polynomial ratio ETH-hardness of approximating densest k-subgraph. STOC 2017, 954-961. "
    "arXiv:1611.05991. The arXiv version was revised in October 2026 and now states the result under a different "
    "assumption, which is why we do not rely on it.",
]
for i, ref in enumerate(references, start=1):
    p = para(f"[{i}]  {ref}", size=8.5, after=2)
    p.paragraph_format.left_indent = Cm(0.9)
    p.paragraph_format.first_line_indent = Cm(-0.9)

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print("wrote", OUT.relative_to(ROOT))
