"""Scoped migration contract for three superseded REU pattern summaries.

These summaries must reference the canonical proofs, not independently admit
arrows or infer mixed-sector units from the selected pure-sigma normalization.
"""

from copy import deepcopy
from dataclasses import asdict

import pytest

from backend.domain.migrations import migrate_project
from backend.domain.models import Proposition, project_from_dict
from backend.domain.reu_fact_chain import ensure_reu_fact_chain
from backend.domain.seed import demo_project


PATTERNS = {
    "prop_reu_d11_corrected_pattern": {
        "page": 11,
        "period": 32,
        "canonical": {"formal_prop_fn-2i-009_1"},
        "old_premises": ["prop_reu_a2sigma_pc", "prop_chain_q8_d11"],
        "forbidden": set(),
    },
    "prop_reu_d9_corrected_pattern": {
        "page": 9,
        "period": 32,
        "canonical": {"formal_prop_fn-2i-016_1"},
        "old_premises": ["prop_reu_d11_corrected_pattern", "prop_chain_q8_d23"],
        "forbidden": {"prop_chain_q8_d23"},
    },
    "prop_reu_d7_corrected_pattern": {
        "page": 7,
        "period": 16,
        "canonical": {"formal_prop_fn-2i-014_1", "formal_prop_fn-2i-012_1"},
        "old_premises": ["prop_reu_d5_a2sigma", "prop_chain_c4_hidden_2"],
        "forbidden": {"prop_chain_c4_hidden_2"},
    },
}


def propositions(project):
    return {p.id: p for workspace in project.workspaces for p in workspace.propositions}


def assert_current_pattern(claim, expected):
    assert claim.status == "verified"
    assert claim.conclusion["precision"] == "exact-after-normalization"
    assert claim.conclusion["scope"] == "*-2sigma_i"
    assert claim.conclusion["page"] == expected["page"]
    assert claim.conclusion["period_pattern"] == expected["period"]
    normalization = claim.conclusion["coefficient_normalization"]
    assert normalization["id"] == "pure-sigma-i-galois-fixed"
    assert normalization["value"] == 1
    assert normalization.get("coefficient_field", normalization.get("field")) == "F4"
    assert normalization["preserves_witt_layers"] is True
    assert expected["canonical"].issubset(claim.premise_ids)
    assert expected["forbidden"].isdisjoint(claim.premise_ids)
    assert "up to" not in claim.statement.lower()
    assert "up-to" not in claim.statement.lower()


@pytest.fixture(scope="module")
def fresh_project():
    return migrate_project(demo_project())


@pytest.mark.parametrize("ident", PATTERNS)
def test_fresh_review_summary_uses_the_exact_canonical_pattern(fresh_project, ident):
    claims = propositions(fresh_project)
    assert_current_pattern(claims[ident], PATTERNS[ident])
    # The named proofs must actually exist in the migrated project. Merely
    # replacing a string with a dangling prerequisite would not repair Review.
    assert PATTERNS[ident]["canonical"].issubset(claims)


def saved_legacy_project(fresh_project):
    project = project_from_dict(asdict(fresh_project))
    claims = propositions(project)
    for ident, expected in PATTERNS.items():
        claim = claims[ident]
        claim.status = "established" if expected["page"] == 7 else "verified"
        claim.statement = f"Legacy d{expected['page']} pattern up to a restriction unit."
        claim.conclusion["precision"] = "up-to-W(F4)-unit"
        claim.conclusion.pop("coefficient_normalization", None)
        claim.conclusion["researcher_annotation"] = {
            "text": "Check the second Witt layer separately.", "two_valuation": 1,
        }
        claim.notes = f"Researcher note on {ident}: do not erase this observation."
        claim.source_ref = f"researcher:{ident}:primary"
        claim.source_refs = [f"researcher:{ident}:additional"]
        claim.premise_ids = [*expected["old_premises"], "researcher:extra-premise"]
    return project


def test_saved_refresh_replaces_only_managed_dependencies_and_keeps_research(fresh_project):
    project = saved_legacy_project(fresh_project)
    before = {ident: deepcopy(asdict(propositions(project)[ident])) for ident in PATTERNS}
    result = ensure_reu_fact_chain(project)
    assert result is project
    claims = propositions(project)
    for ident, expected in PATTERNS.items():
        claim = claims[ident]
        assert_current_pattern(claim, expected)
        assert before[ident]["notes"] in claim.notes
        assert claim.conclusion["researcher_annotation"] == before[ident]["conclusion"]["researcher_annotation"]
        assert before[ident]["source_ref"] in {claim.source_ref, *claim.source_refs}
        assert set(before[ident]["source_refs"]).issubset(claim.source_refs)
        assert "researcher:extra-premise" in claim.premise_ids
        assert len(claim.premise_ids) == len(set(claim.premise_ids))
        assert len(claim.source_refs) == len(set(claim.source_refs))


def test_saved_refresh_is_idempotent(fresh_project):
    project = saved_legacy_project(fresh_project)
    ensure_reu_fact_chain(project)
    first = deepcopy(asdict(project))
    ensure_reu_fact_chain(project)
    assert asdict(project) == first


def test_refresh_does_not_normalize_or_rewrite_other_mixed_claims(fresh_project):
    project = saved_legacy_project(fresh_project)
    mixed = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    # Include both the old REU summaries and the canonical coefficient-linked
    # claims; neither may inherit a pure-sector scalar merely through refresh.
    before = {p.id: deepcopy(asdict(p)) for p in mixed.propositions}
    parameters = [p.conclusion["coefficient_parameter"] for p in mixed.propositions
                  if p.conclusion.get("coefficient_parameter", {}).get("id")
                  in {"mixed_d5_A", "mixed_d5_B"}]
    assert parameters and all(spec["value"] is None for spec in parameters)
    ensure_reu_fact_chain(project)
    assert {p.id: asdict(p) for p in mixed.propositions} == before


def test_refresh_does_not_match_user_ids_by_prefix(fresh_project):
    project = saved_legacy_project(fresh_project)
    workspace = next(w for w in project.workspaces if w.id == "ws_2sigma_i")
    manual = Proposition(
        "prop_reu_d9_corrected_pattern_researcher", "differential", "My separate proposal",
        status="under-review", conclusion={"precision": "up-to-W(F4)-unit"},
        premise_ids=["prop_chain_q8_d23"], notes="Keep this explicitly hypothetical.",
    )
    workspace.propositions.append(manual)
    before = deepcopy(asdict(manual))
    ensure_reu_fact_chain(project)
    assert asdict(manual) == before
