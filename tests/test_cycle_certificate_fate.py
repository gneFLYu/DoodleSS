"""Zero-outgoing certificates qualify fate without deleting differential evidence."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.fate import (
    _cycle_claim_covers,
    class_is_live_on_page,
    derive_class_fate,
    sync_workspace_fates,
)
from domain.models import ClassNode, Differential, Grade, Proposition, Workspace


def node(workspace, ident, stem=12, filtration=0, **style):
    result = ClassNode(ident, ident, Grade(stem, filtration, {"sigma_i": -3}),
                       style={"e2_pattern": "S40", "two_valuation": 1, "j_order": 0, **style})
    workspace.classes.append(result)
    return result


def certificate(workspace, source, *, kind="permanent-cycle", status="verified-pattern",
                key="source_id", page=2, **conclusion):
    claim = Proposition("cycle", kind, "The specified class supports no differential.", status=status,
                        conclusion={key: source.id, "page": page, **conclusion})
    workspace.propositions.append(claim)
    return claim


def arrow(workspace, ident, source, page=5, *, target=None, parameter=None):
    target = target or node(workspace, ident + "-target", source.grade.stem - 1,
                            source.grade.filtration + page, e2_pattern="target-" + ident)
    conclusion = {"source_id": source.id, "target_id": target.id, "page": page}
    if parameter is not None:
        conclusion["coefficient_parameter"] = parameter
    claim = Proposition("claim-" + ident, "differential", ident, status="admitted", conclusion=conclusion)
    result = Differential(ident, source.id, target.id, page, status="admitted", proposition_id=claim.id)
    workspace.propositions.append(claim)
    workspace.differentials.append(result)
    return result, claim


def parameter(value=None, **extra):
    return {"id": "c", "value": value, "domain": [1, 2, 3], "frobenius_power": 0, **extra}


@pytest.mark.parametrize("key", ["source_id", "class_id"])
def test_actual_outgoing_conflict_blocks_current_and_later_not_earlier_and_keeps_history(key):
    workspace = Workspace("w", "HFPSS")
    earlier, _ = arrow(workspace, "earlier", node(workspace, "early", e2_pattern="early"), page=3)
    source = node(workspace, "source")
    outgoing, _ = arrow(workspace, "outgoing", source)
    same_page, _ = arrow(workspace, "same-page", node(workspace, "same", e2_pattern="same"))
    later, _ = arrow(workspace, "later", node(workspace, "later-source", e2_pattern="later"), page=9)
    sync_workspace_fates(workspace)
    history = [asdict(event) for event in workspace.differential_events]
    arrows = deepcopy(workspace.differentials)
    assert not class_is_live_on_page(workspace, source.id, 6)

    claim = certificate(workspace, source, key=key)
    for diff in (outgoing, same_page, later):
        for ident in (diff.source_id, diff.target_id):
            assert class_is_live_on_page(workspace, ident, diff.page + 1)
            assert derive_class_fate(workspace, ident).first_hfpss_death is None
    assert not class_is_live_on_page(workspace, earlier.source_id, 4)
    assert derive_class_fate(workspace, source.id).conclusion == "unresolved"
    sync_workspace_fates(workspace)
    assert workspace.differentials == arrows
    assert [asdict(event) for event in workspace.differential_events] == history
    assert derive_class_fate(workspace, source.id).hfpss_outgoing_events == ["event_outgoing_supports"]

    # Removing the last certificate must invalidate a previously masked cache.
    workspace.propositions.remove(claim)
    assert not class_is_live_on_page(workspace, source.id, 6)
    assert [asdict(event) for event in workspace.differential_events] == history


@pytest.mark.parametrize("filtration,last_live", [(0, "infinity"), (4, "unknown")])
def test_permanent_cycle_is_only_zero_outgoing_not_positive_filtration_survival(filtration, last_live):
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "cycle", filtration=filtration)
    certificate(workspace, source)
    fate = derive_class_fate(workspace, source.id)
    assert fate.conclusion == "permanent_cycle"
    assert fate.last_hfpss_live_page == last_live


def test_incoming_differential_can_kill_a_permanent_cycle():
    workspace = Workspace("w", "HFPSS")
    target = node(workspace, "cycle", filtration=7)
    certificate(workspace, target)
    source = node(workspace, "source", stem=13, filtration=2, e2_pattern="other")
    incoming, _ = arrow(workspace, "incoming", source, target=target)
    sync_workspace_fates(workspace)
    fate = derive_class_fate(workspace, target.id)
    assert fate.conclusion == "is_hit"
    assert fate.first_hfpss_death == {"page": 5, "role": "receives", "claim_id": incoming.id}
    assert fate.last_hfpss_live_page == 5
    assert not class_is_live_on_page(workspace, target.id, 6)


@pytest.mark.parametrize("status", ["review", "under-review", "rejected", "superseded", "source-proved"])
def test_unadmitted_certificate_is_inert(status):
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "source")
    certificate(workspace, source, status=status)
    arrow(workspace, "outgoing", source)
    sync_workspace_fates(workspace)
    assert derive_class_fate(workspace, source.id).conclusion == "supports_differential"
    assert not class_is_live_on_page(workspace, source.id, 6)


def test_zero_differential_certificate_is_page_specific():
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "source")
    claim = certificate(workspace, source, kind="zero-differential", page=5)
    assert not _cycle_claim_covers(workspace, claim, source, 3)
    assert _cycle_claim_covers(workspace, claim, source, 5)
    assert not _cycle_claim_covers(workspace, claim, source, 9)
    arrow(workspace, "later", source, page=9)
    sync_workspace_fates(workspace)
    assert derive_class_fate(workspace, source.id).first_hfpss_death["page"] == 9


@pytest.mark.parametrize("valuation,source_j,target_j,covered", [
    (0, 0, 0, False), (1, 0, 0, True), (2, 0, 0, True),
    (1, 0, 1, False), (1, 1, 0, False), (1, 1, 1, True),
])
def test_witt_two_threshold_and_distinct_constant_positive_j_ports(valuation, source_j, target_j, covered):
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "source", j_order=source_j)
    target = node(workspace, "target", two_valuation=valuation, j_order=target_j)
    claim = certificate(workspace, source)
    assert _cycle_claim_covers(workspace, claim, target, 13) is covered


@pytest.mark.parametrize("stem,filtration,covered", [
    (12, 0, True), (76, 0, True), (-52, 0, True),  # D^8 and its inverse
    (32, 4, True), (96, 4, True), (-32, 4, True),  # g D^{8n}, n arbitrary
    (52, 8, True), (-8, -4, False), (-72, -4, False),  # no inverse g
    (20, 0, False), (32, 3, False), (33, 4, False),
])
def test_d8_bilateral_and_g_forward_period_only(stem, filtration, covered):
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "source")
    target = node(workspace, "translate", stem=stem, filtration=filtration)
    claim = certificate(workspace, source, period_stem=64,
                        forward_period={"stem": 20, "filtration": 4, "nonnegative": True})
    assert _cycle_claim_covers(workspace, claim, target, 23) is covered


def test_actual_projective_vector_and_ro_degree_not_stale_source_basis_control_coverage():
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "source", e2_components={"P": 1, "Q": 2})
    target = node(workspace, "target", e2_components={"P": 2, "Q": 3},
                  e2_basis_patterns=["unrelated-source-basis"])
    claim = certificate(workspace, source)
    assert _cycle_claim_covers(workspace, claim, target, 5)
    target.style["e2_components"] = {"P": 1, "Q": 3}
    assert not _cycle_claim_covers(workspace, claim, target, 5)
    target.style["e2_components"] = {"P": 1, "Q": 2}
    target.grade.representation = {"sigma_j": -3}
    assert not _cycle_claim_covers(workspace, claim, target, 5)


@pytest.mark.parametrize("value,offset", [(None, 0), (1, 1)])
def test_unknown_or_zero_parameter_is_not_a_proved_cycle_contradiction(value, offset):
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "source")
    certificate(workspace, source)
    arrow(workspace, "parameterized", source, parameter=parameter(value, affine_offset=offset))
    legacy, _ = arrow(workspace, "legacy", node(workspace, "independent", e2_pattern="independent"), page=9)
    sync_workspace_fates(workspace)
    assert derive_class_fate(workspace, source.id).conclusion == "permanent_cycle"
    assert derive_class_fate(workspace, source.id).first_hfpss_death is None
    assert not class_is_live_on_page(workspace, legacy.source_id, 10)


@pytest.mark.parametrize("other,conflict", [(1, True), ("0", False)])
def test_zero_one_component_does_not_erase_other_target_components(other, conflict):
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "source")
    certificate(workspace, source)
    target = node(workspace, "target", e2_components={"P": other, "Q": 1})
    arrow(workspace, "outgoing", source, target=target,
          parameter=parameter(1, affine_offset=1, target_component="Q"))
    legacy, _ = arrow(workspace, "legacy", node(workspace, "independent", e2_pattern="independent"), page=9)
    sync_workspace_fates(workspace)
    assert class_is_live_on_page(workspace, legacy.source_id, 10) is conflict
    assert derive_class_fate(workspace, source.id).conclusion == ("unresolved" if conflict else "permanent_cycle")


def test_certificate_status_and_endpoint_port_edits_recheck_cached_fates():
    workspace = Workspace("w", "HFPSS")
    source = node(workspace, "source")
    translated = node(workspace, "translated", stem=76)
    claim = certificate(workspace, source, period_stem=64)
    arrow(workspace, "outgoing", translated)
    sync_workspace_fates(workspace)
    assert class_is_live_on_page(workspace, translated.id, 6)
    claim.status = "review"
    assert not class_is_live_on_page(workspace, translated.id, 6)
    claim.status = "verified-pattern"
    assert class_is_live_on_page(workspace, translated.id, 6)
    translated.style["two_valuation"] = 0
    assert not class_is_live_on_page(workspace, translated.id, 6)
    translated.style["two_valuation"] = 1
    translated.style["j_order"] = 1
    assert not class_is_live_on_page(workspace, translated.id, 6)
    translated.style["j_order"] = 0
    assert class_is_live_on_page(workspace, translated.id, 6)
