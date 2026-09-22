"""Unknown F4 units keep one identity and assignment throughout the atlas."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.atlas_transport import _transport_coefficient_parameter, ensure_q8_atlas_transports
from domain.migrations import migrate_project
from domain.models import Proposition
from domain.seed import demo_project


@pytest.mark.parametrize("value", [None, 1, 2, 3, "zeta", "zeta^2"])
@pytest.mark.parametrize("power", [0, 1])
def test_frobenius_preserves_parameter_identity_assignment_and_is_an_involution(value, power):
    parameter = {"id": "formal:alpha", "symbol": "alpha", "domain": [1, 2, 3],
                 "value": value, "frobenius_power": power}
    original = deepcopy(parameter)
    image = _transport_coefficient_parameter(parameter, True)
    assert image == {**original, "frobenius_power": 1 - power}
    assert _transport_coefficient_parameter(image, True) == original
    assert _transport_coefficient_parameter(parameter, False) == original
    assert parameter == original
    image["domain"].append(0)
    assert parameter["domain"] == [1, 2, 3]


@pytest.mark.parametrize("power", [-1, 2, "1", None, True])
@pytest.mark.parametrize("reflected", [False, True])
def test_frobenius_does_not_silently_normalize_an_invalid_power(power, reflected):
    with pytest.raises(ValueError, match="frobenius_power"):
        _transport_coefficient_parameter({"id": "alpha", "frobenius_power": power}, reflected)


def test_missing_frobenius_power_is_not_assumed_to_be_zero():
    with pytest.raises(ValueError, match="frobenius_power"):
        _transport_coefficient_parameter({"id": "alpha"}, True)


@pytest.fixture(scope="module")
def parameterized_project():
    project = migrate_project(demo_project())
    source_ids = ("ws_3sigma_i", "ws_sigma_i_2sigma_j")
    for workspace in project.workspaces:
        if workspace.id not in source_ids:
            continue
        # Deliberate collision: global parameter ids must not be rewritten
        # by the generic chart-reference remapper.
        parameter_id = workspace.classes[0].id
        workspace.settings["coefficient_assignments"] = {parameter_id: "zeta"}
        for suffix, value in (("a", None), ("b", "zeta")):
            workspace.propositions.append(Proposition(
                id=f"parameter-test-{suffix}", kind="differential", statement="parameter audit", status="review",
                conclusion={
                    "source_id": workspace.classes[0].id,
                    "coefficient_parameter": {
                        "id": parameter_id, "symbol": "alpha", "domain": [1, 2, 3],
                        "value": value, "frobenius_power": 0, "inverse_parameter_id": parameter_id,
                    },
                    "coefficient_condition": {"parameter_id": parameter_id, "equals": 2,
                                              "otherwise": "zero-euler-image"},
                    "two_valuation": 2, "j_order": 1, "unrelated_scalar": "zeta",
                },
            ))
    ensure_q8_atlas_transports(project)
    return project


def test_real_three_sigma_and_mixed_atlas_paths_preserve_shared_parameter_ids(parameterized_project):
    project = parameterized_project
    sources = {workspace.id: workspace for workspace in project.workspaces}
    seen = set()
    for target in project.workspaces:
        plan = target.settings.get("atlas_transport", {})
        source_id = plan.get("source_workspace_id")
        if source_id not in {"ws_3sigma_i", "ws_sigma_i_2sigma_j"}:
            continue
        source = sources[source_id]
        prefix = f"atlas_{plan['sector_id']}_"
        seen.add((source_id, plan["reflected"]))
        parameters = []
        for suffix in ("a", "b"):
            original = next(p for p in source.propositions if p.id == f"parameter-test-{suffix}")
            image = next(p for p in target.propositions if p.id == prefix + original.id)
            expected = {**original.conclusion["coefficient_parameter"],
                        "frobenius_power": int(plan["reflected"])}
            assert image.conclusion["coefficient_parameter"] == expected
            assert image.conclusion["coefficient_condition"] == original.conclusion["coefficient_condition"]
            assert image.conclusion["coefficient_condition"] is not original.conclusion["coefficient_condition"]
            assert image.conclusion["source_id"] == prefix + original.conclusion["source_id"]
            assert image.status == original.status == "review"
            for field in ("two_valuation", "j_order", "unrelated_scalar"):
                assert image.conclusion[field] == original.conclusion[field]
            parameters.append(image.conclusion["coefficient_parameter"]["id"])
        assert parameters[0] == parameters[1]
        assert target.settings["coefficient_assignments"] == source.settings["coefficient_assignments"]
        assert target.settings["coefficient_assignments"] is not source.settings["coefficient_assignments"]
    assert seen == {("ws_3sigma_i", False), ("ws_sigma_i_2sigma_j", False),
                    ("ws_sigma_i_2sigma_j", True)}


def test_refresh_propagates_source_assignment_changes_and_removal(parameterized_project):
    project = deepcopy(parameterized_project)
    source = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    target = next(w for w in project.workspaces if w.id == "ws_q8-ro-a2-b1")
    parameter_id = next(iter(source.settings["coefficient_assignments"]))
    source.settings["coefficient_assignments"][parameter_id] = "zeta^2"
    ensure_q8_atlas_transports(project)
    assert target.settings["coefficient_assignments"] == {parameter_id: "zeta^2"}
    image = next(p for p in target.propositions if p.id.endswith("parameter-test-a"))
    assert image.conclusion["coefficient_parameter"]["id"] == parameter_id
    assert image.conclusion["coefficient_parameter"]["frobenius_power"] == 1
    del source.settings["coefficient_assignments"]
    ensure_q8_atlas_transports(project)
    assert "coefficient_assignments" not in target.settings


@pytest.mark.parametrize("power", [None, 2, "1"])
def test_invalid_imported_parameter_is_retained_without_blocking_atlas_refresh(parameterized_project, power):
    project = deepcopy(parameterized_project)
    source = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    claim = next(p for p in source.propositions if p.id == "parameter-test-a")
    claim.conclusion["coefficient_parameter"]["frobenius_power"] = power
    original = deepcopy(claim.conclusion["coefficient_parameter"])
    ensure_q8_atlas_transports(project)
    affected = []
    for target in project.workspaces:
        plan = target.settings.get("atlas_transport", {})
        if plan.get("source_workspace_id") != source.id:
            continue
        prefix = f"atlas_{plan['sector_id']}_"
        image = next(p for p in target.propositions if p.id == prefix + claim.id)
        assert image.conclusion["coefficient_parameter"] == original
        assert "frobenius_power" in image.conclusion["coefficient_transport_error"]
        assert image.status == "review"
        # Other source records still refresh, including valid parameters.
        valid = next(p for p in target.propositions if p.id == prefix + "parameter-test-b")
        assert "coefficient_transport_error" not in valid.conclusion
        assert valid.conclusion["coefficient_parameter"]["frobenius_power"] == int(plan["reflected"])
        affected.append((target, prefix, plan["reflected"]))
    assert len(affected) == 5
    assert claim.conclusion["coefficient_parameter"] == original
    assert "coefficient_transport_error" not in claim.conclusion

    # Fixing the source must remove the old image error on the next refresh.
    claim.conclusion["coefficient_parameter"]["frobenius_power"] = 0
    ensure_q8_atlas_transports(project)
    for target, prefix, reflected in affected:
        image = next(p for p in target.propositions if p.id == prefix + claim.id)
        assert "coefficient_transport_error" not in image.conclusion
        assert image.conclusion["coefficient_parameter"]["frobenius_power"] == int(reflected)
