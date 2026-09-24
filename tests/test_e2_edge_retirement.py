"""Generated E2 edge retirement must not depend on retiring either endpoint."""

import sys
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.atlas_transport import ensure_q8_atlas_transports
from domain.e2_import import materialize_all_q8_thom_e2_patterns, materialize_verified_e2_records
from domain.grading import ensure_q8_atlas
from domain.models import ClassNode, Grade, Project, Proposition, Workspace


def managed_edges(workspace):
    return [claim for claim in workspace.propositions
            if claim.kind == "relation" and claim.conclusion.get("chart_connection")]


def assert_valid_active_edges(workspace):
    nodes = {node.id: node for node in workspace.classes}
    active = [edge for edge in managed_edges(workspace) if edge.status != "superseded"]
    assert active
    incidence = set()
    for edge in active:
        source = nodes[edge.conclusion["source_id"]]
        target = nodes[edge.conclusion["target_id"]]
        connection = edge.conclusion["chart_connection"]
        kind = connection["kind"]
        assert (target.grade.stem - source.grade.stem,
                target.grade.filtration - source.grade.filtration) == {"h1": (1, 1), "h2": (3, 1)}[kind]
        assert connection["multiplier"] == {"h1": "h_1", "h2": "h_2"}[kind]
        key = (source.id, target.id, kind)
        assert key not in incidence, (workspace.id, edge.id)
        incidence.add(key)


def test_old_sigma_edge_is_retired_even_when_both_endpoint_classes_survive():
    source = ClassNode("sig_a", r"a_{\sigma_i}", Grade(-1, 1, {"sigma_i": -1}))
    target = ClassNode("e2_sigma_v12_usigma_i", r"v_1^2u_{\sigma_i}", Grade(4, 0, {"sigma_i": -1}))
    old = Proposition(
        "source_e2_edge_e2_sigma_i_cell_s7_f1_dm1_h1", "relation",
        r"h_1 multiplication: a_{\sigma_i} to v_1^2u_{\sigma_i}", status="established",
        conclusion={"source_id": source.id, "target_id": target.id, "page": 2,
                    "chart_connection": {"kind": "h1", "multiplier": "h_1", "hidden_extension": False},
                    "period_scope": ["D^8", "kD^3"]},
        rule="DKLLW24 E2 chart enumeration", notes="Retain the original observation.",
    )
    workspace = Workspace("ws_sigma_i", "sigma", classes=[source, target], propositions=[old])
    original_statement = old.statement
    result = materialize_verified_e2_records(workspace, "sigma_i")
    assert old.id in result["superseded_propositions"]
    assert old.status == "superseded"
    assert old.statement == original_statement
    assert old.notes == "Retain the original observation."
    assert old.conclusion["source_schema_retirement_previous_status"] == "established"
    assert old.conclusion["source_id"] == source.id and old.conclusion["target_id"] == target.id
    assert not source.archived and not target.archived
    current = next(edge for edge in managed_edges(workspace)
                   if edge.id == "source_e2_edge_e2_sigma_i_cell_S71_s7_f1_dm1_h1")
    current_target = next(node for node in workspace.classes if node.id == current.conclusion["target_id"])
    assert (current_target.grade.stem, current_target.grade.filtration) == (0, 2)
    assert_valid_active_edges(workspace)
    before = asdict(workspace)
    assert not materialize_verified_e2_records(workspace, "sigma_i")["superseded_propositions"]
    assert asdict(workspace) == before


def test_obsolete_integer_duplicates_retire_but_manual_and_custom_claims_are_unchanged():
    workspace = Workspace("ws_integer", "integer")
    materialize_verified_e2_records(workspace, "integer")
    current = next(edge for edge in managed_edges(workspace) if edge.id == "source_e2_edge_e2_integer_h1_h1")
    old = deepcopy(current)
    old.id = "source_e2_edge_e2_integer_cell_s1_f1_dp0_h1"
    # A valid degree alone is insufficient: obsolete parallel edges duplicate
    # the current catalogue product and must also be retired.
    manual = deepcopy(old)
    manual.id = "researcher-relation"
    manual.rule = "Manual relation"
    custom = deepcopy(old)
    custom.id = "source_e2_edge_custom_relation"
    custom.rule = "Researcher conjecture"
    manual_before, custom_before = asdict(manual), asdict(custom)
    workspace.propositions.extend([old, manual, custom])
    result = materialize_verified_e2_records(workspace, "integer")
    assert result["superseded_propositions"] == [old.id]
    assert current.status == "established" and old.status == "superseded"
    assert asdict(manual) == manual_before and asdict(custom) == custom_before


def test_current_owned_edge_refreshes_its_multiplier_without_restoring_researcher_review_status():
    workspace = Workspace("ws_integer", "integer")
    materialize_verified_e2_records(workspace, "integer")
    current = next(edge for edge in managed_edges(workspace) if edge.id == "source_e2_edge_e2_integer_h1_h1")
    current.status = "review"
    current.conclusion["chart_connection"].update({"kind": "h2", "multiplier": "h_2"})
    current.conclusion["chart_connection"]["researcher_note"] = "Keep this."
    materialize_verified_e2_records(workspace, "integer")
    assert current.status == "review"
    assert current.conclusion["chart_connection"]["researcher_note"] == "Keep this."
    assert_valid_active_edges(workspace)


def test_cleanup_covers_sixteen_thom_sectors_and_is_inherited_by_all_page_atlas_images():
    # Exercise only E2 enumeration and actual atlas transport, not the full
    # unrelated differential/proof migration pipeline.
    project = ensure_q8_atlas(Project("hfpss_studio", "edge audit"))
    materialize_all_q8_thom_e2_patterns(project)
    obsolete = {}
    for workspace in project.workspaces:
        old = deepcopy(managed_edges(workspace)[0])
        old.id = "source_e2_edge_obsolete_surviving_endpoints_h1"
        workspace.propositions.append(old)
        obsolete[workspace.id] = old
    materialize_all_q8_thom_e2_patterns(project)
    assert len(obsolete) == 16
    for workspace in project.workspaces:
        assert obsolete[workspace.id].status == "superseded"
        assert_valid_active_edges(workspace)

    ensure_q8_atlas_transports(project)
    images = [workspace for workspace in project.workspaces if workspace.settings.get("atlas_transport")]
    assert len(images) == 11
    for workspace in images:
        inherited = [edge for edge in managed_edges(workspace)
                     if edge.conclusion.get("atlas_transport", {}).get("source_proposition_id")
                     == "source_e2_edge_obsolete_surviving_endpoints_h1"]
        assert len(inherited) == 1 and inherited[0].status == "superseded"
        assert_valid_active_edges(workspace)
