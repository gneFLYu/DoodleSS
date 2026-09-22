"""Conditional full-page verification, distinct from source admission.

These tests explicitly assume the active two-sigma claims, except the
documented missing-j transcription FN-2I-002. They never promote persisted
review claims. The conclusion is bounded runtime consistency, not a new proof
of the draft's open C4 comparisons or coefficient choices.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.seed import demo_project


@pytest.fixture(scope="module")
def two_sigma_hypothesis():
    original = migrate_project(demo_project())
    project = deepcopy(original)
    ws = next(w for w in project.workspaces if w.id == "ws_2sigma_i")
    for arrow in ws.differentials:
        if arrow.label.startswith("FN-") and arrow.label != "FN-2I-002":
            arrow.status = "admitted"
    for claim in ws.propositions:
        if claim.conclusion.get("fact_id", "").startswith("FN-") and claim.conclusion.get("fact_id") != "FN-2I-002":
            claim.status = "admitted"
    payload = {"project": asdict(project), "workspaces": [ws.id],
               "pages": [3,4,5,6,7,8,9,10,11,12,13,14,21,22,24],
               "bounds": {"stemMin": -64, "stemMax": 127, "filtrationMin": 0, "filtrationMax": 100},
               "vectorAudit": True, "auditNoClipping": True,
               "probes": [{"pattern":p,"stem":s,"filtration":f} for p,s,f in (
                   ("I00",60,4), ("I00",16,8), ("I31",59,25), ("I31",15,29))]}
    result = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT,
                            input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", check=True)
    return original, json.loads(result.stdout)[0]["pages"]


def test_default_formal_period_is_explicit_and_euler_square_is_not_overtranslated():
    ws = next(w for w in migrate_project(demo_project()).workspaces if w.id == "ws_2sigma_i")
    claims = {p.id:p for p in ws.propositions}
    for arrow in ws.differentials:
        if arrow.label.startswith("FN-"):
            assert arrow.period_stem == claims[arrow.proposition_id].conclusion["period_stem"]
    assert next(d for d in ws.differentials if d.id == "diff_two_d13").period_stem == 64


def test_conditional_quotients_have_no_unknown_directions_or_square_conflicts(two_sigma_hypothesis):
    _, pages = two_sigma_hypothesis
    assert not [(row["page"], c) for row in pages for c in row["conflicts"]]
    assert not [(row["page"], b) for row in pages for b in row["blocks"] if b["barriers"]]
    e21 = next(row for row in pages if row["page"] == 21)
    assert "formal_diff_fn-2i-019_1" in e21["rows"]
    assert "formal_diff_two_d21_tate_positive_derived" in e21["rows"]


def test_positive_filtration_comparison_ports_and_vanishing_without_clipping(two_sigma_hypothesis):
    _, pages = two_sigma_hypothesis
    e21 = next(row for row in pages if row["page"] == 21)
    for probe in e21["probes"]:
        assert probe["ports"] == (["2:0"] if probe["pattern"] == "I00" else ["0:0"])
    assert e21["high"] > 0
    for page in (22,24):
        row = next(row for row in pages if row["page"] == page)
        assert row["high"] == 0, row["highPatterns"]
        assert row["unmappedHigh"] > 0  # No imposed vanishing-line clipping.
        assert all(not p["ports"] for p in row["probes"])


def test_research_hypothesis_preserves_independent_original_d21_certificates(two_sigma_hypothesis):
    original, _ = two_sigma_hypothesis
    ws = next(w for w in original.workspaces if w.id == "ws_2sigma_i")
    derived = next(d for d in ws.differentials if d.id == "formal_diff_two_d21_tate_positive_derived")
    parent = next(d for d in ws.differentials if d.label == "FN-2I-021" and d.id != derived.id)
    assert derived.status == parent.status == "verified"
    claim = next(p for p in ws.propositions if p.id == derived.proposition_id)
    assert claim.status == "verified"
    certificate = claim.conclusion["verification_certificate"]
    assert certificate["status"] == "verified"
    assert certificate["method"] == "Published d23 product and finite E21 quotient"
    assert certificate["table_comparison"]["table_period_stem"] == 64
    assert claim.conclusion["comparison_source_filtration"] == 4
    assert claim.conclusion["comparison_target_filtration"] == 25
    assert claim.conclusion["comparison_translation"]["spectral_sequence"] == "tate"
    assert claim.conclusion["evidence_kind"] == "Tate-comparison-derived"
