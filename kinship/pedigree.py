"""Synthetic extended-family generator.

The generator builds three- or four-generation families of the kind met in
cascade screening: one affected index child, obligate-carrier parents,
grandparents, aunts and uncles with their spouses, and a generation of siblings
and cousins. Consanguinity is built in on purpose, because it is what makes
couples inside one family correlated:

* with probability ``consanguinity`` the index parents are first cousins;
* with probability ``exchange`` one paternal and one maternal sibling are
  married to each other (an exchange marriage between the two sides);
* unmarried cousins of opposite sex are linked as engaged or as possible
  future matches.

Everything is seeded. No patient data is used anywhere in this project.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field

import numpy as np

# How much it matters to learn that a person is a carrier, by life stage.
RELEVANCE = {"unmarried": 1.0, "engaged": 1.0, "married": 0.7, "child": 0.5, "elder": 0.1}

NON_CANDIDATE_ROLES = ("father", "mother")


@dataclass
class Person:
    id: int
    label: str
    role: str                 # proband, father, mother, sibling, cousin, spouse, ...
    sex: str                  # "M" or "F"
    gen: int                  # 0 great-grandparents ... 3 index generation
    father: int | None = None
    mother: int | None = None
    affected: bool = False
    alive: bool = True
    available: bool = True    # present and consenting at this visit
    stage: str = "married"    # key of RELEVANCE
    family: int = 0


@dataclass
class Couple:
    a: int
    b: int
    kind: str                 # married | engaged | potential
    strength: float           # probability that the couple link is real


@dataclass
class Family:
    people: list[Person]
    couples: list[Couple]
    probands: list[int]
    seed: int
    params: dict = field(default_factory=dict)

    def candidates(self) -> list[int]:
        """People who can be tested in this visit.

        The affected child is already diagnosed and the parents are obligate
        carriers, so none of the three carries any information for a test kit.
        """
        return [
            p.id
            for p in self.people
            if p.alive and p.available and not p.affected and p.role not in NON_CANDIDATE_ROLES
        ]

    def relevance(self, pid: int) -> float:
        return RELEVANCE[self.people[pid].stage]

    def to_dict(self) -> dict:
        return {
            "people": [asdict(p) for p in self.people],
            "couples": [asdict(c) for c in self.couples],
            "probands": list(self.probands),
            "seed": self.seed,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Family":
        return cls(
            people=[Person(**p) for p in d["people"]],
            couples=[Couple(**c) for c in d["couples"]],
            probands=list(d["probands"]),
            seed=d["seed"],
            params=d.get("params", {}),
        )


def generate_family(
    seed: int,
    n_candidates: int = 10,
    *,
    consanguinity: float = 0.6,
    exchange: float = 0.4,
    cousin_marriage_rate: float = 0.5,
    engaged_rate: float = 0.15,
    family_index: int = 0,
) -> Family:
    """Generate one seeded family with exactly ``n_candidates`` testable relatives."""
    rng = np.random.default_rng(seed)
    P: list[Person] = []
    C: list[Couple] = []

    def add(label, role, sex, gen, father=None, mother=None, **kw) -> int:
        P.append(Person(len(P), label, role, sex, gen, father, mother, family=family_index, **kw))
        return P[-1].id

    def coin(prob: float) -> bool:
        return bool(rng.random() < prob)

    large = n_candidates >= 14
    sib_range = (1, 4)                           # siblings of the index child, [lo, hi)
    par_range = (2, 4) if large else (1, 3)      # siblings of each parent
    kid_range = (2, 5)                           # children of each aunt or uncle

    related = coin(consanguinity)
    ggf = ggm = None
    if related:
        ggf = add("Great-grandfather", "ancestor", "M", 0, alive=False, stage="elder")
        ggm = add("Great-grandmother", "ancestor", "F", 0, alive=False, stage="elder")
    link_p = "pgf" if coin(0.7) else "pgm"
    link_m = "mgf" if coin(0.7) else "mgm"

    def grandparent(role: str, label: str, sex: str) -> int:
        linked = related and role in (link_p, link_m)
        return add(
            label, role, sex, 1,
            ggf if linked else None, ggm if linked else None,
            alive=coin(0.45), stage="elder",
        )

    pgf = grandparent("pgf", "Paternal grandfather", "M")
    pgm = grandparent("pgm", "Paternal grandmother", "F")
    mgf = grandparent("mgf", "Maternal grandfather", "M")
    mgm = grandparent("mgm", "Maternal grandmother", "F")

    father = add("Father", "father", "M", 2, pgf, pgm)
    mother = add("Mother", "mother", "F", 2, mgf, mgm)
    C.append(Couple(father, mother, "married", 1.0))

    def parent_siblings(side: str, fa: int, mo: int) -> list[int]:
        out, counts = [], {"M": 0, "F": 0}
        for _ in range(int(rng.integers(*par_range))):
            sex = "M" if coin(0.5) else "F"
            counts[sex] += 1
            word = "uncle" if sex == "M" else "aunt"
            out.append(add(f"{side.capitalize()} {word} {counts[sex]}", f"{side}_sib", sex, 2, fa, mo))
        return out

    pat = parent_siblings("paternal", pgf, pgm)
    mat = parent_siblings("maternal", mgf, mgm)

    married: list[tuple[int, int]] = []          # (husband, wife), excluding the index parents
    taken: set[int] = set()
    if coin(exchange):
        pairs = [(a, b) for a in pat for b in mat if P[a].sex != P[b].sex]
        if pairs:
            a, b = pairs[int(rng.integers(len(pairs)))]
            h, w = (a, b) if P[a].sex == "M" else (b, a)
            married.append((h, w))
            taken.update((a, b))
            C.append(Couple(h, w, "married", 1.0))
    for s in pat + mat:
        if s in taken:
            continue
        if coin(0.85):
            if P[s].sex == "M":
                sp = add(f"Wife of {P[s].label.lower()}", "spouse", "F", 2)
                married.append((s, sp))
            else:
                sp = add(f"Husband of {P[s].label.lower()}", "spouse", "M", 2)
                married.append((sp, s))
            C.append(Couple(married[-1][0], married[-1][1], "married", 1.0))
        else:
            P[s].stage = "unmarried"

    counters = {"cousin": 0, "sibling": 0}

    def add_cousin(h: int, w: int) -> int:
        counters["cousin"] += 1
        return add(
            f"Cousin {counters['cousin']}", "cousin", "M" if coin(0.5) else "F", 3, h, w,
            stage="child" if coin(0.15) else "unmarried",
        )

    def add_sibling() -> int:
        counters["sibling"] += 1
        return add(
            f"Sibling {counters['sibling']}", "sibling", "M" if coin(0.5) else "F", 3, father, mother,
            stage="child" if coin(0.15) else "unmarried",
        )

    for h, w in married:
        for _ in range(int(rng.integers(*kid_range))):
            add_cousin(h, w)
    proband = add(
        "Index child", "proband", "M" if coin(0.5) else "F", 3, father, mother,
        affected=True, stage="child",
    )
    for _ in range(int(rng.integers(*sib_range))):
        add_sibling()

    fam = Family(P, C, [proband], seed)

    # Grow or trim so that exactly n_candidates relatives can be tested.
    while len(fam.candidates()) < n_candidates:
        if married and coin(0.75):
            h, w = married[int(rng.integers(len(married)))]
            add_cousin(h, w)
        else:
            add_sibling()
    surplus = len(fam.candidates()) - n_candidates
    if surplus > 0:
        # Elders and small children are the most likely to be missing from a visit.
        pool = fam.candidates()
        absent = np.array([
            {"elder": 4.0, "child": 2.0}.get(P[i].stage, 1.5 if P[i].gen == 2 else 0.5) for i in pool
        ])
        for pid in rng.choice(pool, size=surplus, replace=False, p=absent / absent.sum()):
            P[int(pid)].available = False       # absent or declined: fixed to "not tested"

    # Engagements and possible future matches among unmarried cousins.
    young = [
        p.id for p in P
        if p.gen == 3 and p.stage == "unmarried" and p.alive and p.available and not p.affected
    ]

    def same_sibship(a: int, b: int) -> bool:
        return P[a].father == P[b].father and P[a].mother == P[b].mother

    eligible = [
        (a, b)
        for ia, a in enumerate(young)
        for b in young[ia + 1:]
        if P[a].sex != P[b].sex and not same_sibship(a, b)
    ]
    engaged: set[int] = set()
    for t in rng.permutation(len(eligible)):
        a, b = eligible[int(t)]
        if a in engaged or b in engaged:
            continue
        if coin(engaged_rate):
            engaged.update((a, b))
            P[a].stage = P[b].stage = "engaged"
            C.append(Couple(a, b, "engaged", 1.0))
    free = [(a, b) for a, b in eligible if a not in engaged and b not in engaged]
    degree: dict[int, int] = defaultdict(int)
    for a, b in free:
        degree[a] += 1
        degree[b] += 1
    for a, b in free:
        # Each person marries at most one cousin, so the match probabilities of
        # one person sum to at most the first-cousin marriage rate.
        C.append(Couple(a, b, "potential", round(cousin_marriage_rate / max(degree[a], degree[b]), 4)))

    fam.params = {
        "n_candidates": n_candidates,
        "consanguinity": consanguinity,
        "exchange": exchange,
        "cousin_marriage_rate": cousin_marriage_rate,
        "engaged_rate": engaged_rate,
        "parents_are_cousins": related,
    }
    return fam


def generate_linked_families(
    seed: int, n_families: int = 4, n_each: int = 12, cross_links: int = 2
) -> Family:
    """Several index families joined by a few couples that marry across families.

    The families do not share ancestors, so the pedigree is a forest and the
    carrier states of people in different families are independent.
    """
    rng = np.random.default_rng(seed)
    people: list[Person] = []
    couples: list[Couple] = []
    probands: list[int] = []
    blocks: list[list[int]] = []
    for f in range(n_families):
        fam = generate_family(seed * 100 + f, n_each, family_index=f)
        off = len(people)
        block = [q + off for q in fam.candidates()]
        for p in fam.people:
            p.id += off
            p.father = None if p.father is None else p.father + off
            p.mother = None if p.mother is None else p.mother + off
            p.label = f"F{f + 1} {p.label}"
            people.append(p)
        for c in fam.couples:
            couples.append(Couple(c.a + off, c.b + off, c.kind, c.strength))
        probands += [q + off for q in fam.probands]
        blocks.append(block)

    def young(block: list[int], sex: str) -> list[int]:
        return [i for i in block if people[i].gen == 3 and people[i].sex == sex and people[i].stage == "unmarried"]

    for f in range(n_families):
        g = (f + 1) % n_families
        if g == f:
            continue
        made = 0
        for sex_a, sex_b in (("M", "F"), ("F", "M")):
            if made >= cross_links:
                break
            pool_a, pool_b = young(blocks[f], sex_a), young(blocks[g], sex_b)
            if not (pool_a and pool_b):
                continue
            a, b = int(rng.choice(pool_a)), int(rng.choice(pool_b))
            if made == 0:
                # An engagement across two index families replaces any looser matches.
                couples = [
                    c for c in couples
                    if not (c.kind == "potential" and (c.a in (a, b) or c.b in (a, b)))
                ]
                people[a].stage = people[b].stage = "engaged"
                couples.append(Couple(a, b, "engaged", 1.0))
            else:
                couples.append(Couple(a, b, "potential", 0.3))
            made += 1
    return Family(people, couples, probands, seed, {"n_families": n_families, "n_each": n_each})


def layout(family: Family) -> dict[int, tuple[float, float]]:
    """Coordinates for drawing: x in [0, 1], y equal to the generation index."""
    P = family.people
    spouse: dict[int, int] = {}
    for c in family.couples:
        if c.kind == "married":
            spouse[c.a] = c.b
            spouse[c.b] = c.a
    kids: dict[tuple[int, int], list[int]] = defaultdict(list)
    for p in P:
        if p.father is not None and p.mother is not None:
            kids[(p.father, p.mother)].append(p.id)

    pos: dict[int, tuple[float, float]] = {}
    offset = 0.0
    for f in sorted({p.family for p in P}):
        members = [p for p in P if p.family == f]
        role = defaultdict(list)
        for p in members:
            role[p.role].append(p)
        father, mother = role["father"][0], role["mother"][0]

        def unit(person: Person):
            sp = spouse.get(person.id)
            if sp is None:
                return [person.id], []
            h, w = (person.id, sp) if person.sex == "M" else (sp, person.id)
            return [h, w], kids.get((h, w), [])

        exchange_unit = None
        left, right = [], []
        for s in role["paternal_sib"]:
            sp = spouse.get(s.id)
            if sp is not None and P[sp].role == "maternal_sib":
                exchange_unit = ([s.id, sp], kids.get(tuple(sorted((s.id, sp), key=lambda i: P[i].sex == "F")), []))
            else:
                left.append(unit(s))
        for s in role["maternal_sib"]:
            sp = spouse.get(s.id)
            if sp is not None and P[sp].role == "paternal_sib":
                continue
            right.append(unit(s))
        core = ([father.id, mother.id], kids.get((father.id, mother.id), []))
        units = left + [core] + ([exchange_unit] if exchange_unit else []) + right

        x = offset
        for mem, ch in units:
            width = max(len(mem), len(ch), 1)
            m0 = x + (width - len(mem)) / 2
            for t, pid in enumerate(mem):
                pos[pid] = (m0 + t, 2.0)
            c0 = x + (width - len(ch)) / 2
            for t, pid in enumerate(ch):
                pos[pid] = (c0 + t, 3.0)
            x += width + 0.7

        def centre(ids):
            return float(np.mean([pos[i][0] for i in ids]))

        cp = centre([father.id] + [s.id for s in role["paternal_sib"]])
        cm = centre([mother.id] + [s.id for s in role["maternal_sib"]])
        if cm - cp < 2.6:
            mid = (cp + cm) / 2
            cp, cm = mid - 1.3, mid + 1.3
        for key, cx, dx in (("pgf", cp, -0.5), ("pgm", cp, 0.5), ("mgf", cm, -0.5), ("mgm", cm, 0.5)):
            pos[role[key][0].id] = (cx + dx, 1.0)
        if role["ancestor"]:
            linked = [p.id for k in ("pgf", "pgm", "mgf", "mgm") for p in role[k] if p.father is not None]
            ca = centre(linked) if linked else (cp + cm) / 2
            for t, p in enumerate(role["ancestor"]):
                pos[p.id] = (ca - 0.5 + t, 0.0)
        for p in members:                       # anything not placed yet (defensive)
            pos.setdefault(p.id, (x, float(p.gen)))
        offset = max(v[0] for k, v in pos.items() if P[k].family == f) + 2.0

    xs = [v[0] for v in pos.values()]
    lo, span = min(xs), max(max(xs) - min(xs), 1e-9)
    return {pid: ((vx - lo) / span, vy) for pid, (vx, vy) in pos.items()}
