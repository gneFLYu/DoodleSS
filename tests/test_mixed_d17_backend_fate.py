"""Actual-model scalar fates agree with the finite mixed d17 quotient.

The coefficient remains an unknown nonzero F4 unit. Period-family context is
required to certify isolated incidence, including for the transported atlases.
Virtual D8/g occurrences are audited by test_mixed_d17_forced.py in JavaScript;
this file checks the stored source/target records and their immutable events.
"""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.fate import (
    _isolated_rank_one_unit,
    class_is_live_on_page,
    derive_class_fate,
    sync_workspace_fates,
)
from domain.migrations import migrate_project
from domain.seed import demo_project
from test_mixed_d5_parameters import MIXED_ATLAS


FACT = "DER-MIX-D17-V-D3"
PARAMETER = "mixed_d17_VD3"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def records(project, workspace_id):
    workspace = next(item for item in project.workspaces if item.id == workspace_id)
    rows = [item for item in workspace.differentials if item.label == FACT]
    assert len(rows) == 1
    row = rows[0]
    claim = next(item for item in workspace.propositions if item.id == row.proposition_id)
    classes = {item.id: item for item in workspace.classes}
    return workspace, row, claim, classes[row.source_id], classes[row.target_id]


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_actual_mixed_d17_fates_without_choosing_the_unit(project, workspace_id):
    workspace, row, claim, source, target = records(project, workspace_id)
    original = deepcopy(claim.conclusion)
    reflected, shift = MIXED_ATLAS[workspace_id]
    assert (source.grade.stem, source.grade.filtration) == (24 + shift, 2)
    assert (target.grade.stem, target.grade.filtration) == (23 + shift, 19)
    assert row.status == claim.status == "verified"
    assert claim.conclusion["coefficient_parameter"]["frobenius_power"] == int(reflected)
    assert _isolated_rank_one_unit(workspace, row, project=project)

    sync_workspace_fates(workspace, project=project)
    events = [asdict(item) for item in workspace.differential_events]
    for node, role, conclusion in ((source, "supports", "supports_differential"),
                                   (target, "receives", "is_hit")):
        fate = derive_class_fate(workspace, node.id, project=project)
        assert fate.first_hfpss_death == {"page": 17, "role": role, "claim_id": row.id}
        assert fate.last_hfpss_live_page == fate.conclusion_page == 17
        assert fate.conclusion == conclusion
        assert claim.id in fate.justification_ids
        assert class_is_live_on_page(workspace, node.id, 17, project=project)
        for page in (18, 24):
            assert not class_is_live_on_page(workspace, node.id, page, project=project)

    sync_workspace_fates(workspace, project=project)
    assert [asdict(item) for item in workspace.differential_events] == events
    assert claim.conclusion == original
    assert claim.conclusion["coefficient_parameter"]["value"] is None
    assert PARAMETER not in workspace.settings.get("coefficient_assignments", {})


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_missing_period_family_context_does_not_invent_a_fate(project, workspace_id):
    workspace, row, claim, source, target = records(project, workspace_id)
    assert row.period_family_id
    assert not _isolated_rank_one_unit(workspace, row)
    history = deepcopy(workspace.differential_events)
    for node in (source, target):
        assert derive_class_fate(workspace, node.id).first_hfpss_death is None
        assert class_is_live_on_page(workspace, node.id, 18)
        # Explicit context restores the certified result after the conservative
        # context-free query; a cached unresolved fate must not hide it.
        assert derive_class_fate(workspace, node.id, project=project).first_hfpss_death["page"] == 17
        assert not class_is_live_on_page(workspace, node.id, 18, project=project)
    assert workspace.differential_events == history
    assert claim.conclusion["coefficient_parameter"]["value"] is None
