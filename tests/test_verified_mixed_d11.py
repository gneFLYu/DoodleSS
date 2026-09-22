"""Corrected mixed FN006 on the pristine production chart, without hypotheses.

The omega image of pure FN-2I-009 has unit one, but its Euler product is
zeta*x^3, so the mixed source x^3 has target coefficient zeta^2.  Reflection
conjugates that coefficient once.  The D2 and D6 blocks are separately
justified and repeat under D8, not an asserted permanent D4.

Every sequential Node invocation retains the full migrated project, including
integer period authority and the external premises.  No coefficient, claim,
matrix, admission status, or quotient is replaced by a test hypothesis.
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
FACT = "FN-MIX-006"
POWERS = (2, 6)
PAGES = (3, 4, 11, 12)
SIBLING_ID = "formal_diff_mixed_d11_r_D6_sibling"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [ws for ws in project.workspaces if ws.id == MIXED or
                ws.settings.get("atlas_transport", {}).get("source_workspace_id") == MIXED]
    assert {ws.id for ws in selected} == set(MIXED_ATLAS)
    return selected


def shift_of(workspace):
    return workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)


def records(workspace, power):
    claims = {claim.id: claim for claim in workspace.propositions}
    nodes = {node.id: node for node in workspace.classes}
    matches = [row for row in workspace.differentials
               if claims[row.proposition_id].conclusion.get("fact_id") == FACT
               and (nodes[row.source_id].grade.stem, nodes[row.source_id].grade.filtration)
               == (8 * power - 3 + shift_of(workspace), 3)]
    assert len(matches) == 1, (workspace.id, power, [row.id for row in matches])
    row = matches[0]
    return row, claims[row.proposition_id], nodes[row.source_id], nodes[row.target_id]


def occurrences(workspace):
    for power in POWERS:
        for d8 in (0, 64):
            for g in (0, 1):
                yield power, 8 * power - 3 + d8 + 20 * g + shift_of(workspace), 3 + 4 * g


def ports(page, pattern, stem, filtration):
    return set(next(probe["ports"] for probe in page["probes"]
                    if (probe["pattern"], probe["stem"], probe["filtration"])
                    == (pattern, stem, filtration)))


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes = set()
    for workspace in workspaces:
        for _, stem, filtration in occurrences(workspace):
            probes.update({
                ("S53", stem, filtration),
                ("S02", stem - 1, filtration + 11),
                # Possible earlier incoming d9: the C constant is an
                # outgoing d3 source and its entire j ideal is a d3 image.
                ("S11", stem, filtration + 2),
                # Possible earlier incoming d5: the entire U*h1 source
                # maps injectively under its primitive d3.
                ("S51", stem, filtration + 6),
            })
    payload = {
        "project": asdict(project), "workspaces": [ws.id for ws in workspaces],
        "pages": list(PAGES), "vectorAudit": True, "fact": FACT,
        "boundsByWorkspace": {
            ws.id: {"stemMin": shift_of(ws) + 8, "stemMax": shift_of(ws) + 132,
                    "filtrationMin": 0, "filtrationMax": 20} for ws in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
    }
    harness = (ROOT / "tests" / "chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    # Extend output only; all admissions, periodic occurrences, finite ports
    # and coefficients continue to use the unmodified production runtime.
    diagnostics = r"""return {mixedD11: edges
      .filter(e => ws.propositions.find(p => p.id === e.diff.proposition_id)?.conclusion?.fact_id === input.fact)
      .map(e => {const pair = algebra.endpoints(e.diff); return {
        id: e.diff.id, source: e.sourceGrade, target: e.targetGrade,
        admitted: algebra.canApply(e.diff), coefficient: algebra.coefficientState(e.diff),
        sourceLive: algebra.live(pair.source, e.sourceGrade),
        targetLive: algebra.live(pair.target, e.targetGrade),
        sourcePattern: pair.source.style.e2_pattern, targetPattern: pair.target.style.e2_pattern,
        sourceTwo: pair.source.style.two_valuation || 0, targetTwo: pair.target.style.two_valuation || 0,
        sourceJ: pair.source.style.j_order || 0, targetJ: pair.target.style.j_order || 0,
        sourceComponents: pair.source.style.e2_components || {[pair.source.style.e2_pattern]: 1},
        targetComponents: pair.target.style.e2_components || {[pair.target.style.e2_pattern]: 1}
      };}), mixedAdmissions: ws.differentials
      .filter(d => ws.propositions.find(p => p.id === d.proposition_id)?.conclusion?.fact_id === input.fact)
      .map(d => ({id: d.id, admitted: algebra.canApply(d), coefficient: algebra.coefficientState(d)})),
      page, points: points.length"""
    result = {}
    for workspace in workspaces:
        # Only the list of charts being evaluated is narrowed.  The full
        # project remains intact, and each process releases its own caches.
        completed = subprocess.run(
            ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
            input=json.dumps({**payload, "workspaces": [workspace.id]}),
            text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
        )
        rows = json.loads(completed.stdout)
        assert [row["id"] for row in rows] == [workspace.id]
        result[workspace.id] = {page["page"]: page for page in rows[0]["pages"]}
    return result


def test_both_mixed_d11_blocks_have_verified_independent_certificates(project):
    for workspace in images(project):
        for power in POWERS:
            row, claim, _, _ = records(workspace, power)
            metadata = claim.conclusion
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert metadata["source_status"] == "independently-verified"
            assert not metadata.get("source_blockers")
            assert not metadata.get("withdrawn_dependencies")
            assert not metadata.get("machine_verification_pending")
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["method"] == "omega-Euler product and finite E11 target survival"
            assert certificate["source_refs"] and certificate["derivation"]
            assert {"FN-2I-009", "FN-MIX-001", "FN-MIX-004"} <= set(certificate["premises"])
            assert not {"FN-MIX-002", "FN-MIX-003", "FN-MIX-005", "FN-3I-010",
                        "FN-3I-010-pc"} & set(certificate["premises"])
            assert not any("jan29" in premise.lower() or "jan.29" in premise.lower()
                           for premise in certificate["premises"])
            if row.linear_map_id:
                assert next(m for m in workspace.differential_maps if m.id == row.linear_map_id).status == "verified"


def test_exact_finite_endpoint_columns_and_d8_period_on_all_six_atlas(project):
    for workspace in images(project):
        for power in POWERS:
            row, claim, source, target = records(workspace, power)
            metadata = claim.conclusion
            assert row.page == metadata["page"] == 11
            assert row.period_stem == metadata["period_stem"] == 64
            assert metadata["period_kind"] == "same-object"
            assert metadata["period_is_invertible"] and metadata["period_multiplier"] == "D^8"
            assert (source.grade.stem, source.grade.filtration) == (8 * power - 3 + shift_of(workspace), 3)
            assert (target.grade.stem, target.grade.filtration) == (8 * power - 4 + shift_of(workspace), 14)
            for node, pattern in ((source, "S53"), (target, "S02")):
                assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                        node.style.get("j_order", 0)) == (pattern, 0, 0)
                assert node.style.get("e2_components", {pattern: 1}) == {pattern: 1}
            if power == 6:
                assert row.id.endswith(SIBLING_ID)
        left, right = (records(workspace, power) for power in POWERS)
        assert right[2].grade.stem - left[2].grade.stem == 32
        assert right[3].grade.stem - left[3].grade.stem == 32
        assert left[0].id != right[0].id


def test_mixed_unit_is_zeta_squared_and_reflection_conjugates_it_once(project):
    for workspace in images(project):
        reflected = int(workspace.settings.get("atlas_transport", {}).get("reflected", False))
        for power in POWERS:
            row, claim, _, _ = records(workspace, power)
            parameter = claim.conclusion["coefficient_parameter"]
            assert parameter["id"] == "mixed_d11_R"
            assert parameter["value"] == 3 and parameter["domain"] == [3]
            assert parameter["frobenius_power"] == reflected
            assert "zeta" in parameter["symbol"] and "2" in parameter["symbol"]
            assert "coefficient_condition" not in claim.conclusion
            assert "coefficient_normalization" not in claim.conclusion
            assert parameter["id"] not in workspace.settings.get("coefficient_assignments", {})
            assert "Source-basis F4 coefficient" in row.period_notes
            assert "atlas Frobenius is applied" in row.period_notes
            assert "exact unit not fixed" not in row.period_notes
        for name in ("mixed_d5_A", "mixed_d5_B"):
            assert name not in workspace.settings.get("coefficient_assignments", {})
            declarations = [claim.conclusion["coefficient_parameter"] for claim in workspace.propositions
                            if claim.conclusion.get("coefficient_parameter", {}).get("id") == name]
            assert declarations and all(spec.get("value") is None for spec in declarations)


def test_printed_unit_one_is_preserved_separately_from_the_verified_correction(project):
    for workspace in images(project):
        for power in POWERS:
            _, claim, _, _ = records(workspace, power)
            metadata = claim.conclusion
            printed = metadata["printed_source_formula"]
            assert printed["coefficient"] == 1 and printed["status"] == "review-corrected"
            assert printed["source_ref"]
            correction = metadata["coefficient_correction"]
            assert correction["status"] == "verified"
            assert correction["source_product_unit"] == 2
            assert correction["rotated_premise_unit"] == 1
            assert correction["normalized_target_unit"] == 3
            assert metadata["paired_pattern_stem"] == 32
            assert metadata["source_survival"]["status"] == "verified"
            assert metadata["target_survival"]["status"] == "verified"


def test_finite_sources_and_targets_live_through_e11_and_are_absent_on_e12(project, chart):
    for workspace in images(project):
        rows = chart[workspace.id]
        for _, stem, filtration in occurrences(workspace):
            for page in (3, 4, 11):
                assert ports(rows[page], "S53", stem, filtration) == {"0:0"}
                assert ports(rows[page], "S02", stem - 1, filtration + 11) == {"0:0"}
            assert ports(rows[12], "S53", stem, filtration) == set()
            assert ports(rows[12], "S02", stem - 1, filtration + 11) == set()


def test_earlier_incoming_c_and_uh1_slots_are_entirely_removed_by_d3(project, chart):
    for workspace in images(project):
        rows = chart[workspace.id]
        for _, stem, filtration in occurrences(workspace):
            c_ports = ports(rows[3], "S11", stem, filtration + 2)
            assert {"0:0", "0:1"} <= c_ports
            assert "0:0" in ports(rows[3], "S51", stem, filtration + 6)
            for page in (4, 11, 12):
                assert ports(rows[page], "S11", stem, filtration + 2) == set()
                assert ports(rows[page], "S51", stem, filtration + 6) == set()


def test_actual_d11_arrows_cover_both_blocks_d8_and_forward_g_with_exact_coefficients(project, chart):
    for workspace in images(project):
        expected_unit = 2 if workspace.settings.get("atlas_transport", {}).get("reflected") else 3
        drawn = chart[workspace.id][11]["mixedD11"]
        assert drawn
        for item in drawn:
            assert item["admitted"] and item["sourceLive"] and item["targetLive"]
            assert item["coefficient"]["resolved"] and item["coefficient"]["value"] == expected_unit
            assert (item["sourcePattern"], item["targetPattern"]) == ("S53", "S02")
            assert item["sourceTwo"] == item["targetTwo"] == item["sourceJ"] == item["targetJ"] == 0
            assert item["sourceComponents"] == {"S53": 1}
            # The effective endpoint includes the resolved unit exactly once;
            # the separately checked raw stored endpoint remains {S02: 1}.
            assert item["targetComponents"] == {"S02": expected_unit}
            assert item["target"]["stem"] == item["source"]["stem"] - 1
            assert item["target"]["filtration"] == item["source"]["filtration"] + 11
        for _, stem, filtration in occurrences(workspace):
            assert any((item["source"]["stem"], item["source"]["filtration"]) == (stem, filtration)
                       for item in drawn), (workspace.id, stem, filtration)


def test_d11_is_page_scoped_without_dangling_arrows_or_assuming_mixed_d5_answers(project, chart):
    for workspace in images(project):
        row_ids = {records(workspace, power)[0].id for power in POWERS}
        expected_unit = 2 if workspace.settings.get("atlas_transport", {}).get("reflected") else 3
        for page, result in chart[workspace.id].items():
            assert result["blockedFromPage"] is None
            assert not [item for item in result["dangling"] if item["id"] in row_ids]
            assert {item["id"] for item in result["mixedAdmissions"]} == row_ids
            assert all(item["admitted"] and item["coefficient"]["resolved"]
                       and item["coefficient"]["value"] == expected_unit
                       for item in result["mixedAdmissions"])
            assert bool(result["mixedD11"]) == (page == 11)
            # Unresolved P/Q d5 complements are outside these finite lines.
            # Certifying FN006 must not silently replace those maps by zero.
            for conflict in result["conflicts"]:
                assert conflict["page"] == 5
                assert conflict["block"].startswith("S22H+S22Y:")
                assert conflict["reason"] == "outgoing map is only specified on a proper subspace"
                assert 0 < conflict["definedRank"] < conflict["rank"]
