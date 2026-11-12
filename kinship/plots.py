"""Figures for the report and the README. Every figure is built from results/*.json.

    python -m kinship.plots
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"

# One colour per method, the same in every figure and on the website.
BLUE, ORANGE, AQUA, YELLOW, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6"
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
COLORS = {"constrained": BLUE, "penalty": ORANGE, "field": AQUA, "relevance": YELLOW,
          "greedy": VIOLET, "annealing": INK2, "random": MUTED, "exact": INK}
NAMES = {"constrained": "Constrained QAOA", "penalty": "Penalty QAOA", "field": "Field officer's rule",
         "relevance": "Relevance-weighted rule", "greedy": "Greedy", "annealing": "Simulated annealing",
         "random": "Random valid plan", "exact": "Exact optimum", "decomposed_qaoa": "Decomposition + QAOA"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelsize": 9, "axes.labelcolor": INK2, "axes.edgecolor": AXIS,
    "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "legend.frameon": False, "legend.fontsize": 8,
    "figure.dpi": 100, "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.facecolor": "white",
    "lines.linewidth": 2.0, "lines.markersize": 6,
})


def load(name: str):
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def _save(fig, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def short_label(label: str) -> str:
    table = {"Paternal grandfather": "PGF", "Paternal grandmother": "PGM",
             "Maternal grandfather": "MGF", "Maternal grandmother": "MGM",
             "Great-grandfather": "GGF", "Great-grandmother": "GGM"}
    if label in table:
        return table[label]
    if label.startswith("Wife of"):
        return "Wife"
    if label.startswith("Husband of"):
        return "Husband"
    return label.replace("Paternal", "P.").replace("Maternal", "M.")


def _direct_labels(ax, x, items, min_gap, log=False):
    """Write labels at the right of a chart, pushed apart so that they never overlap."""
    pts = sorted(((np.log10(y) if log else y, text, color) for y, text, color in items), key=lambda t: t[0])
    placed = []
    for y, text, color in pts:
        if placed and y - placed[-1][0] < min_gap:
            y = placed[-1][0] + min_gap
        placed.append((y, text, color))
    for y, text, color in placed:
        ax.text(x, 10 ** y if log else y, text, color=color, va="center", fontsize=8)


# --------------------------------------------------------------------------
# pedigree
# --------------------------------------------------------------------------
def draw_pedigree(ax, demo: dict, chosen: list[int], title: str, color: str, subtitle: str = "") -> None:
    people = {p["id"]: p for p in demo["people"]}
    xs = [p["x"] for p in people.values()]
    n_wide = max(sum(1 for p in people.values() if p["y"] == g) for g in (0, 1, 2, 3))
    sx = max(n_wide * 1.15, 8.0)

    def pos(pid):
        return people[pid]["x"] * sx, -people[pid]["y"] * 1.9

    r = 0.3
    kids: dict[tuple[int, int], list[int]] = {}
    for p in people.values():
        if p["father"] is not None:
            kids.setdefault((p["father"], p["mother"]), []).append(p["id"])
    for (fa, mo), ch in kids.items():
        (x1, y1), (x2, y2) = pos(fa), pos(mo)
        ax.plot([x1, x2], [y1, y2], color=AXIS, lw=1.1, zorder=1)
        mx, bar_y = (x1 + x2) / 2, y1 - 0.95
        cx = [pos(c)[0] for c in ch]
        ax.plot([mx, mx], [y1, bar_y], color=AXIS, lw=1.1, zorder=1)
        ax.plot([min(cx + [mx]), max(cx + [mx])], [bar_y, bar_y], color=AXIS, lw=1.1, zorder=1)
        for c in ch:
            ax.plot([pos(c)[0]] * 2, [bar_y, pos(c)[1] + r], color=AXIS, lw=1.1, zorder=1)
    for c in demo["couples"]:
        (x1, y1), (x2, y2) = pos(c["a"]), pos(c["b"])
        both = c["a"] in chosen and c["b"] in chosen
        if c["kind"] == "married":
            if both:
                ax.plot([x1, x2], [y1, y2], color=color, lw=3.2, zorder=2, solid_capstyle="round")
            elif (c["a"], c["b"]) not in kids and (c["b"], c["a"]) not in kids:
                ax.plot([x1, x2], [y1, y2], color=AXIS, lw=1.1, zorder=1)
            continue
        style = "--" if c["kind"] == "engaged" else ":"
        if x1 > x2:
            x1, y1, x2, y2 = x2, y2, x1, y1
        arc = FancyArrowPatch((x1, y1 + r), (x2, y2 + r), connectionstyle="arc3,rad=-0.22", arrowstyle="-",
                              linestyle=style, lw=2.6 if both else 1.2, color=color if both else MUTED, zorder=2)
        ax.add_patch(arc)
    for p in people.values():
        x, y = pos(p["id"])
        picked = p["id"] in chosen
        face, edge, lw = "white", INK2, 1.2
        if p["status"] == "affected":
            face, edge = INK, INK
        elif p["status"] == "obligate":
            face = "#d9d8d2"
        elif p["status"] in ("deceased", "unavailable"):
            face, edge = "#f1f0ec", AXIS
        if picked:
            face, edge, lw = color, color, 2.0
        shape = (Rectangle((x - r, y - r), 2 * r, 2 * r, facecolor=face, edgecolor=edge, lw=lw, zorder=3)
                 if p["sex"] == "M" else Circle((x, y), r, facecolor=face, edgecolor=edge, lw=lw, zorder=3))
        ax.add_patch(shape)
        if p["status"] == "deceased":
            ax.plot([x - r * 1.25, x + r * 1.25], [y - r * 1.25, y + r * 1.25], color=AXIS, lw=1.0, zorder=4)
        if p["qubit"] is not None:
            ax.text(x, y, f"{p['p']:.2f}".lstrip("0"), ha="center", va="center", fontsize=6.3,
                    color="white" if picked else INK2, zorder=5)
        ax.text(x, y - r - 0.12, short_label(p["label"]), ha="center", va="top", fontsize=5.6,
                color=INK if picked else INK2, fontweight="bold" if picked else "normal", zorder=5)
    ax.set_title(title, pad=17)
    if subtitle:
        ax.text(0.0, 1.005, subtitle, transform=ax.transAxes, fontsize=8, color=INK2, va="bottom")
    ax.set_xlim(min(xs) * sx - 0.8, max(xs) * sx + 0.8)
    ax.set_ylim(-max(p["y"] for p in people.values()) * 1.9 - 1.15, 0.7 - (min(p["y"] for p in people.values())) * 1.9)
    ax.set_aspect("equal")
    ax.axis("off")


def fig_pedigree() -> Path:
    demo = load("demo")
    fig, axes = plt.subplots(2, 1, figsize=(9.5, 8.2))
    fld = demo["plans"]["field"]
    qaoa = [q for q in demo["qaoa"] if q["method"] == "constrained"][-1]["best"]
    draw_pedigree(axes[0], demo, fld["chosen"], "Field officer's rule: test the highest carrier probabilities",
                  AQUA, f"expected at-risk couples found {fld['couples']:.3f}   |   {100 * fld['ratio']:.0f}% of the best plan")
    draw_pedigree(axes[1], demo, qaoa["chosen"], "Constrained QAOA plan (best measured plan, equal to the exact optimum)"
                  if qaoa["ratio"] > 1 - 1e-9 else "Constrained QAOA plan (best measured plan)",
                  BLUE, f"expected at-risk couples found {qaoa['couples']:.3f}   |   {100 * qaoa['ratio']:.0f}% of the best plan")
    legend = ["Squares are men, circles are women. Black: affected index child. Grey: parents (obligate carriers).",
              "Pale: absent or deceased. Numbers: carrier probability. Coloured: tested in this plan.",
              "Solid line: married. Dashed arc: engaged. Dotted arc: possible future match.",
              "GGF, GGM: great-grandparents. PGF, PGM, MGF, MGM: paternal and maternal grandparents."]
    fig.text(0.5, 0.0, chr(10).join(legend), fontsize=7, color=INK2, va="bottom", ha="center", linespacing=1.5)
    fig.subplots_adjust(hspace=0.16, bottom=0.085)
    return _save(fig, "fig01_pedigree_plans")


# --------------------------------------------------------------------------
# charts
# --------------------------------------------------------------------------
def fig_gate1() -> Path:
    g = load("gate1")
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.3), sharex=True)
    methods = ["random", "field", "relevance", "greedy", "annealing"]
    rng = np.random.default_rng(0)
    for ax, size in zip(axes, ("S", "M")):
        rows = [r for r in g["rows"] if r["size"] == size]
        for y, m in enumerate(methods):
            vals = np.array([r[f"{m}_ratio"] for r in rows])
            ax.scatter(vals, y + rng.uniform(-0.16, 0.16, len(vals)), s=13, color=COLORS[m], alpha=0.55,
                       linewidths=0, zorder=3)
            ax.plot([vals.mean()] * 2, [y - 0.32, y + 0.32], color=INK, lw=2, zorder=4)
            ax.text(1.04, y, f"{vals.mean():.2f}", va="center", fontsize=8, color=INK)
        ax.set_yticks(range(len(methods)), [NAMES[m] for m in methods])
        ax.set_xlim(0, 1.02)
        ax.set_xlabel("value of the plan / value of the best plan")
        ax.set_title(f"Size {size}: {g['summary'][size]['n']} relatives, {g['summary'][size]['k']} kits")
        ax.axvline(1.0, color=AXIS, lw=0.8)
        ax.grid(axis="y", visible=False)
        ax.invert_yaxis()
    axes[1].tick_params(labelleft=False)
    return _save(fig, "fig02_field_rule_gap")


def _summary(bench, size, method, key):
    rows = sorted([r for r in bench["summary"] if r["size"] == size and r["method"] == method], key=lambda r: r["p"] or 0)
    return [r["p"] for r in rows], np.array([r[key]["mean"] for r in rows]), np.array([r[key]["std"] for r in rows])


def fig_quality() -> Path:
    b = load("benchmark")
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.5), sharey=True)
    for ax, size in zip(axes, ("S", "M")):
        base = {r["method"]: r for r in b["summary"] if r["size"] == size and r["kind"] == "classical"}
        labels = []
        for m in ("constrained", "penalty"):
            p, mean, std = _summary(b, size, m, "quality")
            ax.errorbar(p, mean, yerr=std, color=COLORS[m], marker="o", capsize=3, elinewidth=1, zorder=3)
            labels.append((mean[-1], NAMES[m], INK))
        for m, ls in (("random", "--"), ("field", ":")):
            v = base[m]["quality"]["mean"]
            ax.axhline(v, color=COLORS[m], ls=ls, lw=1.5, zorder=2)
            labels.append((v, NAMES[m] + (" (dashed)" if m == "random" else " (dotted)"), INK2))
        _direct_labels(ax, 3.1, labels, 0.06)
        ax.set_xticks([1, 2, 3])
        ax.set_xlim(0.8, 4.75)
        ax.set_ylim(0, 1)
        ax.set_xlabel("QAOA depth p")
        n = base["random"]["instances"]
        ax.set_title(f"Size {size}: {base['random']['n']} qubits, {base['random']['k']} kits ({n} families)")
    axes[0].set_ylabel("quality score (0 = worst valid plan, 1 = best)")
    return _save(fig, "fig03_quality_vs_depth")


def fig_popt() -> Path:
    b = load("benchmark")
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.5))
    for ax, size in zip(axes, ("S", "M")):
        base = {r["method"]: r for r in b["summary"] if r["size"] == size and r["kind"] == "classical"}
        labels = []
        for m in ("constrained", "penalty"):
            p, mean, _ = _summary(b, size, m, "p_opt")
            ax.plot(p, 100 * mean, color=COLORS[m], marker="o", zorder=3)
            labels.append((100 * mean[-1], NAMES[m], INK))
        v = 100 * base["random"]["p_opt"]["mean"]
        ax.axhline(v, color=COLORS["random"], ls="--", lw=1.5)
        labels.append((v, NAMES["random"] + " (dashed)", INK2))
        _direct_labels(ax, 3.1, labels, 0.16, log=True)
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_xticks([1, 2, 3])
        ax.set_xlim(0.8, 4.75)
        ax.set_xlabel("QAOA depth p")
        ax.set_title(f"Size {size}: chance that one shot is the best plan")
    axes[0].set_ylabel("probability per shot (%, log scale)")
    return _save(fig, "fig04_probability_of_best_plan")


def fig_valid() -> Path:
    b = load("benchmark")
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    width, xs = 0.36, np.arange(3)
    for off, size, hatch in ((-width / 2, "S", None), (width / 2, "M", "///")):
        _, mean, _ = _summary(b, size, "penalty", "valid_share")
        bars = ax.bar(xs + off, 100 * mean, width - 0.03, color=ORANGE, hatch=hatch, edgecolor="white", linewidth=0.6,
                      label=f"Penalty QAOA, size {size}", zorder=3)
        for rect, v in zip(bars, mean):
            ax.text(rect.get_x() + rect.get_width() / 2, 100 * v + 1.5, f"{100 * v:.0f}%", ha="center", fontsize=8, color=INK)
    ax.axhline(100, color=BLUE, lw=2)
    ax.text(2.55, 102.5, "Constrained QAOA: 100% at every depth", color=INK, ha="right", va="bottom", fontsize=8)
    ax.set_xticks(xs, ["p = 1", "p = 2", "p = 3"])
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylim(0, 118)
    ax.set_ylabel("shots that use exactly k kits (%)")
    ax.set_title("Share of valid shots, noise-free")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.84))
    return _save(fig, "fig05_valid_shots")


def fig_noise() -> Path:
    n = load("noise")
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    keys = (("valid_share", "shots with exactly k kits (%)", 100.0),
            ("quality", "quality of the valid shots", 1.0),
            ("p_opt", "chance one shot is the best plan (%)", 100.0))
    depths = sorted({r["p"] for r in n["summary"]})
    x = np.arange(len(n["levels"]))
    for ax, (key, label, scale) in zip(axes, keys):
        for m in ("constrained", "penalty"):
            for p in depths:
                rows = [r for r in n["summary"] if r["method"] == m and r["p"] == p]
                ax.plot(x, [scale * r[key]["mean"] for r in rows], color=COLORS[m], marker="o" if p == depths[0] else "s",
                        ls="-" if p == depths[0] else "--", label=f"{NAMES[m]}, p = {p}")
        if key != "valid_share":
            ref = "random_quality" if key == "quality" else "random_p_opt"
            ax.axhline(scale * n["summary"][0][ref]["mean"], color=MUTED, ls=":", lw=1.5, label=NAMES["random"])
        ax.set_xticks(x, ["0" if e == 0 else f"{100 * e:g}%" for e in n["levels"]])
        ax.set_xlabel("two-qubit gate error")
        ax.set_ylabel(label)
        ax.set_ylim(bottom=0)
    axes[0].set_title(f"Noise model on Aer, size S ({n['instances']} families, {n['shots']} shots)")
    axes[2].legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    return _save(fig, "fig06_noise")


def fig_tradeoff() -> Path:
    t = load("tradeoff")
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.scatter([c["carriers"] for c in t["cloud"]], [c["couples"] for c in t["cloud"]], s=6, color=GRID, zorder=1,
               label="Valid plans (sample)")
    front = sorted(t["front"], key=lambda c: c["carriers"])
    ax.plot([c["carriers"] for c in front], [c["couples"] for c in front], color=INK, lw=1.2, marker="o", ms=4, zorder=3,
            label=f"Exact trade-off front ({t['front_points']['exact']} plans)")
    ax.scatter([c["carriers"] for c in t["qaoa_front"]], [c["couples"] for c in t["qaoa_front"]], s=70, facecolors="none",
               edgecolors=BLUE, linewidths=2, zorder=4, label="Best plans among QAOA shots")
    same = (abs(t["field"]["carriers"] - t["relevance"]["carriers"]) < 1e-9
            and abs(t["field"]["couples"] - t["relevance"]["couples"]) < 1e-9)
    # When both rules land on the same point the field marker is drawn larger, so both stay visible.
    ax.scatter([t["field"]["carriers"]], [t["field"]["couples"]], s=150 if same else 60, marker="D", color=AQUA, zorder=5,
               edgecolors="white", label=NAMES["field"])
    ax.scatter([t["relevance"]["carriers"]], [t["relevance"]["couples"]], s=45 if same else 60, marker="D", color=YELLOW,
               zorder=6, edgecolors="white", label=NAMES["relevance"])
    ax.set_xlabel("relevance-weighted carriers found (expected)")
    ax.set_ylabel("at-risk couples found (expected)")
    ax.set_title(f"Couples against carriers, instance {t['instance']} ({t['n']} qubits, {t['k']} kits)")
    ax.legend(loc="lower left", fontsize=7.5)
    return _save(fig, "fig07_tradeoff")


def fig_circuits() -> Path:
    c = load("circuits")
    sizes = sorted({r["size"] for r in c["rows"]}, key=lambda s: "SML".index(s))
    fig, axes = plt.subplots(1, len(sizes), figsize=(4.8 * len(sizes), 3.4), squeeze=False)
    for ax, size in zip(axes[0], sizes):
        rows = [r for r in c["rows"] if r["size"] == size and r["topology"] == "all-to-all"]
        dicke = next(r for r in rows if r["method"] == "dicke_only")["two_qubit"]
        xs, width = np.arange(3), 0.36
        cons = [next(r for r in rows if r["method"] == "constrained" and r["p"] == p)["two_qubit"] for p in (1, 2, 3)]
        pen = [next(r for r in rows if r["method"] == "penalty" and r["p"] == p)["two_qubit"] for p in (1, 2, 3)]
        ax.bar(xs - width / 2, [dicke] * 3, width - 0.03, color="#86b6ef", label="Dicke start state", zorder=3)
        ax.bar(xs - width / 2, [v - dicke for v in cons], width - 0.03, bottom=[dicke + 0] * 3, color=BLUE,
               label="Constrained QAOA layers", zorder=3, edgecolor="white", linewidth=1.2)
        ax.bar(xs + width / 2, pen, width - 0.03, color=ORANGE, label="Penalty QAOA", zorder=3)
        for x, v in zip(xs - width / 2, cons):
            ax.text(x, v + max(cons) * 0.015, str(v), ha="center", fontsize=8, color=INK)
        for x, v in zip(xs + width / 2, pen):
            ax.text(x, v + max(cons) * 0.015, str(v), ha="center", fontsize=8, color=INK)
        ax.set_xticks(xs, ["p = 1", "p = 2", "p = 3"])
        ax.set_title(f"Size {size}: {rows[0]['n']} qubits")
        ax.grid(axis="x", visible=False)
    axes[0][0].set_ylabel("two-qubit CZ gates after transpilation")
    axes[0][0].legend(loc="upper left", fontsize=7.5)
    return _save(fig, "fig08_circuit_cost")


def fig_decomposition() -> Path:
    d = load("decomposition")
    names = ["field", "relevance", "greedy", "annealing", "decomposed_qaoa"]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    vals = [d["summary"][m]["mean"] for m in names]
    colors = [COLORS.get(m, BLUE) for m in names]
    bars = ax.barh([NAMES[m] for m in names], vals, color=colors, height=0.55, zorder=3)
    for rect, v in zip(bars, vals):
        ax.text(v + 0.012, rect.get_y() + rect.get_height() / 2, f"{100 * v:.0f}%", va="center", fontsize=8, color=INK)
    ax.axvline(1.0, color=INK, lw=1)
    ax.set_xlim(0, 1.12)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    r0 = d["rows"][0]
    ax.set_xlabel("value / proven optimum (integer programme)")
    ax.set_title(f"Linked families: {r0['n']} relatives, {r0['k']} kits, circuits of at most "
                 f"{max(r['max_qubits'] for r in d['rows'])} qubits")
    return _save(fig, "fig09_decomposition")


def fig_histogram() -> Path:
    demo = load("demo")
    h = demo["histogram"]
    edges = np.array(h["edges"])
    centers = (edges[:-1] + edges[1:]) / 2
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    width = 0.028
    series = [("random", MUTED, NAMES["random"]), ("constrained_p1", "#9ec5f4", "Constrained QAOA, p = 1"),
              ("constrained_p3", BLUE, "Constrained QAOA, p = 3")]
    for i, (key, color, label) in enumerate(series):
        if key in h:
            ax.bar(centers + (i - 1) * (width + 0.003), 100 * np.array(h[key]), width, color=color, label=label, zorder=3)
    ax.set_xlabel("quality of the measured plan (0 = worst valid plan, 1 = best)")
    ax.set_ylabel("share of shots (%)")
    ax.set_title(f"Where the shots land, instance {demo['name']}")
    ax.set_xticks(edges[::2])
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right")
    return _save(fig, "fig10_shot_distribution")


def fig_architecture(path: Path | None = None) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6.1))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    def box(x, y, w, h, title, lines, face, edge=AXIS, bold=INK, size=8.4):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", facecolor=face,
                                    edgecolor=edge, linewidth=1.1, zorder=2))
        ax.text(x + 1.3, y + h - 2.2, title, fontsize=size, fontweight="bold", color=bold, va="top", zorder=3)
        ax.text(x + 1.3, y + h - 5.4, lines, fontsize=6.9, color=INK2, va="top", zorder=3, linespacing=1.5)

    def arrow(a, b, color=INK2, rad=0.0, style="-|>"):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=11, lw=1.2, color=color,
                                     connectionstyle=f"arc3,rad={rad}", zorder=4))

    classical, quantum, out = "#f4f3ef", "#e6f0fc", "#e9f7f1"
    box(1, 41, 21.5, 15.5, "1  Family generator",
        "pedigree.py\nseeded synthetic families\ncousin, exchange marriages", classical)
    box(26.5, 41, 21.5, 15.5, "2  Genetics engine",
        "genetics.py\nMendel's rules, exact inference\ncarrier p, couple w", classical)
    box(52, 41, 21.5, 15.5, "3  Problem builder",
        "problem.py\nobjective, exactly-k rule\nQUBO and Ising form", classical)
    box(77.5, 41, 21.5, 15.5, "4  Classical references",
        "classical.py\nbrute force, integer programme,\nfield rule, greedy, annealing", classical)
    box(26.5, 11.5, 47, 24.5, "5  Quantum module in Qiskit", "", quantum, edge=BLUE, bold="#184f95")
    box(28.3, 17.5, 13.6, 12.5, "Circuit", "circuits.py\nDicke state\nRZZ cost, XY mixer", "white",
        edge="#9ec5f4", size=7.8)
    box(43.2, 17.5, 13.6, 12.5, "Estimator", "qaoa.py\nexpected value\nCOBYLA tunes angles", "white",
        edge="#9ec5f4", size=7.8)
    box(58.1, 17.5, 13.6, 12.5, "Sampler", "qaoa.py, noise.py\nmeasured plans\nnoise model", "white",
        edge="#9ec5f4", size=7.8)
    box(1, 11.5, 21.5, 24.5, "6  Decomposition",
        "decompose.py\nsplit along couple links\none circuit per component\ndynamic programme\nshares out the kits",
        classical)
    box(77.5, 11.5, 21.5, 24.5, "7  Evaluation",
        "evaluate.py, plots.py\nquality, chance of best plan\nvalid shots, noise sweep\ntrade-off curve\n"
        "fixed seeds, saved results", classical)
    box(26.5, 0.8, 47, 6.6, "8  Outputs", "", out, edge=AQUA)
    ax.text(40.5, 4.1, "screening plan  |  results and figures  |  report and website",
            fontsize=6.9, color=INK2, va="center", zorder=3)
    arrow((23.1, 48.7), (26.1, 48.7))
    arrow((48.6, 48.7), (51.6, 48.7))
    arrow((74.1, 48.7), (77.1, 48.7))
    arrow((62.7, 40.6), (62.7, 36.6), color=BLUE)
    arrow((42.2, 24.5), (42.9, 24.5), color=BLUE)
    arrow((57.1, 24.5), (57.8, 24.5), color=BLUE)
    arrow((50, 17.1), (35.1, 17.1), color=BLUE, rad=-0.32)
    ax.text(42.5, 12.7, "new angles", fontsize=6.4, color="#184f95", ha="center", zorder=5)
    arrow((23.1, 23.5), (26.1, 23.5), style="<|-|>")
    arrow((74.1, 23.5), (77.1, 23.5))
    arrow((88.2, 40.6), (88.2, 36.6))
    arrow((50, 11.1), (50, 8.0))
    arrow((88.2, 11.1), (74.1, 4.1), rad=-0.25)
    ax.text(1, 58.6, "Classical code prepares the weights, tunes the circuit and checks the answers. "
            "The quantum circuit is the step that proposes screening plans.", fontsize=7.6, color=INK2)
    path = path or (ROOT / "report" / "architecture.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


ALL = [fig_pedigree, fig_gate1, fig_quality, fig_popt, fig_valid, fig_noise, fig_tradeoff, fig_circuits,
       fig_decomposition, fig_histogram, fig_architecture]


def main() -> int:
    for fn in ALL:
        try:
            print("wrote", fn().relative_to(ROOT))
        except FileNotFoundError as exc:
            print("skipped", fn.__name__, "-", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
