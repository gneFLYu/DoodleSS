"""A shared raw coefficient is resolved from current evidence, never a default.

The small fixtures deliberately separate a differential assertion from its
current row and endpoint records.  These tests do not add research results or
change the saved project.
"""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.fate import resolve_raw_coefficient_parameter
from domain.models import (
    CellBasisVector, CellVectorSpace, ClassNode, Differential, DifferentialMap,
    Grade, Project, Proposition, Workspace,
)


PARAMETER = "mixed_d5_A"
OWNER = "ws_sigma_i_2sigma_j"
PROOF = "coefficient_proof_mixed_d5_A"
EXTERNAL = "formal_prop_fn-3i-005_1"
BINDING = {"workspace_id": OWNER, "parameter_id": PARAMETER, "proposition_id": PROOF}
MIXED_IMAGES = {
    OWNER, "ws_q8-ro-a1-b3", "ws_q8-ro-a2-b1", "ws_q8-ro-a2-b3",
    "ws_q8-ro-a3-b1", "ws_q8-ro-a3-b2",
}


def parameter_claim(ident, *, offset=0, power=0):
    return Proposition(ident, "differential", "Abstract parameter consumer", status="review",
                       conclusion={"coefficient_parameter": {
                           "id": PARAMETER, "value": None, "domain": [1, 2, 3],
                           "affine_offset": offset, "frobenius_power": power,
                           "proof_binding": deepcopy(BINDING),
                       }})


def proof_fixture(*, with_matrix=False):
    leaf = Proposition("local-premise", "lemma", "Local naturality premise", status="verified",
                       conclusion={"admission_status": "verified"})
    external_leaf = Proposition("external-leaf", "lemma", "Source calculation premise", status="verified")
    source = ClassNode("source", "Source", Grade(18, 2))
    target = ClassNode("target", "Target", Grade(17, 7))
    spare = ClassNode("spare", "Distinct possible endpoint", Grade(17, 7))
    external = Proposition(EXTERNAL, "differential", "Source d5", status="verified",
                           premise_ids=[external_leaf.id], conclusion={
                               "source_id": source.id, "target_id": target.id, "page": 5,
                               "admission_status": "verified",
                           })
    row = Differential("source-d5", source.id, target.id, 5, status="verified",
                       proposition_id=external.id)
    foreign = Workspace("ws_3sigma_i", "Source calculation", classes=[source, target, spare],
                        propositions=[external, external_leaf], differentials=[row])
    proof = Proposition(PROOF, "coefficient-proof", "Current proof of the raw unit", status="verified",
                        premise_ids=[leaf.id, external.id], conclusion={
                            "parameter_id": PARAMETER, "coefficient_value": 3,
                            "admission_status": "verified", "external_premises": [{
                                "workspace_id": foreign.id, "proposition_id": external.id,
                            }],
                        })
    declarations = [parameter_claim("odd-a"), parameter_claim("odd-b"),
                    parameter_claim("even", offset=1)]
    owner = Workspace(OWNER, "Coefficient owner", propositions=[proof, leaf, *declarations])
    image = Workspace("ws_q8-ro-a2-b1", "Reflected consumer",
                      propositions=[parameter_claim("image-odd", power=1),
                                    parameter_claim("image-even", offset=1, power=1)])
    matrix = None
    if with_matrix:
        source.cell_id, source.coordinates = "source-cell", ["1"]
        target.cell_id, target.coordinates = "target-cell", ["1"]
        foreign.cells = [CellVectorSpace(ident, deepcopy(node.grade), page=5, status="verified",
                                         basis=[CellBasisVector("basis-" + ident, node.label)])
                         for ident, node in ((source.cell_id, source), (target.cell_id, target))]
        matrix = DifferentialMap("source-matrix", source.cell_id, target.cell_id, 5,
                                 matrix=[["1"]], status="verified", proposition_id=external.id)
        row.linear_map_id = matrix.id
        foreign.differential_maps = [matrix]
    project = Project("proof-fixture", "Coefficient proof tests", workspaces=[owner, foreign, image])
    return SimpleNamespace(project=project, owner=owner, image=image, proof=proof, leaf=leaf,
                           foreign=foreign, external=external, external_leaf=external_leaf,
                           row=row, source=source, target=target, spare=spare, matrix=matrix,
                           declarations=declarations)


def resolved(fixture, workspace=None, *, candidates=None):
    return resolve_raw_coefficient_parameter(workspace or fixture.owner, PARAMETER,
                                             project=fixture.project, candidates=candidates)


def assert_blocked(result):
    assert result["resolved"] is False, result
    assert result["proof_bound"] is True, result
    assert result["id"] == PARAMETER
    assert "value" not in result or result["value"] is None
    assert result.get("reason"), result


@pytest.mark.parametrize("with_matrix", [False, True])
def test_raw_unit_is_shared_before_affine_and_frobenius_and_reads_are_pure(with_matrix):
    fixture = proof_fixture(with_matrix=with_matrix)
    original = asdict(fixture.project)
    for workspace in (fixture.owner, fixture.image):
        assert resolved(fixture, workspace) == {
            "resolved": True, "proof_bound": True, "id": PARAMETER, "value": 3,
        }
    assert asdict(fixture.project) == original


@pytest.mark.parametrize("premises", [[], None])
@pytest.mark.parametrize("mutation", ["row-remove", "source-archive", "admission-review"])
def test_registered_empty_premises_cannot_bypass_strict_current_evidence(premises, mutation):
    from domain.fate import _cycle_premises_accepted

    fixture = proof_fixture()
    fixture.external.premise_ids = premises
    fixture.external.conclusion["coefficient_proof_registration"] = {
        "parameter_id": PARAMETER, "binding": deepcopy(BINDING),
    }
    assert _cycle_premises_accepted(fixture.foreign, fixture.external, fixture.project)
    if mutation == "row-remove":
        fixture.foreign.differentials.clear()
    elif mutation == "source-archive":
        fixture.source.archived = True
    else:
        fixture.external.conclusion["admission_status"] = "review"
    assert not _cycle_premises_accepted(fixture.foreign, fixture.external, fixture.project)


def linked_proof_fixture():
    fixture = proof_fixture()
    fixture.project.research_brief["coefficient_proof_registry"] = {PARAMETER: {"installed": True}}
    declaration = fixture.declarations[0]
    declaration.status = "verified"
    # The link reads the raw unit, before this source occurrence's affine image.
    declaration.conclusion["coefficient_parameter"]["affine_offset"] = 1
    declaration.conclusion["coefficient_parameter"]["frobenius_power"] = 1
    fixture.owner.differentials = [Differential("bound-source-row", "source", "target", 5,
        status="verified", proposition_id=declaration.id)]
    spec = {"id": PARAMETER, "value": None, "domain": [1, 2, 3], "source_parameter": {
        "workspace_id": OWNER, "parameter_id": PARAMETER,
        "differential_id": "bound-source-row", "page": 5,
    }}
    fixture.link = Workspace("linked-coefficient", "Linked coefficient", propositions=[
        Proposition("linked-consumer", "differential", "Linked consumer", status="verified",
                    conclusion={"coefficient_parameter": spec}),
    ])
    fixture.project.workspaces.append(fixture.link)
    return fixture


def test_registered_raw_unit_can_be_read_through_an_explicit_source_parameter():
    fixture = linked_proof_fixture()
    original = asdict(fixture.project)
    assert resolved(fixture, fixture.link)["value"] == 3
    assert asdict(fixture.project) == original
    fixture.external.status = "review"
    assert not resolved(fixture, fixture.link)["resolved"]
    assert not resolved(fixture, fixture.link, candidates={PARAMETER: 3})["resolved"]
    fixture.external.status = "verified"
    assert resolved(fixture, fixture.link)["value"] == 3
    fixture.link.settings["coefficient_assignments"] = {PARAMETER: 3}
    assert not resolved(fixture, fixture.link)["resolved"]


def test_directly_registered_consumer_cannot_replace_its_binding_with_a_source_link():
    fixture = linked_proof_fixture()
    fixture.link.propositions[0].conclusion["coefficient_proof_registration"] = {
        "parameter_id": PARAMETER, "binding": deepcopy(BINDING),
    }
    assert_blocked(resolved(fixture, fixture.link))


@pytest.mark.parametrize("scope", ["proof", "leaf", "external", "external_leaf"])
@pytest.mark.parametrize("status", ["review", "rejected", "superseded"])
@pytest.mark.parametrize("field", ["status", "admission_status"])
def test_all_recursive_premises_require_consistent_current_admission(scope, status, field):
    fixture = proof_fixture()
    record = getattr(fixture, scope)
    if field == "status":
        record.status = status
    else:
        record.conclusion[field] = status
    assert_blocked(resolved(fixture))
    assert_blocked(resolved(fixture, fixture.image))


BAD_EVIDENCE = (
    "root-tombstone", "root-remove", "root-duplicate", "root-empty-premises",
    "root-null-premises", "root-malformed-premises", "root-missing-premise",
    "root-wrong-kind", "root-wrong-parameter", "root-zero-value", "root-bool-value",
    "root-self-cycle", "root-local-cycle", "external-cycle", "leaf-tombstone",
    "leaf-remove", "leaf-duplicate", "external-remove", "external-duplicate",
    "external-tombstone", "external-locator-missing", "external-locator-invalid",
    "external-workspace-remove", "external-workspace-duplicate", "owner-workspace-duplicate",
    "row-remove", "row-duplicate-id", "row-second-same-proof", "row-source-edited",
    "row-target-edited", "row-page-edited", "row-review", "row-archived",
    "row-missing-matrix", "source-archived", "target-archived", "source-remove",
    "target-remove", "source-duplicate", "target-duplicate",
)


def break_evidence(fixture, case):
    f = fixture
    if case == "root-tombstone":
        f.proof.kind = "tombstone"
    elif case == "root-remove":
        f.owner.propositions.remove(f.proof)
    elif case == "root-duplicate":
        f.owner.propositions.append(deepcopy(f.proof))
    elif case == "root-empty-premises":
        f.proof.premise_ids = []
        f.proof.conclusion["external_premises"] = []
    elif case == "root-null-premises":
        f.proof.premise_ids = None
    elif case == "root-malformed-premises":
        f.proof.premise_ids = "local-premise"
    elif case == "root-missing-premise":
        f.proof.premise_ids.append("missing")
    elif case == "root-wrong-kind":
        f.proof.kind = "lemma"
    elif case == "root-wrong-parameter":
        f.proof.conclusion["parameter_id"] = "not-c"
    elif case == "root-zero-value":
        f.proof.conclusion["coefficient_value"] = 0
    elif case == "root-bool-value":
        f.proof.conclusion["coefficient_value"] = True
    elif case == "root-self-cycle":
        f.proof.premise_ids.append(f.proof.id)
    elif case == "root-local-cycle":
        f.leaf.premise_ids = [f.proof.id]
    elif case == "external-cycle":
        f.external_leaf.premise_ids = [f.external.id]
    elif case == "leaf-tombstone":
        f.leaf.kind = "tombstone"
    elif case == "leaf-remove":
        f.owner.propositions.remove(f.leaf)
    elif case == "leaf-duplicate":
        f.owner.propositions.append(deepcopy(f.leaf))
    elif case == "external-remove":
        f.foreign.propositions.remove(f.external)
    elif case == "external-duplicate":
        f.foreign.propositions.append(deepcopy(f.external))
    elif case == "external-tombstone":
        f.external.kind = "tombstone"
    elif case == "external-locator-missing":
        f.proof.conclusion["external_premises"] = []
    elif case == "external-locator-invalid":
        f.proof.conclusion["external_premises"][0]["workspace_id"] = "missing"
    elif case == "external-workspace-remove":
        f.project.workspaces.remove(f.foreign)
    elif case == "external-workspace-duplicate":
        f.project.workspaces.append(deepcopy(f.foreign))
    elif case == "owner-workspace-duplicate":
        f.project.workspaces.append(deepcopy(f.owner))
    elif case == "row-remove":
        f.foreign.differentials.clear()
    elif case == "row-duplicate-id":
        f.foreign.differentials.append(deepcopy(f.row))
    elif case == "row-second-same-proof":
        duplicate = deepcopy(f.row)
        duplicate.id = "another-row-with-same-proof"
        f.foreign.differentials.append(duplicate)
    elif case == "row-source-edited":
        f.row.source_id = f.spare.id
    elif case == "row-target-edited":
        f.row.target_id = f.spare.id
    elif case == "row-page-edited":
        f.row.page = 7
    elif case == "row-review":
        f.row.status = "review"
    elif case == "row-archived":
        f.row.archived = True
    elif case == "row-missing-matrix":
        f.row.linear_map_id = "unavailable-matrix"
    elif case.endswith("-archived"):
        getattr(f, case.split("-")[0]).archived = True
    elif case.endswith("-remove"):
        f.foreign.classes.remove(getattr(f, case.split("-")[0]))
    elif case.endswith("-duplicate"):
        f.foreign.classes.append(deepcopy(getattr(f, case.split("-")[0])))
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", BAD_EVIDENCE)
@pytest.mark.parametrize("fallback", ["none", "raw", "setting", "candidate"])
def test_withdrawn_evidence_cannot_be_bypassed_by_a_stored_or_candidate_three(case, fallback):
    fixture = proof_fixture()
    break_evidence(fixture, case)
    candidates = None
    if fallback == "raw":
        for claim in fixture.declarations:
            claim.conclusion["coefficient_parameter"]["value"] = 3
    elif fallback == "setting":
        fixture.owner.settings["coefficient_assignments"] = {PARAMETER: 3}
    elif fallback == "candidate":
        candidates = {PARAMETER: 3}
    before = asdict(fixture.project)
    assert_blocked(resolved(fixture, candidates=candidates))
    assert_blocked(resolved(fixture, fixture.image, candidates=candidates))
    assert asdict(fixture.project) == before


@pytest.mark.parametrize("case", [
    "review", "archived", "missing", "duplicate", "wrong-page",
    "wrong-source", "wrong-target", "wrong-proof",
])
def test_matrix_is_part_of_the_exact_source_differential_evidence(case):
    fixture = proof_fixture(with_matrix=True)
    assert resolved(fixture)["resolved"]
    if case == "review":
        fixture.matrix.status = "review"
    elif case == "archived":
        fixture.matrix.archived = True
    elif case == "missing":
        fixture.foreign.differential_maps.clear()
    elif case == "duplicate":
        fixture.foreign.differential_maps.append(deepcopy(fixture.matrix))
    elif case == "wrong-page":
        fixture.matrix.page = 7
    elif case == "wrong-source":
        fixture.matrix.source_cell_id = "missing-source-cell"
    elif case == "wrong-target":
        fixture.matrix.target_cell_id = "missing-target-cell"
    elif case == "wrong-proof":
        fixture.matrix.proposition_id = "different-proof"
    assert_blocked(resolved(fixture))


@pytest.mark.parametrize("duplicate_id", [False, True])
@pytest.mark.parametrize("defect", ["missing", "wrong-proof", "wrong-owner", "wrong-parameter", "raw"])
def test_every_same_id_declaration_is_checked_even_duplicate_claim_ids(duplicate_id, defect):
    fixture = proof_fixture()
    claim = parameter_claim(fixture.declarations[0].id if duplicate_id else "additional-declaration")
    spec = claim.conclusion["coefficient_parameter"]
    if defect == "missing":
        spec.pop("proof_binding")
    elif defect == "raw":
        spec["value"] = 2
    else:
        key = {"wrong-proof": "proposition_id", "wrong-owner": "workspace_id",
               "wrong-parameter": "parameter_id"}[defect]
        spec["proof_binding"][key] = "mismatched"
    fixture.owner.propositions.append(claim)
    assert_blocked(resolved(fixture))
    assert_blocked(resolved(fixture, fixture.image))


@pytest.mark.parametrize("scope", ["owner", "image"])
@pytest.mark.parametrize("assignment, accepted", [(3, True), ("zeta^2", True), (2, False), (True, False)])
def test_user_assignment_is_preserved_and_checked_against_the_live_proof(scope, assignment, accepted):
    fixture = proof_fixture()
    owner = getattr(fixture, scope)
    owner.settings["coefficient_assignments"] = {PARAMETER: assignment, "unrelated": 2}
    before = deepcopy(owner.settings)
    result = resolved(fixture, fixture.image)
    assert result["resolved"] is accepted, result
    if accepted:
        assert result["value"] == 3
    else:
        assert_blocked(result)
    assert owner.settings == before


@pytest.mark.parametrize("candidate, accepted", [(3, True), (2, False), (True, False)])
def test_candidate_is_a_consistency_check_not_an_alternative_proof(candidate, accepted):
    fixture = proof_fixture()
    result = resolved(fixture, candidates={PARAMETER: candidate})
    assert result["resolved"] is accepted
    if accepted:
        assert result["value"] == 3
    else:
        assert_blocked(result)


@pytest.mark.parametrize("value, accepted", [(3, True), (2, False), (0, False), (True, False)])
def test_raw_value_is_only_a_consistency_check_against_a_valid_proof(value, accepted):
    fixture = proof_fixture()
    fixture.declarations[0].conclusion["coefficient_parameter"]["value"] = value
    result = resolved(fixture)
    assert result["resolved"] is accepted
    if accepted:
        assert result["value"] == 3 and result["proof_bound"] is True
    else:
        assert_blocked(result)


def test_cross_workspace_proof_requires_the_live_project():
    fixture = proof_fixture()
    assert_blocked(resolve_raw_coefficient_parameter(fixture.image, PARAMETER))
    assert_blocked(resolve_raw_coefficient_parameter(fixture.owner, PARAMETER))


@pytest.mark.parametrize("scope", ["owner", "image"])
@pytest.mark.parametrize("extent", ["one", "all"])
@pytest.mark.parametrize("defect", ["binding", "spec", "id"])
def test_registered_consumers_cannot_be_unbound_by_removing_their_parameter_metadata(scope, extent, defect):
    fixture = proof_fixture()
    for workspace in (fixture.owner, fixture.image):
        for claim in workspace.propositions:
            if "coefficient_parameter" in claim.conclusion:
                claim.conclusion["coefficient_proof_registration"] = {
                    "parameter_id": PARAMETER, "binding": deepcopy(BINDING),
                }
    owner = getattr(fixture, scope)
    claims = [p for p in owner.propositions if "coefficient_parameter" in p.conclusion]
    for claim in claims[:1] if extent == "one" else claims:
        if defect == "binding":
            claim.conclusion["coefficient_parameter"].pop("proof_binding")
        elif defect == "spec":
            claim.conclusion.pop("coefficient_parameter")
        else:
            claim.conclusion["coefficient_parameter"]["id"] = "different-parameter"
    owner.settings["coefficient_assignments"] = {PARAMETER: 3}
    assert_blocked(resolved(fixture, owner, candidates={PARAMETER: 3}))
    if scope == "owner":
        assert_blocked(resolved(fixture, fixture.image, candidates={PARAMETER: 3}))


@pytest.fixture(scope="module")
def canonical_project():
    from domain.migrations import migrate_project
    from domain.seed import demo_project
    return migrate_project(demo_project())


def test_canonical_six_mixed_atlas_images_resolve_one_proof_not_saved_values(canonical_project):
    project = canonical_project
    seen = set()
    for workspace in project.workspaces:
        if workspace.id not in MIXED_IMAGES:
            continue
        specs = [p.conclusion.get("coefficient_parameter") for p in workspace.propositions]
        specs = [s for s in specs if isinstance(s, dict) and s.get("id") == PARAMETER]
        assert specs, workspace.id
        assert all(s.get("value") is None and s.get("proof_binding") == BINDING for s in specs), workspace.id
        assert resolve_raw_coefficient_parameter(workspace, PARAMETER, project=project) == {
            "resolved": True, "proof_bound": True, "id": PARAMETER, "value": 3,
        }, workspace.id
        seen.add(workspace.id)
    assert seen == MIXED_IMAGES


@pytest.mark.parametrize("withdrawal", ["review", "remove"])
def test_migration_does_not_reinstate_a_withdrawn_coefficient_root(canonical_project, withdrawal):
    from domain.migrations import migrate_project
    project = deepcopy(canonical_project)
    owner = next(w for w in project.workspaces if w.id == OWNER)
    proof = next(p for p in owner.propositions if p.id == PROOF)
    if withdrawal == "remove":
        owner.propositions.remove(proof)
    else:
        proof.status = "review"
    owner.settings["coefficient_assignments"] = {PARAMETER: 3, "unrelated": 2}
    migrate_project(project)
    owner = next(w for w in project.workspaces if w.id == OWNER)
    proofs = [p for p in owner.propositions if p.id == PROOF]
    if withdrawal == "remove":
        assert not proofs
    else:
        assert len(proofs) == 1 and proofs[0].status == "review"
    assert owner.settings["coefficient_assignments"] == {PARAMETER: 3, "unrelated": 2}
    for workspace in project.workspaces:
        if workspace.id in MIXED_IMAGES:
            assert_blocked(resolve_raw_coefficient_parameter(workspace, PARAMETER, project=project))


@pytest.mark.parametrize("withdrawal", ["claim-review", "claim-remove", "row-remove", "endpoint-archived"])
def test_migration_preserves_withdrawn_source_differential_evidence(canonical_project, withdrawal):
    from domain.migrations import migrate_project
    project = deepcopy(canonical_project)
    source = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    proof = next(p for p in source.propositions if p.id == EXTERNAL)
    row = next(d for d in source.differentials if d.proposition_id == EXTERNAL)
    row_id, target_id = row.id, row.target_id
    if withdrawal == "claim-review":
        proof.status = "review"
    elif withdrawal == "claim-remove":
        source.propositions.remove(proof)
    elif withdrawal == "row-remove":
        source.differentials.remove(row)
    else:
        next(c for c in source.classes if c.id == target_id).archived = True
    migrate_project(project)
    source = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    if withdrawal == "claim-review":
        assert next(p for p in source.propositions if p.id == EXTERNAL).status == "review"
    elif withdrawal == "claim-remove":
        assert not any(p.id == EXTERNAL for p in source.propositions)
    elif withdrawal == "row-remove":
        assert not any(d.id == row_id for d in source.differentials)
    else:
        assert next(c for c in source.classes if c.id == target_id).archived is True
    for workspace in project.workspaces:
        if workspace.id in MIXED_IMAGES:
            assert_blocked(resolve_raw_coefficient_parameter(workspace, PARAMETER, project=project,
                                                            candidates={PARAMETER: 3}))


@pytest.mark.parametrize("withdrawal", ["remove-spec", "change-id"])
def test_migration_does_not_repair_a_registered_consumer_that_was_unbound(canonical_project, withdrawal):
    from domain.migrations import migrate_project
    project = deepcopy(canonical_project)
    owner = next(w for w in project.workspaces if w.id == OWNER)
    claim = next(p for p in owner.propositions if p.id == "formal_prop_fn-mix-002_1")
    if withdrawal == "remove-spec":
        claim.conclusion.pop("coefficient_parameter")
    else:
        claim.conclusion["coefficient_parameter"]["id"] = "different-parameter"
    owner.settings["coefficient_assignments"] = {PARAMETER: 3}
    assert_blocked(resolve_raw_coefficient_parameter(owner, PARAMETER, project=project))
    migrate_project(project)
    owner = next(w for w in project.workspaces if w.id == OWNER)
    claim = next(p for p in owner.propositions if p.id == "formal_prop_fn-mix-002_1")
    if withdrawal == "remove-spec":
        assert "coefficient_parameter" not in claim.conclusion
    else:
        assert claim.conclusion["coefficient_parameter"]["id"] == "different-parameter"
    assert owner.settings["coefficient_assignments"] == {PARAMETER: 3}
    for workspace in project.workspaces:
        if workspace.id in MIXED_IMAGES:
            assert_blocked(resolve_raw_coefficient_parameter(workspace, PARAMETER, project=project,
                                                            candidates={PARAMETER: 3}))
