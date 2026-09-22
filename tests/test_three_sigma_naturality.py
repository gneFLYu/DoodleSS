"""Conditional cross-grading audit with the independent Tate cycle retained.

Put A=xh1^2 D^4 u_2sigma=h2^3 D^3 u_2sigma and
z=2 v1^2 k D^4 u_3sigma. Formal notes 515 and 770--774 assert a_sigma*A=z.
The product uses the actual group-cohomology hidden h1 extension proved in
DKLLW main.tex:1094--1111, not just its 2-BSS associated graded.

These tests expose incompatible *conditional* page states. They do not claim
that the separate-workspace quotient engine checks cross-grading naturality,
choose a replacement differential, or use FN010 to justify any coefficient.
The common nonzero F4 coefficient 1 is fixed by the user's Galois-fixed basis,
not a test-only scalar choice. All differential admissions remain in copies.
The independent verified Tate cycle for w=2UDu, hence its forward g image z,
blocks the disputed d23 even in the counterfactual admitted-Jan29 fixture.

The incoming-source audit is also conditional on the separate Ck permanent
cycle assertion FN-3I-010-pc. Its printed restriction proof uses the kernel
subgroup and currently carries its own source blocker. We do not repair that
proof by accepting the disputed d23 or by assuming homotopy exactness on E_r.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "tests")]
from domain.fate import is_accepted
from domain.migrations import migrate_project
from domain.seed import demo_project
from test_three_sigma_convergence import TATE_CYCLE_ID, assert_tate_cycle_conflict, hypothesis


FINAL_ROWS = {"formal_diff_fn-3i-010_1", "formal_diff_fn-3i-010_2"}
BASE_PROBES = (("I13", 33, 3), ("I13X", 33, 3), ("I02", 32, 26),
               ("S40", 12, 0), ("S40", 32, 4), ("S73", 31, 27))
SIGMA_PATTERNS = ("S00", "S40", "S11", "S51", "S71", "S02", "S22Y",
                  "S22H", "S62", "S62V", "S13", "S33", "S53", "S73", "S73V")
INCOMING_PAGES = (3, 5, 7, 9, 11, 13)


def _workspace(project, ident):
    return next(w for w in project.workspaces if w.id == ident)


def _candidate(original, *, admit_final=False):
    candidate = hypothesis(original, common=1)
    two = _workspace(candidate, "ws_2sigma_i")
    for arrow in two.differentials:
        if arrow.label.startswith("FN-") and arrow.label != "FN-2I-002":
            arrow.status = "admitted"
    for claim in two.propositions:
        fact = claim.conclusion.get("fact_id", "")
        if fact.startswith("FN-") and fact != "FN-2I-002":
            claim.status = "admitted"
    if not admit_final:
        three = _workspace(candidate, "ws_3sigma_i")
        claims = {claim.id: claim for claim in three.propositions}
        for arrow in three.differentials:
            if arrow.id in FINAL_ROWS:
                arrow.status = claims[arrow.proposition_id].status = "review"
    return candidate


def _runtime(candidate, pages):
    probes = {(p, s + 20 * n, f + 4 * n)
              for p, s, f in BASE_PROBES for n in range(4)}
    # Z=2Uk^4D^5=(28,16) is the D^-8 translate of g^3 z.
    # Enumerate its incoming source grades, not merely a preferred source.
    probes.update((p, 29, 16 - r) for p in SIGMA_PATTERNS for r in INCOMING_PAGES)
    probes.add(("S40", 28, 16))
    payload = {
        "project": asdict(candidate), "workspaces": ["ws_2sigma_i", "ws_3sigma_i"],
        "pages": pages, "vectorAudit": True,
        "bounds": {"stemMin": 27, "stemMax": 94, "filtrationMin": 0, "filtrationMax": 42},
        "probes": [{"pattern": p, "stem": s, "filtration": f}
                   for p, s, f in sorted(probes)],
        "vectorProbes": [
            {"components": components, "stem": 33 + 20 * n, "filtration": 3 + 4 * n}
            for components in ({"I13": 1}, {"I13X": 1}, {"I13": 1, "I13X": 1})
            for n in range(4)
        ],
    }
    result = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT,
                            input=json.dumps(payload), capture_output=True, text=True,
                            encoding="utf-8", check=True, timeout=90)
    return {ws["id"]: {row["page"]: row for row in ws["pages"]}
            for ws in json.loads(result.stdout)}


def _ports(row, pattern, stem, filtration, g_power=0):
    return set(next(probe["ports"] for probe in row["probes"] if
                    (probe["pattern"], probe["stem"], probe["filtration"]) ==
                    (pattern, stem + 20 * g_power, filtration + 4 * g_power)))


def _vector_live(row, components, g_power=0):
    return next(probe["live"] for probe in row["vectorProbes"]
                if probe["components"] == components
                and (probe["stem"], probe["filtration"]) == (33 + 20 * g_power, 3 + 4 * g_power))


@pytest.fixture(scope="module")
def audit():
    original = migrate_project(demo_project())
    before = deepcopy(asdict(original))
    early = _runtime(_candidate(original), [3, 5, 6, 7, 9, 11, 13, 14, 23, 24])
    final = _runtime(_candidate(original, admit_final=True), [23, 24])
    assert asdict(original) == before
    return original, early, final


def test_e23_euler_preimage_survives_but_its_possible_d23_target_is_empty(audit):
    _, early, _ = audit
    two, three = early["ws_2sigma_i"], early["ws_3sigma_i"]
    for rows in early.values():
        assert not [conflict for row in rows.values() for conflict in row["conflicts"]]
    for n in range(3):
        for page in (3, 5, 6, 9, 13, 14, 23, 24):
                assert _ports(two[page], "I13", 33, 3, n) == {"0:0"}
                # The source proof's second candidate x^2*h2*D^4 also maps
                # to z by the hidden h2 extension, not to zero on E2.
                # Its g translates become equal to A modulo a d5 boundary.
                # An absent *canonical column* is not a zero quotient class!
                assert _vector_live(two[page], {"I13X": 1}, n)
        # xh1*k^6 D^7 u_2sigma at (32,26) is the only E2 column in
        # A's d23 target grade. FN-2I-006 kills this *source* on d5;
        # it is not an incoming d5 boundary and cannot receive d23 later.
        assert _ports(two[5], "I02", 32, 26, n) == {"0:0"}
        assert _ports(two[6], "I02", 32, 26, n) == set()
        assert _ports(two[23], "I02", 32, 26, n) == set()
        # g^2 z=(72,12) is D8 times the new CD1 d11 target. Only the
        # first two lower-filtration Euler images remain at this late page.
        assert _ports(three[11], "S40", 32, 4, n) == {"1:0"}
        assert _ports(three[23], "S40", 32, 4, n) == ({"1:0"} if n < 2 else set())
        assert _ports(three[23], "S73", 31, 27, n) == {"0:0"}


def test_admitting_final_formula_blocks_e23_instead_of_deleting_the_euler_image(audit):
    _, early, final = audit
    for n in range(3):
        assert _ports(final["ws_2sigma_i"][24], "I13", 33, 3, n) == {"0:0"}
        assert _ports(final["ws_2sigma_i"][23], "I02", 32, 26, n) == set()
        expected = {"1:0"} if n < 2 else set()
        assert _ports(early["ws_3sigma_i"][24], "S40", 32, 4, n) == expected
        assert _ports(final["ws_3sigma_i"][23], "S40", 32, 4, n) == expected
        assert _ports(final["ws_3sigma_i"][24], "S40", 32, 4, n) == expected
        assert _ports(final["ws_3sigma_i"][24], "S73", 31, 27, n) == {"0:0"}
    # The new independent certificate detects this obstruction without
    # pretending that the runtime has proved the cross-workspace product.
    for page in (23, 24):
        assert_tate_cycle_conflict(final["ws_3sigma_i"][page])
        assert {"1:0", "2:0", "3:0"} <= _ports(final["ws_3sigma_i"][page], "S40", 12, 0)


def test_independent_d11_resolves_the_third_forward_g_d13_euler_image_gap(audit):
    _, early, _ = audit
    two, three = early["ws_2sigma_i"], early["ws_3sigma_i"]
    # g^3 A = D^8*h2^3*k^3*D^4*u_2sigma, exactly a D^8 translate
    # of the FN-2I-018 d13 target. Its asserted Euler image g^3 z
    # must therefore also be zero by E14. The independent Euler13-derived
    # CD1 d11 now supplies that earlier boundary, without admitting Jan29.
    assert _ports(two[13], "I13", 33, 3, 3) == {"0:0"}
    assert _ports(two[14], "I13", 33, 3, 3) == set()
    assert _vector_live(two[13], {"I13": 1}, 3)
    assert not _vector_live(two[14], {"I13": 1}, 3)
    assert _ports(three[11], "S40", 32, 4, 3) == {"1:0"}
    assert _ports(three[13], "S40", 32, 4, 3) == set()
    assert _ports(three[14], "S40", 32, 4, 3) == set()


def test_incoming_grades_and_independent_d11_match_the_euler_deadline(audit):
    original, early, _ = audit
    three = early["ws_3sigma_i"]
    expected = {
        3: {"S11": {"0:0", "0:1"}},  # C*k^3*D^5 (and positive j).
        5: {"S53": {"0:0"}},           # x^3*k^2*D^5.
        7: {},
        9: {"S13": {"0:0"}},           # T*k*D^4.
        11: {"S11": {"0:0"}},          # C*k*D^4.
        13: {},                         # x^3*D^4 has already died on d5.
    }
    for page, source in expected.items():
        actual = {pattern: ports for pattern in SIGMA_PATTERNS
                  if (ports := _ports(three[page], pattern, 29, 16 - page))}
        assert actual == source
        expected_ports = {"0:0", "0:1", "1:0"} if page == 3 else {"1:0"} if page <= 11 else set()
        assert _ports(three[page], "S40", 28, 16) == expected_ports

    # Source-based eliminations, not extra maps silently installed here:
    # d3(C)=0 (formal 681), and D,k are 3-cycles.
    # The d5 candidate is g^2*(B D^-2)*h2^2; FN-3I-005 and C*h2=0
    # force its differential to vanish. C*h2 lies in an empty E2 cell,
    # so this does not misuse a 2-BSS associated-graded zero relation.
    # The d9 candidate is gTD1, whose two Leibniz terms cancel independently
    # of Ck or Jan29. The Euler13 product deadline, together with this complete
    # inventory, now forces the (29,5)->(28,16) forward-g image of CD1 d11.
    # The historical Option 2 table alone still would not prove that theorem.
    ws = _workspace(original, "ws_3sigma_i")
    classes = {item.id: item for item in ws.classes}
    arrow = next(d for d in ws.differentials if d.label == "DER-3I-EULER-CD1-D11")
    assert arrow.status == "verified" and arrow.page == 11 and arrow.period_stem == 64
    assert (classes[arrow.source_id].grade.stem, classes[arrow.source_id].grade.filtration) == (9, 1)
    assert (classes[arrow.target_id].grade.stem, classes[arrow.target_id].grade.filtration) == (8, 12)
    assert _ports(three[14], "S40", 28, 16) == set()


def test_euler_preimages_are_quotient_vectors_not_independent_deleted_columns(audit):
    _, early, _ = audit
    two = early["ws_2sigma_i"]
    for n in (1, 2):
        assert _vector_live(two[5], {"I13": 1, "I13X": 1}, n)
        assert not _vector_live(two[6], {"I13": 1, "I13X": 1}, n)
        assert _vector_live(two[23], {"I13": 1}, n)
        assert _vector_live(two[23], {"I13X": 1}, n)
        assert _ports(two[23], "I13X", 33, 3, n) == set()


def test_independent_euler_permanence_remains_an_explicit_blocked_premise(audit):
    original, _, _ = audit
    ws = _workspace(original, "ws_3sigma_i")
    claim = next(item for item in ws.propositions
                 if item.conclusion.get("fact_id") == "FN-3I-010-pc")
    assert claim.kind == "permanent-cycle"
    assert claim.status == "review" and not is_accepted(claim.status)
    assert claim.conclusion["source_status"] == "withdrawn-proof"
    assert claim.conclusion["printed_source_status"] == "source-proved"
    conflict = next(item for item in claim.conclusion["source_conflicts"]
                    if item["kind"] == "euler-restriction-uses-kernel-subgroup")
    assert "Res_C4<i>(3sigma_i)=3" in conflict["checked_identity"]
    assert "a_3=0" in conflict["checked_identity"]
    assert claim.conclusion["source_blockers"]

    # The runtime audit does assume this premise, but carries its proof
    # blocker unchanged. This explicit test-only acceptance is neither a
    # mathematical repair nor a side effect of accepting the final d23.
    conditional = _workspace(_candidate(original), "ws_3sigma_i")
    copied = next(item for item in conditional.propositions if item.id == claim.id)
    assert copied.status == "admitted"
    assert copied.conclusion["source_conflicts"] == claim.conclusion["source_conflicts"]
    assert all(arrow.status == "review" for arrow in conditional.differentials
               if arrow.id in FINAL_ROWS)
    independent = next(item for item in conditional.propositions if item.id == TATE_CYCLE_ID)
    assert independent.status == "verified"
    assert independent.conclusion["cycle_constraint"] == "outgoing-only"


def test_source_formulas_remain_under_review_with_independent_fixed_units(audit):
    original, _, _ = audit
    three = _workspace(original, "ws_3sigma_i")
    claims = {claim.id: claim for claim in three.propositions}
    assert not three.settings.get("coefficient_assignments")
    for arrow in three.differentials:
        if arrow.id in FINAL_ROWS:
            assert arrow.status == claims[arrow.proposition_id].status == "review"
            assert not is_accepted(arrow.status)
            assert claims[arrow.proposition_id].conclusion["source_conflicts"]
            assert claims[arrow.proposition_id].conclusion["source_status"] == "withdrawn-proof"
    for claim in claims.values():
        parameter = claim.conclusion.get("coefficient_parameter")
        if parameter:
            assert parameter["value"] == 1 and parameter["domain"] == [1]
            assert claim.conclusion["coefficient_normalization"]["admission_independent"] is True
