"""Exact incidence, scalar, and grading checks for the sixteen-sector atlas."""
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.actions import apply_omega_representation, apply_psi_representation, frobenius_scalar
from domain.atlas_transport import SOURCE_REPRESENTATIONS, ensure_q8_atlas_transports, q8_atlas_transport_plan
from domain.fate import class_is_live_on_page, sync_project_fates
from domain.grading import normalize_to_q8_sector
from domain.migrations import migrate_project
from domain.models import CellBasisVector, CellVectorSpace, ClassNode, DifferentialMap, Grade, NamedVector, Proposition, project_to_dict
from domain.seed import demo_project


def project_with_transports():
    project = migrate_project(demo_project())
    ensure_q8_atlas_transports(project)
    sync_project_fates(project)
    return project


def test_s3_relations_and_frobenius_are_exact():
    representation = {"sigma_i": 2, "sigma_j": -3, "sigma_k": 7, "H": 2}
    assert apply_omega_representation(representation, 3) == representation
    assert apply_psi_representation(apply_psi_representation(representation)) == representation
    assert apply_psi_representation(apply_omega_representation(apply_psi_representation(representation))) == apply_omega_representation(representation, 2)
    assert [frobenius_scalar(value) for value in ("0", "1", "zeta", "zeta^2")] == ["0", "1", "zeta^2", "zeta"]


def test_picard_reduction_keeps_dimension_correct_stem_and_source_status():
    project = migrate_project(demo_project())
    sigma_k = normalize_to_q8_sector(project, {"sigma_k": -1})
    three_k = normalize_to_q8_sector(project, {"sigma_k": -3})
    assert (sigma_k.sector_id, sigma_k.stem_shift) == ("q8-ro-a3-b3", -16)
    assert (three_k.sector_id, three_k.stem_shift % 64) == ("q8-ro-a1-b1", 16)
    assert sigma_k.status == "source-declared"
    assert "Tate-to-HFPSS" in sigma_k.obligations[0]
    for a in range(-5, 6):
        for b in range(-5, 6):
            for c in range(-5, 6):
                result = normalize_to_q8_sector(project, {"sigma_i": -a, "sigma_j": -b, "sigma_k": -c})
                assert result.sector_id == f"q8-ro-a{(a-c)%4}-b{(b-c)%4}"
                assert result.stem_shift == -16 * c


def test_five_computed_patterns_cover_all_sixteen_atlas_tiles():
    project = project_with_transports()
    plans = q8_atlas_transport_plan(project)
    assert len(plans) == 16
    counts = {source: sum(plan["source_workspace_id"] == source for plan in plans.values()) for source in SOURCE_REPRESENTATIONS}
    assert sorted(counts.values()) == [1, 3, 3, 3, 6]
    assert plans["q8-ro-a1-b1"]["source_workspace_id"] == "ws_3sigma_i"
    assert plans["q8-ro-a1-b1"]["stem_shift"] == 16
    assert plans["q8-ro-a3-b3"]["source_workspace_id"] == "ws_sigma_i"
    assert plans["q8-ro-a3-b3"]["stem_shift"] == -16
    assert plans["q8-ro-a2-b1"]["reflected"]


def test_atlas_s3_group_laws_include_picard_stem_shifts_mod_64():
    project = migrate_project(demo_project())

    def move(position, symbol):
        a, b, stem = position
        action = apply_omega_representation if symbol == "w" else apply_psi_representation
        normalized = normalize_to_q8_sector(project, action({"sigma_i": -a, "sigma_j": -b}))
        tile = next(sector for sector in project.grading_sectors if sector.id == normalized.sector_id)
        return tile.a, tile.b, (stem + normalized.stem_shift) % 64

    def word(position, symbols):
        for symbol in symbols:
            position = move(position, symbol)
        return position

    for a in range(4):
        for b in range(4):
            initial = a, b, 0
            assert word(initial, "www") == initial
            assert word(initial, "pp") == initial
            assert word(initial, "pwp") == word(initial, "ww")


def test_every_transported_arrow_and_endpoint_has_identical_page_fate():
    project = project_with_transports()
    by_id = {workspace.id: workspace for workspace in project.workspaces}
    transported_count = 0
    for target in project.workspaces:
        plan = target.settings.get("atlas_transport")
        if not plan:
            continue
        transported_count += 1
        source = by_id[plan["source_workspace_id"]]
        prefix = f"atlas_{plan['sector_id']}_"
        source_nodes = {node.id: node for node in source.classes}
        target_nodes = {node.id: node for node in target.classes}
        target_arrows = {arrow.id: arrow for arrow in target.differentials}
        for arrow in source.differentials:
            image = target_arrows[prefix + arrow.id]
            assert image.source_id == prefix + arrow.source_id
            assert image.target_id == prefix + arrow.target_id
            assert (image.page, image.period_stem, image.status) == (arrow.page, arrow.period_stem, arrow.status)
            for ident in (arrow.source_id, arrow.target_id):
                original, transported = source_nodes[ident], target_nodes[prefix + ident]
                assert transported.grade.stem - original.grade.stem == plan["stem_shift"]
                assert transported.grade.filtration == original.grade.filtration
                for page in (2, 3, 4, 5, 7, 9, 13, 17, 23, 24, 25):
                    assert class_is_live_on_page(target, transported.id, page) == class_is_live_on_page(source, original.id, page)
    assert transported_count == 11


def test_semilinear_transport_conjugates_matrix_and_vector_coordinates():
    project = migrate_project(demo_project())
    source = next(workspace for workspace in project.workspaces if workspace.id == "ws_sigma_i_2sigma_j")
    source.cells.extend([
        CellVectorSpace("test-source", Grade(1, 1), basis=[CellBasisVector("e", "e")], named_vectors=[NamedVector("v", "v", ["zeta"])]),
        CellVectorSpace("test-target", Grade(0, 4), basis=[CellBasisVector("f", "f")]),
    ])
    source.differential_maps.append(DifferentialMap("test-map", "test-source", "test-target", 3, [["zeta"]]))
    source.classes.append(ClassNode("test-port", "v", Grade(1, 1), cell_id="test-source", coordinates=["zeta"]))
    ensure_q8_atlas_transports(project)
    target = next(workspace for workspace in project.workspaces if workspace.id == "ws_q8-ro-a2-b1")
    prefix = "atlas_q8-ro-a2-b1_"
    assert next(item for item in target.differential_maps if item.id == prefix + "test-map").matrix == [["zeta^2"]]
    assert next(item for item in target.cells if item.id == prefix + "test-source").named_vectors[0].coordinates == ["zeta^2"]
    assert next(item for item in target.classes if item.id == prefix + "test-port").coordinates == ["zeta^2"]


def test_qualified_external_proof_is_not_renamed_as_a_local_atlas_collision():
    from domain.fate import _cycle_premises_accepted

    project = migrate_project(demo_project())
    source = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    external = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    # The local record is intentionally not usable as the external evidence.
    source.propositions.append(Proposition("collision-proof", "manual", "local", status="review"))
    external.propositions.append(Proposition("collision-proof", "manual", "external", status="verified"))
    source.propositions.append(Proposition(
        "qualified-cycle", "permanent-cycle", "external zero-outgoing evidence", status="verified",
        premise_ids=["collision-proof"], conclusion={"external_premises": [
            {"workspace_id": external.id, "proposition_id": "collision-proof"},
        ]},
    ))
    ensure_q8_atlas_transports(project)
    images = [w for w in project.workspaces
              if w.settings.get("atlas_transport", {}).get("source_workspace_id") == source.id]
    assert len(images) == 5
    for image in images:
        claim = next(p for p in image.propositions if p.id.endswith("_qualified-cycle"))
        assert claim.premise_ids == ["collision-proof"]
        assert claim.conclusion["external_premises"] == [
            {"workspace_id": external.id, "proposition_id": "collision-proof"},
        ]
        assert _cycle_premises_accepted(image, claim, project)
    external.propositions[-1].status = "review"
    for image in images:
        claim = next(p for p in image.propositions if p.id.endswith("_qualified-cycle"))
        assert not _cycle_premises_accepted(image, claim, project)


def test_pattern_components_follow_frobenius_without_changing_witt_metadata():
    project = migrate_project(demo_project())
    source = next(workspace for workspace in project.workspaces if workspace.id == "ws_sigma_i_2sigma_j")
    components = {"S22Y": "zeta", "S22H": "zeta^2", "unit": 1, "zero": 0,
                  "encoded-zeta": 2, "encoded-zeta-squared": 3}
    source.classes.append(ClassNode(
        "test-pattern-port", "v", Grade(6, 6),
        coordinates=["zeta", "zeta^2"], coefficient_context_id="q8-residue-f4",
        style={"e2_components": dict(components), "two_valuation": 2, "two_adic_valuation": 2},
    ))
    ensure_q8_atlas_transports(project)
    checked = set()
    for target in project.workspaces:
        plan = target.settings.get("atlas_transport", {})
        if plan.get("source_workspace_id") != source.id:
            continue
        image = next(node for node in target.classes if node.id.endswith("_test-pattern-port"))
        expected = ({"S22Y": "zeta^2", "S22H": "zeta", "unit": 1, "zero": 0,
                     "encoded-zeta": 3, "encoded-zeta-squared": 2}
                    if plan["reflected"] else components)
        assert image.style["e2_components"] == expected
        assert image.coordinates == (["zeta^2", "zeta"] if plan["reflected"] else ["zeta", "zeta^2"])
        assert image.style["two_valuation"] == image.style["two_adic_valuation"] == 2
        checked.add(plan["reflected"])
    assert checked == {False, True}
    assert source.classes[-1].style["e2_components"] == components


def test_picard_transport_moves_claim_grades_and_preserves_source_claims():
    project = migrate_project(demo_project())
    source = next(workspace for workspace in project.workspaces if workspace.id == "ws_sigma_i")
    source.propositions.append(Proposition(
        id="test-sigma-permanent", kind="permanent-cycle", statement="test position",
        status="review", conclusion={"grade": {"stem": 4, "filtration": 0,
                                                "representation": {"sigma_i": -1}}},
    ))
    ensure_q8_atlas_transports(project)
    workspaces = {workspace.id: workspace for workspace in project.workspaces}
    s11 = workspaces["ws_q8-ro-a1-b1"]
    zero = next(prop for prop in s11.propositions if prop.id.endswith("formal_prop_fn-3i-001-zero"))
    permanent = next(prop for prop in s11.propositions if prop.id.endswith("formal_prop_fn-3i-010-pc"))
    assert zero.conclusion["grade"] == {"stem": 17, "filtration": 1}
    assert permanent.conclusion["grade"] == {"stem": 13, "filtration": 5}
    s33 = workspaces["ws_q8-ro-a3-b3"]
    image = next(prop for prop in s33.propositions if prop.id.endswith("_test-sigma-permanent"))
    assert image.conclusion["grade"] == {
        "stem": -12, "filtration": 0, "representation": {"sigma_i": -3, "sigma_j": -3},
    }
    assert source.propositions[-1].conclusion["grade"]["stem"] == 4
    for target in project.workspaces:
        plan = target.settings.get("atlas_transport")
        if not plan:
            continue
        original = workspaces[plan["source_workspace_id"]]
        props = {prop.id: prop for prop in target.propositions}
        for prop in original.propositions:
            grade = prop.conclusion.get("grade")
            if not isinstance(grade, dict) or "stem" not in grade:
                continue
            image = props[f"atlas_{plan['sector_id']}_{prop.id}"]
            assert image.conclusion["grade"]["stem"] == grade["stem"] + plan["stem_shift"]
            assert image.conclusion["grade"]["filtration"] == grade["filtration"]
            assert image.status == prop.status


def test_formal_multidimensional_maps_keep_transported_basis_and_arrow_links():
    project = migrate_project(demo_project())
    workspaces = {workspace.id: workspace for workspace in project.workspaces}
    checked = 0
    for target in project.workspaces:
        plan = target.settings.get("atlas_transport")
        if not plan:
            continue
        source = workspaces[plan["source_workspace_id"]]
        prefix = f"atlas_{plan['sector_id']}_"
        cells = {cell.id: cell for cell in target.cells}
        maps = {linear.id: linear for linear in target.differential_maps}
        nodes = {node.id: node for node in target.classes}
        arrows = {arrow.id: arrow for arrow in target.differentials}
        for arrow in source.differentials:
            if not arrow.linear_map_id:
                continue
            image = arrows[prefix + arrow.id]
            linear = maps[image.linear_map_id]
            assert image.linear_map_id == prefix + arrow.linear_map_id
            assert linear.source_cell_id == nodes[image.source_id].cell_id
            assert linear.target_cell_id == nodes[image.target_id].cell_id
            assert linear.proposition_id == image.proposition_id
            for cell_id in (linear.source_cell_id, linear.target_cell_id):
                cell = cells[cell_id]
                original = next(item for item in source.cells if prefix + item.id == cell_id)
                assert [vector.id for vector in cell.basis] == [prefix + vector.id for vector in original.basis]
                for field in ("named_vectors", "display_basis"):
                    originals = getattr(original, field)
                    for vector, base in zip(getattr(cell, field), originals):
                        assert vector.id == prefix + base.id
                        expected = ([frobenius_scalar(value) for value in base.coordinates]
                                    if plan["reflected"] else base.coordinates)
                        assert vector.coordinates == expected
                assert cell.grade.stem == original.grade.stem + plan["stem_shift"]
            checked += 1
    assert checked == 7


def test_repeated_transport_keeps_custom_drawing_and_current_page():
    project = project_with_transports()
    target = next(workspace for workspace in project.workspaces if workspace.id == "ws_q8-ro-a0-b1")
    target.page = 13
    target.classes.append(ClassNode("manual-target", "manual", Grade(3, 2)))
    before = len(target.classes), len(target.differentials), len(target.propositions)
    ensure_q8_atlas_transports(project)
    assert target.page == 13
    assert (len(target.classes), len(target.differentials), len(target.propositions)) == before
    assert next(node for node in target.classes if node.id == "manual-target").label == "manual"


def test_complete_migrations_do_not_multiply_atlas_period_certificates():
    project = migrate_project(demo_project())

    def snapshot():
        return {
            "families": {item.id: asdict(item) for item in project.period_families},
            "propositions": {workspace.id: {item.id: asdict(item) for item in workspace.propositions}
                             for workspace in project.workspaces},
        }

    initial = snapshot()
    for _ in range(2):
        migrate_project(project)
        assert snapshot() == initial
        for workspace in project.workspaces:
            assert len({item.id for item in workspace.propositions}) == len(workspace.propositions)
            for differential in workspace.differentials:
                if differential.period_stem or differential.period_filtration:
                    certificate_id = f"prop_period_{differential.id}"
                    assert sum(prop.id == certificate_id for prop in workspace.propositions) == 1


def test_locally_archived_atlas_images_stay_archived_after_full_migration():
    project = migrate_project(demo_project())
    target = next(workspace for workspace in project.workspaces if workspace.id == "ws_q8-ro-a0-b1")
    node = next(node for node in target.classes if node.style.get("atlas_transport") and not node.archived)
    node.archived = True
    node.archived_reason = "Archived by Clear current canvas. User history retained."
    node_id = node.id
    source_id = node.style["atlas_transport"]["source_class_id"]
    target.page = 9
    migrate_project(project)
    image = next(node for node in target.classes if node.id == node_id)
    source = next(workspace for workspace in project.workspaces if workspace.id == "ws_sigma_i")
    assert image.archived
    assert image.archived_reason == "Archived by Clear current canvas. User history retained."
    assert not next(node for node in source.classes if node.id == source_id).archived
    assert target.page == 9


@pytest.fixture(scope="module")
def rendered_atlas():
    """Run the real viewport and port algebra for all sixteen persisted tiles."""
    # Full migration also issues each transported row's period certificate.
    # A bare transport refresh is an intermediate state, not an API response.
    project = migrate_project(demo_project())
    root = Path(__file__).resolve().parents[1]
    bounds = {"stemMin": -64, "stemMax": 127, "filtrationMin": 0, "filtrationMax": 64}
    payload = {
        "project": project_to_dict(project),
        "workspaces": [sector.workspace_id for sector in project.grading_sectors],
        "pages": [3, 9, 23, 24],
        "bounds": bounds,
        # Transport the viewport as well as its points. Long differentials
        # crossing an edge must remain visible, so equal unshifted windows
        # need not have the same boundary-arrow count after a Picard shift.
        "boundsByWorkspace": {
            workspace.id: {
                **bounds,
                "stemMin": bounds["stemMin"] + workspace.settings["atlas_transport"]["stem_shift"],
                "stemMax": bounds["stemMax"] + workspace.settings["atlas_transport"]["stem_shift"],
            }
            for workspace in project.workspaces if workspace.settings.get("atlas_transport")
        },
    }
    # Keep the full 16 x 4-page coverage and identical wide viewports, but
    # bound each workspace separately. A single timeout for all 64 page
    # computations conflated aggregate test duration with a hung chart.
    output = {}
    for workspace_id in payload["workspaces"]:
        workspace_payload = {**payload, "workspaces": [workspace_id]}
        completed = subprocess.run(
            ["node", "tests/chart_runtime.cjs"], cwd=root,
            input=json.dumps(workspace_payload), capture_output=True, check=True,
            text=True, encoding="utf-8", timeout=45,
        )
        workspace, = json.loads(completed.stdout)
        assert workspace["id"] == workspace_id
        output[workspace_id] = workspace["pages"]
    return project, output


def test_rendered_atlas_has_no_arrows_with_dead_periodic_endpoints(rendered_atlas):
    _, output = rendered_atlas
    assert len(output) == 16
    invalid = [(workspace, page["page"], page["dangling"])
               for workspace, pages in output.items() for page in pages if page["dangling"]]
    assert not invalid, invalid
    for workspace, pages in output.items():
        for page in pages:
            assert page["renderedEndpointCount"] == page["edges"]
            assert not set(page["zeroRows"]).intersection(page["rows"]), (workspace, page["page"])
            assert page["nonzeroEndpointMapCount"] == page["edges"], (workspace, page["page"])
    dead_anchors = [(workspace, page["page"], anchor)
                    for workspace, pages in output.items() for page in pages for anchor in page["anchors"]
                    if anchor["sourceDead"] or anchor["targetDead"]]
    assert not dead_anchors, dead_anchors


def test_rendered_atlas_preserves_each_table_row_and_its_live_quotient(rendered_atlas):
    project, output = rendered_atlas
    for workspace in project.workspaces:
        transport = workspace.settings.get("atlas_transport")
        if not transport:
            continue
        source_pages = output[transport["source_workspace_id"]]
        prefix = f"atlas_{transport['sector_id']}_"
        for source, target in zip(source_pages, output[workspace.id]):
            assert target["page"] == source["page"]
            assert target["points"] == source["points"], (workspace.id, target["page"])
            assert target["edges"] == source["edges"], (workspace.id, target["page"])
            assert set(target["rows"]) == {prefix + ident for ident in source["rows"]}
            assert target["high"] == source["high"]
            # This is a published Table9 convergence assertion, not a blanket
            # assertion that the research-note sectors have already converged.
            if transport["source_workspace_id"] == "ws_sigma_i" and target["page"] == 24:
                assert target["high"] == 0
