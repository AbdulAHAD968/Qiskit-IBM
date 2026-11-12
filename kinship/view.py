"""A drawable, JSON-friendly view of a family: people with coordinates, couples with weights."""
from __future__ import annotations

from . import CARRIER_RATE
from .genetics import PedigreeModel
from .pedigree import layout
from .problem import ScreeningProblem


def family_view(problem: ScreeningProblem) -> dict:
    fam = problem.family
    pos = layout(fam)
    model = PedigreeModel(fam, problem.meta.get("carrier_rate", CARRIER_RATE))
    qubit = {pid: t for t, pid in enumerate(problem.person_ids)}
    people = []
    for p in fam.people:
        if p.affected:
            status = "affected"
        elif p.role in ("father", "mother"):
            status = "obligate"
        elif not p.alive:
            status = "deceased"
        elif not p.available:
            status = "unavailable"
        else:
            status = "candidate"
        people.append({
            "id": p.id, "label": p.label, "role": p.role, "sex": p.sex, "gen": p.gen,
            "father": p.father, "mother": p.mother, "status": status, "stage": p.stage,
            "p": model.carrier_prob(p.id), "r": fam.relevance(p.id),
            "qubit": qubit.get(p.id), "x": pos[p.id][0], "y": pos[p.id][1],
        })
    couples = []
    for c in fam.couples:
        w = model.both_carriers(c.a, c.b)
        couples.append({
            "a": c.a, "b": c.b, "kind": c.kind, "strength": c.strength, "w": w,
            "weight": w * c.strength, "in_problem": c.a in qubit and c.b in qubit,
        })
    return {"people": people, "couples": couples}
