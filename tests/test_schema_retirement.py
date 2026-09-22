"""Source-schema corrections retire generated motifs without erasing research."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.e2_import import materialize_verified_e2_records, materialize_all_q8_thom_e2_patterns, verified_e2_classes
from domain.formal_notes_chart import _occurrence_style, _reconcile_original_demo_aliases
from domain.grading import ensure_q8_atlas
from domain.migrations import migrate_project
from domain.models import ClassFate, ClassNode, Differential, Grade, Project, Proposition, Workspace, project_to_dict
from domain.published_differentials import _node_for, ensure_published_differential_charts
from domain.seed import demo_project


def attach_old_motif(workspace, ident, source_rule):
    node = ClassNode(ident, "old schema motif", Grade(101, 2), style={"e2_pattern": "obsolete"})
    other = ClassNode("user-endpoint", "user endpoint", Grade(100, 5))
    relation = Proposition("user-relation", "relation", "User's old-motif relation", status="candidate",
                           conclusion={"source_id": node.id, "target_id": other.id}, rule="manual")
    claim = Proposition("user-claim", "differential", "User's old-motif differential", status="under-review",
                        conclusion={"source_id": node.id, "target_id": other.id, "page": 3}, rule="manual")
    generated = Proposition("source_e2_obsolete", "source", "Old generated declaration", status="established",
                            conclusion={"class_id": node.id}, rule=source_rule)
    arrow = Differential("user-differential", node.id, other.id, 3, status="under-review", proposition_id=claim.id,
                         unperiodic_reason="User supplied no periodicity assertion.")
    fate = ClassFate(node.id, conclusion="unresolved")
    workspace.classes.extend([node, other])
    workspace.propositions.extend([relation, claim, generated])
    workspace.differentials.append(arrow)
    workspace.fates.append(fate)
    return node, deepcopy([asdict(item) for item in (other, relation, claim, arrow, fate)])


def assert_research_retained(workspace, node, original, *, generated_retired):
    by_id = {item.id: item for item in workspace.classes}
    props = {item.id: item for item in workspace.propositions}
    assert node.id in by_id
    assert by_id[node.id].archived
    assert "source-schema correction" in by_id[node.id].archived_reason or "E2-only placeholder" in by_id[node.id].archived_reason
    assert [asdict(item) for item in (
        by_id["user-endpoint"], props["user-relation"], props["user-claim"],
        next(item for item in workspace.differentials if item.id == "user-differential"),
        next(item for item in workspace.fates if item.class_id == node.id),
    )] == original
    if generated_retired:
        assert props["source_e2_obsolete"].status == "superseded"


@pytest.mark.parametrize("mode", ["catalogue", "thom", "published"])
def test_source_cleanup_archives_original_nodes_and_keeps_user_records(mode):
    project = Project("hfpss_studio", "Research")
    ensure_q8_atlas(project)
    workspace_id = "ws_2sigma_i" if mode == "thom" else "ws_integer"
    workspace = next(item for item in project.workspaces if item.id == workspace_id)
    ident = {"catalogue": "e2_integer_obsolete", "thom": "e2_thom_a2_b0_obsolete",
             "published": "published_class_ws_integer_obsolete"}[mode]
    node, original = attach_old_motif(workspace, ident, "ThomIsomorphism + DKLLW24 E2 pattern" if mode == "thom" else "DKLLW24 E2 source import")
    if mode == "catalogue":
        def apply():
            result = materialize_verified_e2_records(workspace, "integer")
            assert result["removed_classes"] == []
            assert node.id in result["archived_classes"]
    elif mode == "thom":
        def apply():
            materialize_all_q8_thom_e2_patterns(project)
    else:
        def apply():
            ensure_published_differential_charts(project)
    apply()
    assert_research_retained(workspace, node, original, generated_retired=True)
    counts = len(workspace.classes), len(workspace.propositions), len(workspace.differentials)
    apply()
    assert counts == (len(workspace.classes), len(workspace.propositions), len(workspace.differentials))
    assert_research_retained(workspace, node, original, generated_retired=True)

    # Exercise the actual frontend predicate, including its E2-pattern bypass
    # of ordinary fate handling. Archiving must still hide the old motif.
    script = r"""
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{HFPSSPageAlgebra:{}}});
const script=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(script.slice(0,script.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.input=input;
process.stdout.write(JSON.stringify(vm.runInContext(`state.project=input.project;
liveClassesAt(input.project.workspaces.find(w=>w.id===input.workspace),2).map(c=>c.id)`,context)));
"""
    output = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, check=True,
                            text=True, encoding="utf-8", input=json.dumps({"project": project_to_dict(project), "workspace": workspace.id}))
    assert node.id not in json.loads(output.stdout)


def test_retired_alias_does_not_replace_the_correct_current_catalogue_record():
    record = verified_e2_classes("integer")[0]
    workspace = Workspace("ws_integer", "integer")
    old = ClassNode("e2_integer_old_id", record.label, Grade(record.stem, record.filtration, record.representation))
    workspace.classes.append(old)
    materialize_verified_e2_records(workspace, "integer")
    assert old.archived
    assert any(node.id == record.id and not node.archived for node in workspace.classes)


def test_published_endpoints_skip_schema_aliases_but_preserve_user_archives():
    workspace = Workspace("ws_integer", "integer")
    retired = ClassNode("e2_integer_old", "h_2^2", Grade(6, 2), archived=True,
                        archived_reason="Retired generated E2 motif after source-schema correction.")
    current = ClassNode("e2_integer_current", "h_2^2", Grade(6, 2))
    workspace.classes.extend([retired, current])
    assert _node_for(workspace, "h_2^2", 6, 2, 1001) is current
    assert retired.archived
    current.archived = True
    current.archived_reason = "Clear current canvas"
    assert _node_for(workspace, "h_2^2", 6, 2, 1001) is current
    assert current.archived and current.archived_reason == "Clear current canvas"

    stale_witt = ClassNode("e2_integer_old_witt", "D", Grade(8, 0), archived=True,
                          archived_reason=retired.archived_reason, style={"dkllw_glyph": "witt-j-series"})
    current_witt = ClassNode("e2_integer_current_witt", "D", Grade(8, 0),
                            style={"dkllw_glyph": "witt-j-series"})
    workspace.classes.extend([stale_witt, current_witt])
    assert _node_for(workspace, "4D", 8, 0, 1002).style["coefficient_parent_id"] == current_witt.id


def test_atlas_refresh_preserves_user_claims_on_retired_thom_motifs():
    project = migrate_project(demo_project())
    workspace = next(item for item in project.workspaces if item.id == "ws_q8-ro-a0-b1")
    node, original = attach_old_motif(workspace, "e2_thom_a0_b1_obsolete", "ThomIsomorphism + DKLLW24 E2 pattern")
    # A full migration derives new fates/events, so inspect the persisted
    # original claims independently of that derived cache.
    migrate_project(project)
    assert node.archived
    assert next(item for item in workspace.propositions if item.id == "source_e2_obsolete").status == "superseded"
    assert asdict(next(item for item in workspace.propositions if item.id == "user-relation")) == original[1]
    assert asdict(next(item for item in workspace.propositions if item.id == "user-claim")) == original[2]
    assert asdict(next(item for item in workspace.differentials if item.id == "user-differential")) == original[3]


CORE_DEMO_WORKSPACES = {
    "ws_integer", "ws_sigma_i", "ws_2sigma_i", "ws_3sigma_i", "ws_sigma_i_2sigma_j",
}


def original_seed_snapshots():
    """Independently read literal _node snapshots; do not copy the migration whitelist."""
    import ast

    tree = ast.parse((ROOT / "backend/domain/seed.py").read_text(encoding="utf-8"))
    names = {"integer": "ws_integer", "sigma": "ws_sigma_i", "two_sigma": "ws_2sigma_i",
             "three_sigma": "ws_3sigma_i", "mixed": "ws_sigma_i_2sigma_j"}
    records = {}
    for assignment in ast.walk(tree):
        if not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1:
            continue
        target = assignment.targets[0]
        if (not isinstance(target, ast.Attribute) or target.attr != "classes"
                or not isinstance(target.value, ast.Name) or target.value.id not in names):
            continue
        for call in assignment.value.elts:
            ident, label, stem, filtration = [ast.literal_eval(value) for value in call.args[:4]]
            representation = ast.literal_eval(call.args[4]) if len(call.args) > 4 else {}
            records[ident] = (names[target.value.id], {"id": ident, "label": label, "grade": {
                "stem": stem, "filtration": filtration, "representation": representation,
            }})
    return records


def demo_for_reconciliation():
    project = demo_project()
    # The helper runs after materialize_all_q8_thom_e2_patterns in the real
    # migration. Supply that routing metadata without rematerializing cells.
    for workspace in project.workspaces:
        if workspace.id in CORE_DEMO_WORKSPACES:
            workspace.settings["rendering"]["enumerated_e2_pattern"] = (
                "integer" if workspace.id in {"ws_integer", "ws_2sigma_i"} else "sigma_i"
            )
    return project


def test_every_original_core_demo_has_exact_snapshot_and_a_schema_disposition():
    project = demo_for_reconciliation()
    snapshots = original_seed_snapshots()
    assert len(snapshots) == 52
    _reconcile_original_demo_aliases(project)
    nodes = {node.id: node for workspace in project.workspaces for node in workspace.classes}
    retired = {
        "int_Dinvh1": [-7, 1], "sig_x3": [29, 3], "two_a2": [-2, 2],
        "two_xh1u": [0, 2], "two_kh1cubedu": [-1, 7],
        "mixed_h1": [2, 2], "two_d13target": None,
    }
    for ident, (_, snapshot) in snapshots.items():
        node = nodes[ident]
        metadata = node.style["original_demo_reconciliation"]
        assert metadata["original"] == snapshot
        assert metadata["source_ref"] == "backend/domain/seed.py:research_project"
        assert (node.label, asdict(node.grade)) == (snapshot["label"], snapshot["grade"])
        if ident in retired:
            assert node.archived
            assert "source-schema correction" in node.archived_reason
            assert "not a spectral-sequence death" in node.archived_reason
            assert metadata["mathematical_bidegree"] == retired[ident]
        else:
            assert metadata["action"] == "mapped-E2-alias"
            assert node.style.get("e2_pattern") or node.style.get("e2_components")
            assert node.style["two_valuation"] in {0, 1}
            assert node.style["j_order"] == 0
    assert nodes["two_D"].style["e2_pattern"] == "I00"
    assert nodes["two_k2h1sqD3"].style["e2_pattern"] == "I22H"
    assert nodes["two_k4xh1sqD4"].style["e2_pattern"] == "I13"
    assert nodes["two_2D"].style["two_valuation"] == 1
    assert nodes["three_sum_target"].style["e2_components"] == {"S22Y": 1, "S22H": 1}
    before = project_to_dict(project)
    _reconcile_original_demo_aliases(project)
    assert project_to_dict(project) == before


@pytest.mark.parametrize("ident", ["int_Dinvh1", "sig_x3", "two_a2", "three_combo", "mixed_h1"])
@pytest.mark.parametrize("edited_field", ["label", "stem", "filtration", "representation"])
def test_original_demo_reconciliation_never_overwrites_user_edited_identity(ident, edited_field):
    project = demo_for_reconciliation()
    node = next(node for workspace in project.workspaces for node in workspace.classes if node.id == ident)
    if edited_field == "label":
        node.label += r"\text{user revision}"
    elif edited_field == "representation":
        node.grade.representation = {"sigma_j": -7}
    else:
        setattr(node.grade, edited_field, getattr(node.grade, edited_field) + 1)
    before = asdict(node)
    _reconcile_original_demo_aliases(project)
    assert asdict(node) == before


def test_demo_retirement_keeps_all_claims_fates_and_nonwhitelisted_nodes():
    project = demo_for_reconciliation()
    workspace = next(item for item in project.workspaces if item.id == "ws_2sigma_i")
    node = next(item for item in workspace.classes if item.id == "two_a2")
    user_copy = deepcopy(node)
    user_copy.id = "two_a2_user_copy"
    workspace.classes.append(user_copy)
    user_claim = Proposition("user-demo-claim", "relation", "Keep my relation", status="candidate",
                             conclusion={"source_id": node.id, "target_id": user_copy.id}, rule="manual")
    user_diff = Differential("user-demo-arrow", node.id, user_copy.id, 5, status="under-review")
    workspace.propositions.append(user_claim)
    workspace.differentials.append(user_diff)
    workspace.fates.append(ClassFate(node.id, conclusion="unresolved"))
    before_claims = [(workspace.id, [asdict(p) for p in workspace.propositions],
                     [asdict(d) for d in workspace.differentials], [asdict(f) for f in workspace.fates])
                    for workspace in project.workspaces]
    before_user_copy = asdict(user_copy)
    original_state = node.state
    _reconcile_original_demo_aliases(project)
    assert node.archived and node.state == original_state
    assert asdict(user_copy) == before_user_copy
    assert [(workspace.id, [asdict(p) for p in workspace.propositions],
             [asdict(d) for d in workspace.differentials], [asdict(f) for f in workspace.fates])
            for workspace in project.workspaces] == before_claims


def test_full_migration_propagates_original_demo_dispositions_to_atlas_copies():
    project = migrate_project(demo_project())
    checked = set()
    for workspace in project.workspaces:
        for node in workspace.classes:
            record = node.style.get("original_demo_reconciliation")
            if not record:
                continue
            checked.add(workspace.id)
            if record["action"].startswith("retired"):
                assert node.archived
            elif not node.archived:
                assert node.style.get("e2_pattern") or node.style.get("e2_components")
    assert CORE_DEMO_WORKSPACES <= checked
    assert len(checked) == 16


def test_formal_endpoint_ports_distinguish_j_multiples_from_primitive_bo_families():
    workspace = Workspace("ws_2sigma_i", "two sigma", settings={"rendering": {"enumerated_e2_pattern": "integer"}})
    for label in (r"h_1v_1^6u_{2\sigma_i}", r"v_1^6h_1u_{2\sigma_i}"):
        style = _occurrence_style(workspace, label, 13, 1)
        assert style["e2_pattern"] == "I51"
        assert style["j_order"] == 1 and style["two_valuation"] == 0
    primitive = _occurrence_style(workspace, r"v_1^6u_{2\sigma_i}", 12, 0)
    assert primitive["e2_pattern"] == "I40" and primitive["j_order"] == 0
    witt_level = _occurrence_style(workspace, r"2Du_{2\sigma_i}", 8, 0)
    assert witt_level["e2_pattern"] == "I00" and witt_level["two_valuation"] == 1
