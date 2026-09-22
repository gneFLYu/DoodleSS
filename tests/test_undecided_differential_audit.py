import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.undecided_differential_audit import audit_undecided_differentials


def test_unresolved_inventory_is_structurally_complete_and_source_located():
    audit = audit_undecided_differentials()

    assert audit["valid"] is True
    assert audit["status"] == "underdetermined"
    assert audit["unresolved_fact_count"] == 5
    assert audit["errors"] == []

    obligations = {item["fact_id"]: item for item in audit["obligations"]}
    for fact_id in ("FN-3I-010", "FN-MIX-002", "FN-MIX-003", "FN-MIX-005"):
        item = obligations[fact_id]
        assert item["occurrences"]
        assert all(row["degree_valid"] for row in item["occurrences"])
        assert all(row["source_ref"] for row in item["occurrences"])
        assert item["missing_premises"]


def test_audit_exposes_status_divergence_without_promoting_the_fact():
    audit = audit_undecided_differentials()
    obligations = {item["fact_id"]: item for item in audit["obligations"]}

    mixed = obligations["FN-MIX-002"]
    assert mixed["ledger_status"] == "review"
    assert mixed["runtime_admission"] is None
    assert any("coefficient" in premise for premise in mixed["missing_premises"])
    assert any("FN-MIX-002" in warning for warning in audit["warnings"]) is False
    assert any("FN-3I-010 ledger status" in warning for warning in audit["warnings"])
