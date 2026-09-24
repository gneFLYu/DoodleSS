"""Only the read-only phase of one fate sync may memoize certificate admission."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain import fate
from domain.models import ClassNode, Grade, Project, Proposition, Workspace


def example():
    leaf = Proposition("leaf", "lemma", "External premise", status="verified")
    owner = Workspace("owner", "Source proofs", propositions=[leaf])
    nodes = [ClassNode(f"x-{n}", "x", Grade(64 * n, 0),
                       style={"e2_pattern": "I00"}) for n in range(80)]
    cycle = Proposition("cycle", "permanent-cycle", "No outgoing differential", status="verified",
        premise_ids=[leaf.id], conclusion={"source_id": nodes[0].id, "period_stem": 64,
            "external_premises": [{"workspace_id": owner.id, "proposition_id": leaf.id}]})
    workspace = Workspace("chart", "Chart", classes=nodes, propositions=[cycle])
    return Project("example", "Example", workspaces=[owner, workspace]), workspace, leaf, cycle


def test_repeated_class_admission_is_evaluated_once_per_sync(monkeypatch):
    project, workspace, _, _ = example()
    resolve = Mock(wraps=fate._uncached_cycle_premises_accepted)
    monkeypatch.setattr(fate, "_uncached_cycle_premises_accepted", resolve)
    fate.sync_workspace_fates(workspace, project=project)
    assert resolve.call_count == 1
    assert all(item.conclusion == "permanent_cycle" for item in workspace.fates)
    assert fate._CYCLE_PREMISE_CACHE.get() is None
    fate.sync_workspace_fates(workspace, project=project)
    assert resolve.call_count == 2


@pytest.mark.parametrize("change", ["withdraw", "remove", "duplicate", "replace", "link"])
def test_external_premise_edits_are_seen_by_next_sync(change):
    project, workspace, leaf, cycle = example()
    fate.sync_workspace_fates(workspace, project=project)
    assert workspace.fates[0].conclusion == "permanent_cycle"
    owner = project.workspaces[0]
    if change == "withdraw":
        leaf.status = "review"
    elif change == "remove":
        owner.propositions.clear()
    elif change == "duplicate":
        owner.propositions.append(deepcopy(leaf))
    elif change == "replace":
        owner.propositions[:] = [Proposition("leaf", "lemma", "Replacement", status="review")]
    else:
        cycle.premise_ids = ["missing"]
    fate.sync_workspace_fates(workspace, project=project)
    assert all(item.conclusion == "unresolved" for item in workspace.fates)


def test_independent_queries_never_reuse_previous_sync_or_query():
    project, workspace, leaf, cycle = example()
    fate.sync_workspace_fates(workspace, project=project)
    leaf.status = "review"
    assert not fate._cycle_premises_accepted(workspace, cycle, project)
    leaf.status = "verified"
    assert fate._cycle_premises_accepted(workspace, cycle, project)


def test_fates_and_immutable_inputs_match_uncached_implementation(monkeypatch):
    project, workspace, _, _ = example()
    before = asdict(project)
    fate.sync_workspace_fates(workspace, project=project)
    cached = asdict(project)
    monkeypatch.setattr(fate, "_cycle_premises_accepted", fate._uncached_cycle_premises_accepted)
    fate.sync_workspace_fates(workspace, project=project)
    assert asdict(project) == cached
    for actual, original in zip(cached["workspaces"], before["workspaces"]):
        assert actual["propositions"] == original["propositions"]
        assert actual["classes"] == original["classes"]


def test_exception_always_discards_sync_memo(monkeypatch):
    project, workspace, _, _ = example()
    def fail(*args, **kwargs):
        assert fate._CYCLE_PREMISE_CACHE.get() is not None
        raise RuntimeError("aborted sync")
    monkeypatch.setattr(fate, "_parameterized_event_eligibility", fail)
    with pytest.raises(RuntimeError, match="aborted sync"):
        fate.sync_workspace_fates(workspace, project=project)
    assert fate._CYCLE_PREMISE_CACHE.get() is None


def test_strict_and_legacy_admission_do_not_share_a_cache_entry():
    workspace = Workspace("w", "w")
    # An undeclared legacy premise is tolerated by the non-strict helper, not
    # by a qualified proof query which requires one unambiguous current row.
    claim = Proposition("unknown", "lemma", "Legacy", status="verified")
    token = fate._CYCLE_PREMISE_CACHE.set({})
    try:
        assert fate._cycle_premises_accepted(workspace, claim)
        assert not fate._cycle_premises_accepted(workspace, claim, strict=True)
    finally:
        fate._CYCLE_PREMISE_CACHE.reset(token)


def test_simultaneous_syncs_do_not_share_admission_state():
    def inspect(status):
        project, workspace, leaf, _ = example()
        leaf.status = status
        fate.sync_workspace_fates(workspace, project=project)
        assert fate._CYCLE_PREMISE_CACHE.get() is None
        return workspace.fates[0].conclusion
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(inspect, ["verified", "review"])) == ["permanent_cycle", "unresolved"]
