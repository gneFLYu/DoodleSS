"""Review summaries distinguish C3-only warnings from actual semilinear transport."""
from copy import deepcopy
from dataclasses import asdict

from backend.domain.actions import apply_s3_representation
from backend.domain.logic_graph import build_logic_graph, validate_logic_graph
from backend.domain.migrations import migrate_project
from backend.domain.reu_fact_chain import _MIXED_SUMMARY_REFRESH, ensure_reu_fact_chain
from backend.domain.seed import demo_project


def claims(project):
    return {p.id: p for w in project.workspaces for p in w.propositions}


def test_current_summary_matches_the_actual_mixed_atlas_path():
    project = migrate_project(demo_project())
    props = claims(project)
    guard = props["prop_reu_mixed_sector_guard"]
    transport = guard.conclusion["semilinear_transport"]
    target = next(w for w in project.workspaces if w.id == "ws_q8-ro-a2-b1")
    plan = target.settings["atlas_transport"]
    assert transport["omega_power"] == plan["omega_power"] == 1
    assert transport["reflected"] is plan["reflected"] is True
    assert transport["stem_shift"] == plan["stem_shift"] == 0
    assert apply_s3_representation({"sigma_i": -1, "sigma_j": -2}, 1, True) == {
        "sigma_i": -2, "sigma_j": -1,
    }
    assert guard.conclusion["c3_only_transport"] is False
    assert "unsupported_transport" not in guard.conclusion
    assert "Frobenius preserves zero sums" in guard.notes
    summary = props["prop_reu_mixed_formulas_review"]
    assert summary.status == "under-review" and "are admitted" not in summary.statement
    assert summary.conclusion["unresolved_parameters"] == ["mixed_d5_A", "mixed_d5_B"]
    for fact in summary.conclusion["independent_facts"]:
        canonical = [p for p in props.values() if p.conclusion.get("fact_id") == fact]
        assert canonical and all(p.status == "verified" for p in canonical)
    graph = build_logic_graph(project)
    assert validate_logic_graph(graph) == []
    node = next(n for n in graph["nodes"] if n["id"] == "proposition:prop_reu_mixed_formulas_review")
    assert not node["admitted"]


def test_legacy_summary_refresh_preserves_research_fields_and_is_idempotent():
    project = migrate_project(demo_project())
    props = claims(project)
    for ident, old in _MIXED_SUMMARY_REFRESH.items():
        p = props[ident]
        p.statement = old["statement"]
        p.notes = old["notes"] + "\nResearcher: retain my unresolved product check."
        p.conclusion["researcher_annotation"] = {"degree": [15, 3]}
        p.source_refs.append("researcher:private-proof")
    props["prop_reu_mixed_sector_guard"].conclusion["unsupported_transport"] = (
        "sigma_i+2sigma_j <-> 2sigma_i+sigma_j")
    rows_before = deepcopy([asdict(d) for w in project.workspaces for d in w.differentials])
    parameters_before = deepcopy([p.conclusion["coefficient_parameter"] for p in props.values()
                                  if "coefficient_parameter" in p.conclusion])
    ensure_reu_fact_chain(project)
    for ident, old in _MIXED_SUMMARY_REFRESH.items():
        p = props[ident]
        assert p.statement != old["statement"]
        assert old["notes"] not in p.notes
        assert "Researcher: retain my unresolved product check." in p.notes
        assert p.conclusion["researcher_annotation"] == {"degree": [15, 3]}
        assert "researcher:private-proof" in p.source_refs
    guard = props["prop_reu_mixed_sector_guard"]
    assert "unsupported_transport" not in guard.conclusion
    assert guard.conclusion["historical_c3_only_guard"]
    assert [asdict(d) for w in project.workspaces for d in w.differentials] == rows_before
    assert [p.conclusion["coefficient_parameter"] for p in props.values()
            if "coefficient_parameter" in p.conclusion] == parameters_before
    snapshot = deepcopy(asdict(project))
    ensure_reu_fact_chain(project)
    assert asdict(project) == snapshot


def test_custom_mixed_summary_is_not_overwritten():
    project = migrate_project(demo_project())
    props = claims(project)
    for ident in _MIXED_SUMMARY_REFRESH:
        props[ident].statement = "Researcher's custom summary of the mixed action."
    snapshot = {ident: deepcopy(asdict(props[ident])) for ident in _MIXED_SUMMARY_REFRESH}
    ensure_reu_fact_chain(project)
    assert {ident: asdict(props[ident]) for ident in _MIXED_SUMMARY_REFRESH} == snapshot
