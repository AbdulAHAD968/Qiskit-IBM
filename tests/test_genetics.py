"""The pedigree engine is checked against textbook values before any optimisation runs."""
import numpy as np
import pytest

from kinship.genetics import CARRIER, PedigreeModel, allele_frequency, transmission_table
from kinship.pedigree import Family, Person, generate_family

RATE = 0.05
Q = allele_frequency(RATE)


def family(rows, probands):
    """rows: (label, father, mother, affected)."""
    people = [
        Person(i, label, "x", "M", 0, father, mother, affected=affected)
        for i, (label, father, mother, affected) in enumerate(rows)
    ]
    return Family(people, [], probands, seed=0)


def nuclear():
    return family(
        [("father", None, None, False), ("mother", None, None, False),
         ("index", 0, 1, True), ("sibling", 0, 1, False)],
        [2],
    )


def three_generations():
    #  0 gf, 1 gm, 2 father, 3 uncle, 4 mother, 5 index, 6 uncle's wife, 7 cousin
    return family(
        [("gf", None, None, False), ("gm", None, None, False),
         ("father", 0, 1, False), ("uncle", 0, 1, False), ("mother", None, None, False),
         ("index", 2, 4, True), ("wife", None, None, False), ("cousin", 3, 6, False)],
        [5],
    )


def test_allele_frequency_reproduces_carrier_rate():
    assert 2 * Q * (1 - Q) == pytest.approx(RATE)


def test_transmission_rows_sum_to_one():
    assert np.allclose(transmission_table().sum(axis=2), 1.0)


def test_parents_of_affected_child_are_obligate_carriers():
    m = PedigreeModel(nuclear(), RATE)
    assert m.carrier_prob(0) == pytest.approx(1.0)
    assert m.carrier_prob(1) == pytest.approx(1.0)


def test_unaffected_sibling_is_carrier_with_probability_two_thirds():
    assert PedigreeModel(nuclear(), RATE).carrier_prob(3) == pytest.approx(2 / 3)


def test_grandparent_matches_closed_form():
    # Without an uncle the closed form is (1 + q) / 2, slightly above one half.
    fam = family(
        [("gf", None, None, False), ("gm", None, None, False), ("father", 0, 1, False),
         ("mother", None, None, False), ("index", 2, 3, True)],
        [4],
    )
    m = PedigreeModel(fam, RATE)
    assert m.carrier_prob(0) == pytest.approx((1 + Q) / 2)
    assert m.carrier_prob(1) == pytest.approx((1 + Q) / 2)


def test_uncle_matches_closed_form():
    fam = family(
        [("gf", None, None, False), ("gm", None, None, False), ("father", 0, 1, False),
         ("uncle", 0, 1, False), ("mother", None, None, False), ("index", 2, 4, True)],
        [5],
    )
    assert PedigreeModel(fam, RATE).carrier_prob(3) == pytest.approx(2 / (4 - Q))


def test_first_cousin_is_about_one_quarter():
    p = PedigreeModel(three_generations(), RATE).carrier_prob(7)
    assert 0.25 < p < 0.30          # 1/4 from the family line plus the married-in parent


def test_married_in_spouse_stays_near_population_rate():
    p = PedigreeModel(three_generations(), RATE).carrier_prob(6)
    assert p == pytest.approx(RATE, abs=0.01)


def test_control_family_stays_at_population_rate():
    fam = family([("a", None, None, False), ("b", None, None, False), ("c", 0, 1, False)], [])
    p = PedigreeModel(fam, RATE).carrier_prob(2)
    assert p == pytest.approx(RATE, abs=0.005)


def cousin_marriage():
    """Index parents are first cousins, so the pedigree contains a loop."""
    #  0 ggf, 1 ggm, 2 brother A, 3 brother B, 4 wife of A, 5 wife of B,
    #  6 father (child of A), 7 mother (child of B), 8 index child, 9 sibling
    return family(
        [("ggf", None, None, False), ("ggm", None, None, False),
         ("brother a", 0, 1, False), ("brother b", 0, 1, False),
         ("wife a", None, None, False), ("wife b", None, None, False),
         ("father", 2, 4, False), ("mother", 3, 5, False),
         ("index", 6, 7, True), ("sibling", 6, 7, False)],
        [8],
    )


def test_variable_elimination_matches_full_enumeration_with_a_loop():
    fam = cousin_marriage()
    m = PedigreeModel(fam, RATE)
    joint = m.joint_bruteforce()                 # all 3^10 genotype assignments
    n = len(fam.people)
    for i in range(n):
        axes = tuple(a for a in range(n) if a != i)
        assert m.marginal((i,)) == pytest.approx(joint.sum(axis=axes), abs=1e-12)
    for i in range(n):
        for j in range(i + 1, n):
            axes = tuple(a for a in range(n) if a not in (i, j))
            assert m.marginal((i, j)) == pytest.approx(joint.sum(axis=axes), abs=1e-12)
    assert m.carrier_prob(9) == pytest.approx(2 / 3)


def test_cousin_marriage_raises_the_shared_ancestor_risk():
    # With cousin parents, both lines lead back to the same great-grandparents.
    m = PedigreeModel(cousin_marriage(), RATE)
    assert m.carrier_prob(2) > 0.85 and m.carrier_prob(3) > 0.85
    assert m.carrier_prob(4) < 0.2 and m.carrier_prob(5) < 0.2


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_variable_elimination_matches_reference_contraction(seed):
    fam = generate_family(seed, n_candidates=10)
    m = PedigreeModel(fam, RATE)
    for p in fam.people:
        assert m.marginal((p.id,)) == pytest.approx(m.marginal_reference((p.id,)), abs=1e-10)
    for c in fam.couples:
        assert m.marginal((c.a, c.b)) == pytest.approx(m.marginal_reference((c.a, c.b)), abs=1e-10)


def test_relatives_are_correlated_not_independent():
    # The father is a carrier, so almost surely exactly one of his parents is.
    # "Both grandparents are carriers" is therefore rare, although each one
    # alone has probability about one half. Pair values cannot be built from
    # single-person probabilities, which is why the objective is quadratic.
    fam = family(
        [("gf", None, None, False), ("gm", None, None, False), ("father", 0, 1, False),
         ("mother", None, None, False), ("index", 2, 3, True)],
        [4],
    )
    m = PedigreeModel(fam, RATE)
    joint = m.both_carriers(0, 1)
    assert joint == pytest.approx(Q)             # closed form: b / (2a + b) = q
    assert joint < 0.2 * m.carrier_prob(0) * m.carrier_prob(1)
    assert m.marginal((0, 1))[CARRIER, CARRIER] == pytest.approx(joint)
