import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.migrations import migrate_project
from domain.published_differentials import (
    PUBLISHED_ARROWS,
    _published_e2_pattern,
    endpoint_component_style,
    ensure_published_differential_charts,
    page_horizontal_period_stem,
    published_arrow_counts,
)
from domain.seed import demo_project
from domain.models import ClassNode, Differential, Grade, Project, Proposition, Workspace


def test_positive_j_h1_sources_keep_the_bo_column_independent_of_factor_order():
    for workspace_id, prefix in (("ws_integer", "I"), ("ws_sigma_i", "S")):
        workspace = Workspace(workspace_id, "column audit")
        for power, suffix in ((1, "51"), (2, "62V"), (3, "73V")):
            h1 = "h_1" if power == 1 else f"h_1^{power}"
            for label in (f"{h1}v_1^6", f"v_1^6{h1}"):
                assert _published_e2_pattern(workspace, label, power) == prefix + suffix
                assert endpoint_component_style(label)["j_order"] == 1
        assert _published_e2_pattern(workspace, "v_1^4h_1^3", 3) == prefix + "33"


def test_table_import_does_not_retire_user_edits_or_remove_attached_research():
    modified = ClassNode("int_Dinvh1", "my edited class", Grade(101, 1))
    edited_period = ClassNode("int_D8", "my edited period", Grade(103, 0))
    obsolete = ClassNode("e2_integer_obsolete", r"v_1^4D^{-1}", Grade(4, 0))
    manual = ClassNode("user-id", r"v_1^4D^{-1}", Grade(4, 0))
    target = ClassNode("my-target", "target", Grade(3, 3))
    claim = Proposition("user-claim", "differential", "my retained claim", status="under-review")
    arrow = Differential("user-arrow", obsolete.id, target.id, 3, status="under-review", proposition_id=claim.id)
    workspace = Workspace("ws_integer", "integer", classes=[modified, edited_period, obsolete, manual, target],
                          propositions=[claim], differentials=[arrow])
    ensure_published_differential_charts(Project("hfpss_studio", "test", workspaces=[workspace]))
    assert not modified.archived and modified.label == "my edited class"
    assert not edited_period.archived and "e2_pattern" not in edited_period.style
    assert not manual.archived
    assert obsolete.archived
    assert claim in workspace.propositions and arrow in workspace.differentials


def test_complete_published_tables_are_materialized_with_correct_bidegrees():
    assert published_arrow_counts() == {"ws_integer": 24, "ws_sigma_i": 22}
    assert len(PUBLISHED_ARROWS) == 46
    assert all(
        arrow.target_stem == arrow.source_stem - 1
        and arrow.target_filtration == arrow.source_filtration + arrow.page
        for arrow in PUBLISHED_ARROWS
    )

    project = migrate_project(demo_project())
    workspaces = {item.id: item for item in project.workspaces}
    for workspace_id, expected in published_arrow_counts().items():
        workspace = workspaces[workspace_id]
        arrows = [item for item in workspace.differentials if item.id.startswith("published_diff_")]
        assert len(arrows) == expected
        assert all(
            item.status == "established"
            and item.period_stem == (64 if item.id == "published_diff_ws_integer_5" else page_horizontal_period_stem(item.page))
            for item in arrows
        )
        assert workspace.settings["convergence"]["stable_from_page"] == 24
        assert workspace.settings["convergence"]["status"] == "published-complete"
        classes = {item.id: item for item in workspace.classes}
        assert all(
            classes[endpoint].style.get("e2_pattern")
            for item in arrows
            for endpoint in (item.source_id, item.target_id)
        )
        # Every printed table row remains an independent family, even when
        # two coefficient levels share one Witt-square bidegree.
        assert len({item.source_id for item in arrows}) == expected
        propositions = {item.id: item for item in workspace.propositions}
        assert {
            propositions[item.proposition_id].conclusion["table_row"]
            for item in arrows
        } == set(range(1, expected + 1))
        assert all(
            propositions[item.proposition_id].conclusion["period_kind"]
            == "repeated-differential-pattern"
            for item in arrows
        )


def test_sigma_published_sources_use_the_correct_e2_cells():
    project = migrate_project(demo_project())
    sigma = next(item for item in project.workspaces if item.id == "ws_sigma_i")
    classes = {(item.label, item.grade.stem, item.grade.filtration): item for item in sigma.classes}
    assert (r"v_1^2u_{\sigma_i}", 4, 0) in classes
    assert (r"(h_1+xv_1)u_{\sigma_i}", 1, 1) in classes
    assert not any(r"\Theta_i" in item.label for item in sigma.classes if not item.archived)

    by_id = {item.id: item for item in sigma.classes}
    d3_sources = {
        (by_id[item.source_id].label, by_id[item.source_id].grade.stem, by_id[item.source_id].grade.filtration)
        for item in sigma.differentials
        if item.id.startswith("published_diff_") and item.page == 3
    }
    assert d3_sources == {
        (r"v_1^2u_{\sigma_i}", 4, 0),
        (r"(h_1+xv_1)u_{\sigma_i}", 1, 1),
    }


def test_pagewise_d_power_schedule_and_witt_tower_sources_use_distinct_ports():
    assert [page_horizontal_period_stem(page) for page in (2, 3, 4, 5, 6, 7, 8, 23)] == [
        8, 8, 8, 16, 16, 32, 64, 64,
    ]
    project = migrate_project(demo_project())
    atlas_workspace_ids = {item.workspace_id for item in project.grading_sectors}
    workspaces = {item.id: item for item in project.workspaces}
    assert atlas_workspace_ids
    for workspace_id in atlas_workspace_ids:
        schedule = workspaces[workspace_id].settings["rendering"]["page_horizontal_periods"]
        assert [item["stem"] for item in schedule] == [8, 16, 32, 64]

    integer = workspaces["ws_integer"]
    d7 = [
        item for item in integer.differentials
        if item.id.startswith("published_diff_") and item.page == 7
    ]
    by_id = {item.id: item for item in integer.classes}
    assert {by_id[item.source_id].label for item in d7} == {"4D", "2D^2", "D^{4}"}
    assert len({item.source_id for item in d7}) == 3
    scalar_ports = [by_id[item.source_id] for item in d7 if by_id[item.source_id].label in {"4D", "2D^2"}]
    assert all(not item.archived for item in scalar_ports)
    assert all(item.style.get("coefficient_port") for item in scalar_ports)
    assert all(item.style.get("coefficient_parent_id") for item in scalar_ports)
    assert all(item.style.get("dkllw_glyph") == "witt-j-series" for item in scalar_ports)


def test_demo_d5_of_d_squared_is_replaced_by_its_correct_leibniz_target():
    project = migrate_project(demo_project())
    integer = next(item for item in project.workspaces if item.id == "ws_integer")
    assert not any(item.id == "diff_int_d5_D2" for item in integer.differentials)
    assert not next(item for item in integer.classes if item.id == "int_D2").archived
    derived = next(item for item in integer.differentials if item.id == "leibniz_diff_integer_d5_D2")
    target = next(item for item in integer.classes if item.id == derived.target_id)
    assert target.label == r"2D^{-1}gh_2"
    assert target.style["two_valuation"] == 1
    assert derived.period_stem == 32
    sigma = next(item for item in project.workspaces if item.id == "ws_sigma_i")
    assert next(item for item in sigma.classes if item.id == "sig_x3").archived
