"""Verified four-block Phi transport on the unmodified production chart.

D0/D1/D4/D5 retain external coefficient links to the independently verified
pure-three-sigma C-D6/C-D7/C-D2/C-D3 rows, not mixed-local assignments.
The finite S73 target is distinct from its same-cell S73V d3 source.
Sequential isolated chart-runtime processes cover all six mixed atlas images,
D8 and g, retaining the full project for external source-parameter links.
No fixture admits hypotheses or changes coefficients, matrices, or algebra.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.seed import demo_project
from test_mixed_d5_parameters import MIXED_ATLAS


MIXED = "ws_sigma_i_2sigma_j"
THREE = "ws_3sigma_i"
POWERS = {0: 6, 1: 7, 4: 2, 5: 3}
FACTS = {power: f"DER-MIX-PHI-D9-D{power}" for power in POWERS}
SOURCE_IDS = {power: f"formal_diff_three_d9_c_D{n}_{'derived' if n % 2 == 0 else 'euler_derived'}"
              for power, n in POWERS.items()}
SOURCE_FACTS = {power: "DER-3I-D9-C" if n % 2 == 0 else "DER-3I-EULER-D9-C"
                for power, n in POWERS.items()}
PARAMETER_IDS = {power: f"three_sigma_d9_{'D' if n % 2 == 0 else 'CD'}{n}"
                 for power, n in POWERS.items()}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    result = [w for w in project.workspaces if w.id == MIXED or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == MIXED]
    assert {w.id for w in result} == set(MIXED_ATLAS)
    return result


def shift_of(workspace):
    return workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)


def records(workspace, power):
    row = next(d for d in workspace.differentials if d.label == FACTS[power])
    claim = next(p for p in workspace.propositions if p.id == row.proposition_id)
    nodes = {n.id: n for n in workspace.classes}
    return row, claim, nodes[row.source_id], nodes[row.target_id]


def ports(page, pattern, stem, filtration):
    return set(next(p["ports"] for p in page["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


def occurrences(workspace):
    for power in POWERS:
        for d8 in (0, 64):
            for g in (0, 1):
                yield power, 8 * power + d8 + 20 * g + shift_of(workspace), 2 + 4 * g


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes = set()
    for ws in workspaces:
        for _, stem, filtration in occurrences(ws):
            probes.add(("S02", stem, filtration))
            probes.add(("S73", stem - 1, filtration + 9))
            probes.add(("S73V", stem - 1, filtration + 9))
            # This incoming-d7 slot loses both its odd U and even 2U layers
            # by the two independently verified mixed d3 maps.
            probes.add(("S40", stem, filtration + 2))
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [3, 4, 9, 10], "vectorAudit": True, "phiFacts": list(FACTS.values()),
        "boundsByWorkspace": {
            w.id: {"stemMin": shift_of(w) - 1, "stemMax": shift_of(w) + 125,
                   "filtrationMin": 0, "filtrationMax": 16} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
    }
    # Only extend the shared harness's output. Every map, quotient and
    # coefficient is still evaluated by the actual production implementation.
    harness = (ROOT / "tests" / "chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {phiOccurrences: edges
      .filter(e => input.phiFacts.includes(e.diff.label))
      .map(e => {const pair = algebra.endpoints(e.diff); return {
        id: e.diff.id, fact: e.diff.label, source: e.sourceGrade, target: e.targetGrade,
        admitted: algebra.canApply(e.diff), coefficient: algebra.coefficientState(e.diff),
        sourceLive: algebra.live(classes.get(e.diff.source_id), e.sourceGrade),
        targetLive: algebra.live(classes.get(e.diff.target_id), e.targetGrade),
        sourcePattern: pair.source.style.e2_pattern, targetPattern: pair.target.style.e2_pattern,
        sourceTwo: pair.source.style.two_valuation || 0, targetTwo: pair.target.style.two_valuation || 0,
        sourceJ: pair.source.style.j_order || 0, targetJ: pair.target.style.j_order || 0,
        targetComponents: pair.target.style.e2_components || {[pair.target.style.e2_pattern]: 1}
      };}), phiAdmissions: ws.differentials
      .filter(d => input.phiFacts.includes(d.label))
      .map(d => ({fact: d.label, admitted: algebra.canApply(d)})), page, points: points.length"""
    chart = {}
    for workspace in workspaces:
        # Release each chart's runtime caches before rendering the next atlas
        # image. Keep every workspace in project: Phi resolves coefficients
        # against its external pure-three-sigma source, not a local substitute.
        completed = subprocess.run(
            ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
            input=json.dumps({**payload, "workspaces": [workspace.id]}),
            text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
        )
        rows = json.loads(completed.stdout)
        assert [w["id"] for w in rows] == [workspace.id]
        chart.update({w["id"]: {p["page"]: p for p in w["pages"]} for w in rows})
    return chart


def test_all_four_phi_rows_have_independent_verified_certificates(project):
    for ws in images(project):
        claims = {p.id: p for p in ws.propositions}
        for power in POWERS:
            row, claim, source, target = records(ws, power)
            metadata = claim.conclusion
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"] and not metadata.get("withdrawn_dependencies")
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["source_refs"] and certificate["derivation"]
            assert certificate["method"] == "Permanent Phi transport and finite Euler target survival"
            assert {SOURCE_FACTS[power], "FN-MIX-001"} <= set(certificate["premises"])
            for dependencies in (metadata["derived_from"], certificate["premises"]):
                assert not {"FN-3I-010", "FN-3I-010-pc"} & set(dependencies)
                assert not any("jan29" in p.lower() or "jan.29" in p.lower() for p in dependencies)
            assert row.page == 9 and row.period_stem == metadata["period_stem"] == 64
            assert metadata["period_kind"] == "same-object" and metadata["period_is_invertible"]
            assert metadata["period_multiplier"] == "D^8"
            assert (source.grade.stem, source.grade.filtration) == (8 * power + shift_of(ws), 2)
            assert (target.grade.stem, target.grade.filtration) == (8 * power - 1 + shift_of(ws), 11)
            for node, pattern in ((source, "S02"), (target, "S73")):
                assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                        node.style.get("j_order", 0)) == (pattern, 0, 0)
            if row.linear_map_id:
                assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"
        phi_rows = [d for d in ws.differentials if d.label in FACTS.values()]
        assert len(phi_rows) == 4
        assert all(d.status == claims[d.proposition_id].status == "verified" for d in phi_rows)


def test_phi_keeps_external_source_parameter_links_without_normalizing_mixed_coefficients(project):
    source_ws = next(w for w in project.workspaces if w.id == THREE)
    source_claims = {p.id: p for p in source_ws.propositions}
    for ws in images(project):
        reflected = int(ws.settings.get("atlas_transport", {}).get("reflected", False))
        for power, n in POWERS.items():
            row, claim, _, _ = records(ws, power)
            metadata = claim.conclusion
            parameter = metadata["coefficient_parameter"]
            assert parameter["id"] == PARAMETER_IDS[power]
            assert parameter["value"] is None and parameter["domain"] == [1, 2, 3]
            assert parameter["frobenius_power"] == reflected
            assert parameter["source_parameter"] == {
                "workspace_id": THREE, "parameter_id": parameter["id"],
                "differential_id": SOURCE_IDS[power], "page": 9,
            }
            assert parameter["id"] not in ws.settings.get("coefficient_assignments", {})
            assert "coefficient_normalization" not in metadata
            assert "coefficient_condition" not in metadata
            source_row = next(d for d in source_ws.differentials if d.id == SOURCE_IDS[power])
            source_claim = source_claims[source_row.proposition_id]
            assert source_row.status == source_claim.status == "verified"
            assert source_row.label == SOURCE_FACTS[power]
            source_parameter = source_claim.conclusion["coefficient_parameter"]
            assert source_parameter["id"] == parameter["id"]
            assert source_parameter["value"] == 1 and source_parameter["domain"] == [1]
        for name in ("mixed_d5_A", "mixed_d5_B"):
            assert name not in ws.settings.get("coefficient_assignments", {})
            declarations = [p.conclusion["coefficient_parameter"] for p in ws.propositions
                            if p.conclusion.get("coefficient_parameter", {}).get("id") == name]
            assert declarations and all(spec.get("value") is None for spec in declarations)


def test_transport_uses_inverse_phi_and_only_permanent_d8_translation(project):
    for ws in images(project):
        for power, n in POWERS.items():
            _, claim, _, _ = records(ws, power)
            metadata = claim.conclusion
            transport = metadata["transport_certificate"]
            assert transport["source_workspace_id"] == THREE
            assert transport["source_differential_id"] == SOURCE_IDS[power]
            assert transport["source_power"] == n and transport["action"] == "omega^2"
            assert transport["phi_stem_shift"] == -16 and transport["phi_filtration_shift"] == 0
            assert transport["applied_inverse"] and transport["euler_multiplier"] == "a_sigma_j"
            assert transport["final_D_exponent"] == (-8 if power < 2 else 0)
            assert n + 2 + transport["final_D_exponent"] == power
            assert "common Thom unit cancels" in metadata["derivation"]
            assert "D^4 is not used as a 9-cycle" in metadata["derivation"]
            assert metadata["target_survival"]["nonzero_condition"] == "independent of mixed_d5_A and mixed_d5_B"


def test_printed_thirty_two_stem_pattern_uses_two_separately_verified_d8_families(project):
    for ws in images(project):
        for left, right in ((0, 4), (1, 5)):
            left_row, left_claim, left_source, left_target = records(ws, left)
            right_row, right_claim, right_source, right_target = records(ws, right)
            assert right_source.grade.stem - left_source.grade.stem == 32
            assert right_target.grade.stem - left_target.grade.stem == 32
            assert right_source.grade.filtration == left_source.grade.filtration == 2
            assert right_target.grade.filtration == left_target.grade.filtration == 11
            assert left_row.period_stem == right_row.period_stem == 64
            assert SOURCE_IDS[left] != SOURCE_IDS[right]
            for power, claim in ((left, left_claim), (right, right_claim)):
                metadata = claim.conclusion
                comparison = metadata["related_period_table"]
                assert comparison["printed_period_stem"] == 32
                assert comparison["status"] == "independently-compared"
                assert comparison["source_ref"] == f"REU Projects/table_Q8.tex:{520 if power % 2 else 521}"
                assert "Two separately verified D8 families" in comparison["interpretation"]
                assert "D4 is not used as a permanent unit" in comparison["interpretation"]
                assert metadata["period_is_invertible"] and metadata["period_multiplier"] == "D^8"
                assert metadata["transport_certificate"]["source_differential_id"] == SOURCE_IDS[power]


def test_phi_source_d7_certificates_are_scoped_zero_maps_not_permanent_cycles(project):
    for ws in images(project):
        nodes = {n.id: n for n in ws.classes}
        for power in POWERS:
            fact = f"DER-MIX-PHI-D7-D{power}-zero"
            claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == fact)
            metadata = claim.conclusion
            assert claim.kind == "zero-differential"
            assert claim.status == metadata["admission_status"] == "verified"
            assert metadata["page"] == 7 and metadata["zero"] is True
            assert metadata["cycle_constraint"] == "outgoing-only"
            assert metadata["period_stem"] == 64
            assert metadata["forward_period"] == {
                "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
            }
            assert metadata["e2_components"] == {"S02": 1}
            assert SOURCE_FACTS[power] in metadata["derived_from"]
            assert "FN-3I-010-pc" not in metadata["derived_from"]
            source = nodes[metadata["source_id"]]
            assert (source.grade.stem, source.grade.filtration) == (8 * power + shift_of(ws), 2)
            assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                    source.style.get("j_order", 0)) == ("S02", 0, 0)
            assert metadata["verification_certificate"]["status"] == "verified"
        # The runtime tests below require these same sources to support d9.
        # A page-7 zero must never become an all-later-page immunity rule.


def test_s73v_dies_by_d3_while_the_finite_phi_target_remains_until_d9(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for _, stem, filtration in occurrences(ws):
            assert "0:0" in ports(rows[3], "S73V", stem - 1, filtration + 9)
            assert "0:0" in ports(rows[3], "S40", stem, filtration + 2)
            assert "1:0" in ports(rows[3], "S40", stem, filtration + 2)
            for page in (4, 9, 10):
                assert ports(rows[page], "S73V", stem - 1, filtration + 9) == set()
                assert ports(rows[page], "S40", stem, filtration + 2) == set()
            for page in (3, 4, 9):
                assert ports(rows[page], "S73", stem - 1, filtration + 9) == {"0:0"}
        assert any(d.endswith("formal_diff_mixed_d3_h1_3_derived") for d in rows[3]["rows"])


def test_all_phi_blocks_remove_only_their_finite_source_and_target_on_e10_in_all_atlas_images(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for _, stem, filtration in occurrences(ws):
            for page in (3, 4, 9):
                assert ports(rows[page], "S02", stem, filtration) == {"0:0"}
            assert ports(rows[10], "S02", stem, filtration) == set()
            assert ports(rows[10], "S73", stem - 1, filtration + 9) == set()


def test_actual_phi_arrows_have_live_endpoints_and_source_linked_unit_one(project, chart):
    for ws in images(project):
        drawn = chart[ws.id][9]["phiOccurrences"]
        assert drawn
        for item in drawn:
            assert item["admitted"] and item["sourceLive"] and item["targetLive"]
            assert item["coefficient"]["resolved"] and item["coefficient"]["value"] == 1
            assert (item["sourcePattern"], item["targetPattern"]) == ("S02", "S73")
            assert item["sourceTwo"] == item["targetTwo"] == 0
            assert item["sourceJ"] == item["targetJ"] == 0
            assert item["targetComponents"] == {"S73": 1}
            assert item["target"]["stem"] == item["source"]["stem"] - 1
            assert item["target"]["filtration"] == item["source"]["filtration"] + 9
        for power, stem, filtration in occurrences(ws):
            assert any(item["fact"] == FACTS[power]
                       and (item["source"]["stem"], item["source"]["filtration"]) == (stem, filtration)
                       for item in drawn), (ws.id, power, stem, filtration)


def test_all_phi_arrows_are_e9_only_with_verified_q_closure_and_unassigned_units(project, chart):
    for ws in images(project):
        # The independent finite-target injection now proves d5(Q)=0,
        # including its completed tail. This is not a choice of b=1 or
        # a consequence of the Phi d9 rows. Check the actual certificate
        # before expecting the old proper-subspace barrier to be absent.
        q_zero = next(p for p in ws.propositions
                      if p.conclusion.get("fact_id") == "FN-MIX-005-Q-zero")
        assert q_zero.kind == "zero-differential" and q_zero.status == "verified"
        assert q_zero.conclusion["page"] == 5 and q_zero.conclusion["zero"] is True
        proof = q_zero.conclusion["verification_certificate"]
        assert proof["status"] == "verified"
        assert "DER-MIX-D5-B-NONZERO" in proof["premises"]
        assert proof["target_injection"]["source_bidegree"] == [1, 7]
        assert proof["target_injection"]["target_bidegree"] == [13, 11]
        nonzero = proof["nonzero_parameter_certificate"]
        assert nonzero["status"] == "verified"
        assert nonzero["domain"] == [1, 2, 3] and nonzero["value"] is None
        b_claims = [p for p in ws.propositions if p.conclusion.get("fact_id") == "FN-MIX-005"]
        assert b_claims and all(p.status == "review" for p in b_claims)
        for claim in b_claims:
            parameter = claim.conclusion["coefficient_parameter"]
            assert parameter["domain"] == [1, 2, 3] and parameter["value"] is None
            assert parameter["id"] not in ws.settings.get("coefficient_assignments", {})
        for page, row in chart[ws.id].items():
            assert row["blockedFromPage"] is None
            assert not row["conflicts"], (ws.id, page, row["conflicts"])
            assert not [d for d in row["dangling"] if any(d["id"].endswith(
                f"formal_diff_mixed_phi_d9_D{p}") for p in POWERS)]
            assert {d["fact"] for d in row["phiAdmissions"]} == set(FACTS.values())
            assert all(d["admitted"] for d in row["phiAdmissions"])
            if page == 9:
                assert row["phiOccurrences"]
            else:
                assert row["phiOccurrences"] == []
