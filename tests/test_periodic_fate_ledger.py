import re
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import app
from domain.periodic_fate_ledger import (
    audit_periodic_fate_ledger,
    hfpss_d8_period_class_id,
    hfpss_g_d8_semiperiod_class_id,
    load_periodic_fate_ledger,
    tate_g_d8_period_class_id,
)


def test_d8_ids_merge_only_genuine_64_translates():
    anchor = hfpss_d8_period_class_id(
        "2i", "h1sq", k_power=2, d_power=3
    )
    assert anchor == hfpss_d8_period_class_id(
        "2i", "h1sq", k_power=2, d_power=11
    )
    assert anchor != hfpss_d8_period_class_id(
        "2i", "h1sq", k_power=2, d_power=7
    )
    assert anchor != hfpss_d8_period_class_id(
        "mix-i2j", "h1sq", k_power=2, d_power=3
    )


def test_guarded_tate_ids_use_the_g_equals_kd3_lattice_invariant():
    assert tate_g_d8_period_class_id(
        "2i", "h1sq", k_power=2, d_power=3
    ) == tate_g_d8_period_class_id(
        "2i", "h1sq", k_power=6, d_power=7
    )
    assert tate_g_d8_period_class_id(
        "2i", "h1sq", k_power=2, d_power=3
    ).endswith("-r5")


def test_hfpss_semiperiod_id_includes_bo_without_inverting_g():
    assert hfpss_g_d8_semiperiod_class_id(
        "integer", "bo-h1-tower", k_power=0, d_power=0
    ) == hfpss_g_d8_semiperiod_class_id(
        "integer", "bo-h1-tower", k_power=4, d_power=12
    )
    assert ".gd8semi." in hfpss_g_d8_semiperiod_class_id(
        "integer", "bo-h1-tower"
    )

    data = load_periodic_fate_ledger()
    semiperiod = next(
        item
        for item in data["period_mechanisms"]
        if item["id"] == "semi.hfpss.g-d8"
    )
    assert semiperiod["exponent_domains"] == {
        "g": "integer >= 0",
        "D^8": "integer",
    }
    assert "including j-adic bo-pattern towers" in semiperiod["scope"]


def test_ledger_indexes_every_active_sector_fact_and_preserves_matrix_port():
    data = load_periodic_fate_ledger()
    facts = {item["id"]: item for item in data["fact_families"]}

    expected = {
        *(f"FN-2I-{index:03d}" for index in range(1, 22)),
        *(f"FN-3I-{index:03d}" for index in range(1, 11)),
        *(f"FN-MIX-{index:03d}" for index in range(1, 7)),
    }
    assert set(facts) == expected

    matrix_fact = facts["FN-3I-006"]
    assert matrix_fact["matrix"] == [["1"], ["1"]]
    assert matrix_fact["projective_port"] == ["1", "1"]
    assert matrix_fact["target_period_class_ids"] == [
        "pc.3i.d8.target-cell-line11-cone-k1-d1"
    ]

    record_ids = set(
        re.findall(
            r"FN-(?:2I|3I|MIX)-\d{3}",
            (ROOT / "RECORD.md").read_text(encoding="utf-8"),
        )
    )
    assert expected.issubset(record_ids)


def test_pattern_periods_are_not_same_object_periods():
    data = load_periodic_fate_ledger()
    mechanisms = {item["id"]: item for item in data["period_mechanisms"]}

    assert mechanisms["per.hfpss.d8"]["semantic"] == "same-object"
    assert mechanisms["semi.hfpss.g-d8"]["semantic"] == "period-family"
    assert mechanisms["per.tate.g-d8"]["semantic"] == "comparison-identity"
    assert mechanisms["pat.e3.d"]["semantic"] == "pattern-only"
    assert mechanisms["pat.e5.d2"]["semantic"] == "pattern-only"
    assert mechanisms["pat.d4"]["semantic"] == "pattern-only"

    for fact in data["fact_families"]:
        assert fact["same_object_period_id"] == "per.hfpss.d8"
        assert "pat.d4" != fact["same_object_period_id"]
    assert data["fact_family_period_defaults"]["semiperiod_family_id"] == (
        "semi.hfpss.g-d8"
    )


def test_module_kinds_separate_j_adic_towers_from_finite_cells():
    data = load_periodic_fate_ledger()
    kinds = {item["id"]: item for item in data["module_kinds"]}

    assert set(kinds) == {
        "finite-2-primary",
        "witt-2-adic",
        "j-adic-formal-power-series",
    }
    assert kinds["j-adic-formal-power-series"]["parameter"] == "j=v1^4D^-1"
    assert "not inferred from filtration" in data["module_assignment_policy"][
        "forbidden_inference"
    ]


def test_vanishing_audit_reports_covered_rank_and_exact_open_obligations():
    audit = audit_periodic_fate_ledger(load_periodic_fate_ledger())
    obligations = {item["id"]: item for item in audit["obligations"]}

    assert audit["valid"] is True
    assert audit["status"] == "underdetermined"
    assert audit["fact_family_count"] == 37
    assert audit["period_mechanism_count"] == 6
    assert audit["module_kind_count"] == 3
    assert audit["formal_series_family_count"] == 2
    assert audit["obligation_count"] == 5
    assert audit["finite_rank_obligation_count"] == 5
    assert audit["formal_series_obligation_count"] == 0
    assert audit["covered_obligation_count"] == 1

    assert obligations["obl-2i-f26-d9-target"]["covered"] is True
    assert obligations["obl-2i-f26-d9-target"]["covered_rank"] == 1
    assert obligations["obl-2i-f26-d21-target"]["covered"] is False
    assert any(
        "FN-2I-019 has non-certifying status review" in reason
        for reason in obligations["obl-2i-f26-d21-target"]["unresolved_reasons"]
    )
    assert obligations["obl-3i-rank2-target-cell"]["covered_rank"] == 0
    assert obligations["obl-3i-rank2-target-cell"]["required_killed_rank"] == 2


def test_vanishing_rank_is_the_span_rank_not_the_number_of_arrows():
    data = deepcopy(load_periodic_fate_ledger())
    facts = {item["id"]: item for item in data["fact_families"]}
    facts["FN-3I-006"]["status"] = "admitted"
    obligation = next(
        item
        for item in data["vanishing_audit"]["obligations"]
        if item["id"] == "obl-3i-rank2-target-cell"
    )
    obligation["unresolved_reasons"] = []
    obligation["resolutions"].append(
        {
            "fact_id": "FN-3I-006",
            "role": "receives",
            "killed_rank": 1,
            "killed_vectors": [["1", "1"]],
        }
    )

    result = audit_periodic_fate_ledger(data)
    audited = next(
        item
        for item in result["obligations"]
        if item["id"] == "obl-3i-rank2-target-cell"
    )
    assert audited["covered_rank"] == 1
    assert audited["covered"] is False


def test_j_adic_tower_uses_a_fixed_family_not_finite_rank():
    data = deepcopy(load_periodic_fate_ledger())
    data["formal_series_families"].append(
        {
            "id": "fs.test.fixed-killed-family",
            "status": "admitted-pattern",
            "vanishing_outcome": "killed",
            "fixed_differential_templates": ["d3(j^n a)=j^n b"],
        }
    )
    data["vanishing_audit"]["obligations"] = [
        {
            "id": "obl-bo-j-adic",
            "kind": "cell-subspace",
            "module_kind": "j-adic-formal-power-series",
            "period_class_id": "pc.integer.gd8semi.bo-h1-c1-r0",
            "fixed_differential_family_id": "fs.test.fixed-killed-family",
            "cell_dimension": 1,
            "required_killed_rank": 1,
            "resolutions": [
                {
                    "fact_id": "FN-2I-003",
                    "role": "receives",
                    "killed_vectors": [["1"]],
                }
            ],
            "unresolved_reasons": [],
        }
    ]

    audit = audit_periodic_fate_ledger(data)
    obligation = audit["obligations"][0]
    assert obligation["audit_mode"] == "fixed-differential-family"
    assert obligation["covered_rank"] is None
    assert obligation["cell_dimension"] is None
    assert obligation["covered"] is True
    assert obligation["unresolved_reasons"] == []
    assert audit["finite_rank_obligation_count"] == 0
    assert audit["formal_series_obligation_count"] == 1


def test_j_adic_finite_vector_is_ignored_without_a_fixed_family():
    data = deepcopy(load_periodic_fate_ledger())
    data["vanishing_audit"]["obligations"] = [
        {
            "id": "obl-bo-missing-family",
            "kind": "cell-subspace",
            "module_kind": "j-adic-formal-power-series",
            "period_class_id": "pc.integer.gd8semi.bo-h1-c1-r0",
            "cell_dimension": 1,
            "required_killed_rank": 1,
            "resolutions": [
                {
                    "fact_id": "FN-2I-003",
                    "role": "receives",
                    "killed_vectors": [["1"]],
                }
            ],
            "unresolved_reasons": [],
        }
    ]

    obligation = audit_periodic_fate_ledger(data)["obligations"][0]
    assert obligation["covered"] is False
    assert obligation["covered_rank"] is None
    assert any(
        "fixed_differential_family_id" in reason
        for reason in obligation["unresolved_reasons"]
    )


def test_review_endpoint_is_read_only_and_returns_computed_audit():
    client = app.test_client()
    response = client.get("/api/v2/review/periodic-fate-ledger")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ledger"]["canonical"] is False
    assert payload["audit"]["status"] == "underdetermined"
    assert payload["audit"]["fact_family_count"] == 37
    assert payload["audit"]["formal_series_family_count"] == 2
