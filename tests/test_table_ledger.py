import json
import subprocess
import sys
from dataclasses import asdict
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import app
from domain.migrations import migrate_project
from domain.seed import demo_project
from domain.logic_graph import admitted_proposition_ids


SCRIPT = ROOT / "backend" / "static" / "table-ledger.js"


def test_independent_cycle_certificate_shows_products_and_tate_boundary_distinction():
    project = migrate_project(demo_project())
    workspace = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    cycle = next(p for p in workspace.propositions
                 if p.conclusion.get("fact_id") == "DER-3I-TATE-W-cycle")
    markup = run_ledger(asdict(cycle), "audit")
    assert cycle.rule == "Euler/Tate cycle certificate from DKLLW24"
    assert cycle.id in admitted_proposition_ids(project)
    assert "zero outgoing differentials" in markup
    assert "not immunity to incoming" in markup
    assert "Actual E2 product certificate" in markup
    assert "Tate zero by E13" in markup
    assert "3, 5, 7, 9, 11" in markup
    assert "No specific incoming differential is asserted" in markup
    assert "not delete an HFPSS class" in markup
    assert "This proof does not use Jan.29" in markup


def test_cycle_certificate_metadata_is_escaped():
    markup = run_ledger({"conclusion": {
        "cycle_constraint": "outgoing-only", "derivation": "<script>bad()</script>",
        "product_certificate": {"euler_cube": "<img>", "hidden_product": "<svg>",
                                "source_ref": "<script>source</script>"},
        "comparison_certificate": {"comparison_range": "<img>", "interpretation": "<svg>",
                                   "tate_zero_by_page": "<script>", "possible_pages": ["<img>"]},
    }}, "audit")
    assert all(tag not in markup for tag in ("<script", "<img", "<svg"))
    assert all(tag in markup for tag in ("&lt;script", "&lt;img", "&lt;svg"))


def test_verified_d3_certificate_shows_its_limited_scope_and_escapes_metadata():
    project = migrate_project(demo_project())
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == "FN-3I-001-zero")
    markup = run_ledger(asdict(claim), "audit")
    assert "Verified pure-sector d3 products" in markup
    assert "not a 2-torsion group" in markup and "no Jan29 premise" in markup
    assert "1094" in markup and "2868" in markup
    hostile = run_ledger({"conclusion": {"d3_product_certificate": {
        "derivation": "<script>bad()</script>", "scope": "<img>", "source_refs": ["<svg>"],
    }}}, "audit")
    assert all(tag not in hostile for tag in ("<script", "<img", "<svg"))
    assert all(tag in hostile for tag in ("&lt;script", "&lt;img", "&lt;svg"))


def test_fixed_galois_units_and_withdrawn_proofs_are_visible_without_claiming_admission():
    project = migrate_project(demo_project())
    workspace = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    fixed = next(p for p in workspace.propositions if p.conclusion.get("coefficient_parameter"))
    markup = run_ledger(asdict(fixed), "audit")
    assert "Galois-fixed F4 normalization: nonzero coefficient = 1" in markup
    assert "Fixed F4 coefficient: 1" in markup
    assert "Preserves Witt factors 2, 4" in markup
    assert "does not establish the differential" in markup
    assert "no implicit unit-1 assignment" not in markup
    assert "formal d23 families" not in markup
    withdrawn = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == "FN-3I-010")
    markup = run_ledger(asdict(withdrawn), "audit")
    assert "Withdrawn proof — not an accepted differential" in markup
    assert "11_21_30.pdf" in markup and "10_52_56.pdf" in markup


def test_new_authority_and_normalization_metadata_are_escaped():
    markup = run_ledger({"conclusion": {
        "source_status": "withdrawn-proof", "authority_decision": "<script>bad()</script>",
        "source_artifacts": ['<img src=x onerror="bad()">'],
        "coefficient_normalization": {"basis": "<svg onload=bad()>", "source_ref": "<script>source</script>"},
        "coefficient_parameter": {"id": "<script>id</script>", "value": 1, "fixed_reason": "<img>"},
    }}, "audit")
    assert all(tag not in markup for tag in ("<script", "<img", "<svg"))
    assert all(tag in markup for tag in ("&lt;script", "&lt;img", "&lt;svg"))


def test_verified_derivations_show_independent_proof_and_escape_all_fields():
    project = migrate_project(demo_project())
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == "FN-3I-006")
    markup = run_ledger(asdict(claim), "audit")
    assert claim.status == "verified"
    assert "Verified derivation:" in markup
    certificate = claim.conclusion["verification_certificate"]
    assert certificate["method"] in markup
    assert "730" in markup and "762" in markup
    hostile = run_ledger({"conclusion": {"verification_certificate": {
        "method": "<script>method()</script>", "derivation": "<img>",
        "scope": "<svg>", "source_refs": ["<script>source()</script>"],
    }}}, "audit")
    assert all(tag not in hostile for tag in ("<script", "<img", "<svg"))
    assert all(tag in hostile for tag in ("&lt;script", "&lt;img", "&lt;svg"))


def test_fixed_mixed_coefficient_uses_field_symbols_and_frobenius_not_witt_numerals():
    for parameter_id, value, symbols in (
        ("mixed_d3_C", 2, ("ζ", "ζ²")),
        ("mixed_d11_R", 3, ("ζ²", "ζ")),
    ):
        for reflected, expected in enumerate(symbols):
            markup = run_ledger({"conclusion": {"coefficient_parameter": {
                "id": parameter_id, "value": value, "domain": [value],
                "frobenius_power": reflected, "fixed_reason": "verified source product",
            }}}, "audit")
            assert f"Fixed F4 coefficient: {expected}<" in markup
            assert f"Fixed F4 coefficient: {value}" not in markup
            assert "Galois-fixed F4 normalization" not in markup


def test_source_caveats_remain_visible_and_escape_untrusted_metadata():
    project = migrate_project(demo_project())
    ws = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == "FN-MIX-006")
    markup = run_ledger(asdict(claim), "audit")
    assert "Source / coefficient caveats" in markup
    assert "1409-1413" in markup and "zeta^2" in markup and "lambda" in markup
    assert "printed coefficient 1 for review" in markup
    assert "verifies coefficient zeta^2" in markup
    assert "fixes lambda=1" in markup
    assert "Fixed F4 coefficient: ζ²<" in markup
    assert claim.status == "verified"
    assert claim.conclusion["printed_source_formula"]["status"] == "review-corrected"
    hostile = {"conclusion": {"source_blockers": ['<img onerror="fail()">'],
               "source_conflicts": [{"source_ref": "<script>bad()</script>"}],
               "coefficient_constraint": "<svg onload=bad()>"}}
    markup = run_ledger(hostile, "audit")
    assert "<img" not in markup and "<script>" not in markup and "<svg" not in markup
    assert "&lt;img" in markup and "&lt;script&gt;" in markup and "&lt;svg" in markup
    assert run_ledger({}, "audit") == ""
    assert "claimAuditMarkup(item)" in (ROOT / "backend/static/app.js").read_text(encoding="utf-8")


def test_leibniz_constraints_show_their_premises_without_injecting_markup():
    constraint = {"parameter_ids": ["alpha", '<img onerror="bad()">'],
                  "scope": '<script>bad()</script>', "derivation": '<svg onload="bad()">',
                  "source_ref": "formal_notes.tex:775", "normalization_value": 1,
                  "normalization_source": '<script>table()</script>'}
    markup = run_ledger({"conclusion": {"coefficient_constraints": [constraint]}}, "audit")
    assert "Leibniz compatibility: alpha = " in markup
    assert "formal_notes.tex:775" in markup
    assert "Integer-table normalization: 1" in markup
    assert "&lt;script&gt;table()&lt;/script&gt;" in markup
    assert all(tag not in markup for tag in ("<img", "<script", "<svg"))
    assert all(tag in markup for tag in ("&lt;img", "&lt;script", "&lt;svg"))


def run_ledger(payload, operation="rows", katex="absent"):
    script = """
require(process.argv[1]);
const payload = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const helper = globalThis.HFPSSTableLedger;
const mathCalls = [];
if (process.argv[3] !== 'absent') globalThis.katex = {renderToString: (formula, options) => {
  mathCalls.push({formula, options});
  if (process.argv[3] === 'throws') throw new Error('Unavailable font/parser');
  return '<span class="katex">safe renderer output</span>';
}};
let result;
if (process.argv[2] === 'render') {
  const count = {textContent: ''}, total = {textContent: ''}, content = {innerHTML: ''};
  const elements = {'[data-table-ledger-count]': count,
    '#shown-differential-count': total, '[data-table-ledger-content]': content};
  const mount = {open: payload.open, querySelector: selector => elements[selector] || null};
  const before = JSON.stringify(payload.workspace);
  helper.render(payload.workspace, mount);
  result = {open: mount.open, summary: count.textContent, total: total.textContent, html: content.innerHTML,
            unmodified: before === JSON.stringify(payload.workspace), mathCalls};
} else if (process.argv[2] === 'audit') result = helper.claimAuditMarkup(payload);
else if (process.argv[2] === 'markup') result = helper.markup(payload);
else result = helper.rowsForWorkspace(payload);
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", script, str(SCRIPT), operation, katex],
        input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_affine_zero_branch_and_premise_transport_are_visible_and_escaped():
    claim = {"conclusion": {
        "premise_transport_certificate": {
            "premise": "FN-2I-010<script>bad()</script>",
            "derivation": '<img onerror="bad()">', "source_ref": "formal_notes.tex:476-478",
        },
        "coefficient_parameter": {
            "id": "mixed_d5_A", "symbol": "c", "affine_offset": 1,
            "expression": '(c+1)<svg onload="bad()">', "frobenius_power": 1,
        },
    }}
    markup = run_ledger(claim, "audit")
    assert "FN-2I-010" in markup and "formal_notes.tex:476-478" in markup
    assert "Linked coefficient: (c+1)" in markup
    assert "zero differential, not an arrow or a page death" in markup
    assert "Frobenius image" in markup
    assert all(tag not in markup for tag in ("<img", "<script", "<svg"))
    assert all(tag in markup for tag in ("&lt;img", "&lt;script", "&lt;svg"))


def test_relative_coefficient_scope_is_visible_not_a_global_scalar():
    markup = run_ledger({"conclusion": {"coefficient_parameter": {
        "id": "mixed_d5_B", "symbol": "b", "target_component": 'S22H<img onerror="bad()">',
    }}}, "audit")
    assert "Relative coefficient on S22H" in markup
    assert "P+bQ is not b(P+Q)" in markup
    assert "<img" not in markup and "&lt;img" in markup


def test_historical_period_column_is_visible_without_becoming_a_published_row():
    metadata = {"column": "Period", "source_ref": "REU projects/table_Q8.tex:485-544",
                "interpretation": "Family stem displacement <img onerror=bad()>",
                "authority": "Historical review, not admission <script>bad()</script>"}
    claim = {"conclusion": {"related_period_table": metadata}}
    markup = run_ledger(claim, "audit")
    assert "printed Period column" in markup and "table_Q8.tex:485-544" in markup
    assert "Historical review, not admission" in markup
    assert "<img" not in markup and "<script>" not in markup
    assert "&lt;img" in markup and "&lt;script&gt;" in markup
    assert run_ledger({"propositions": [claim]}) == []


def test_conditional_euler_image_and_its_zero_branch_are_visible_and_escaped():
    condition = {"parameter_id": "mixed_d5_A", "equals": 1, "otherwise": "zero-euler-image",
                 "derivation": "Earlier boundary <script>bad()</script>",
                 "source_ref": "formal_notes.tex:520-526<img onerror=bad()>"}
    markup = run_ledger({"conclusion": {"coefficient_condition": condition}}, "audit")
    assert "mixed_d5_A = 1 in the source field" in markup
    assert "no arrow or class death" in markup and "own resolved unit" in markup
    assert "formal_notes.tex:520-526" in markup
    assert "<script>" not in markup and "<img" not in markup
    assert "&lt;script&gt;" in markup and "&lt;img" in markup


def test_ratio_uses_one_source_denominator_and_is_not_an_independent_unit():
    parameter = {"id": "gamma", "symbol": "gamma", "expression": "gamma/b",
                 "inverse_parameter_id": 'b<script>bad()</script>'}
    markup = run_ledger({"conclusion": {"coefficient_parameter": parameter}}, "audit")
    assert "Linked coefficient ratio: gamma/b" in markup
    assert "before applying Frobenius" in markup
    assert "unresolved denominator does not mean 1" in markup
    assert "<script>" not in markup and "&lt;script&gt;" in markup


@lru_cache(maxsize=1)
def published_workspaces():
    project = migrate_project(demo_project())
    return {
        workspace.id: {key: value for key, value in asdict(workspace).items()
                       if key in {"page", "classes", "propositions", "differentials"}}
        for workspace in project.workspaces if workspace.id in {"ws_integer", "ws_sigma_i"}
    }


def test_ledger_distinguishes_all_46_published_rows_from_19_derived_families():
    counts = {"published": 0, "derived": 0}
    for workspace_id, expected, table in (("ws_integer", 24, 8), ("ws_sigma_i", 22, 9)):
        workspace = published_workspaces()[workspace_id]
        all_rows = run_ledger(workspace)
        assert len(all_rows) == len(workspace["differentials"])
        rows = [row for row in all_rows if row["tableRecord"]]
        original = [row for row in rows if row["original"]]
        derived = [row for row in rows if not row["original"]]
        assert len(original) == expected
        assert {row["row"] for row in original} == set(range(1, expected + 1))
        assert all(row["table"] == table for row in rows)
        assert all(row["source"] and row["target"] and row["sourceRef"] for row in rows)
        assert len({row["key"] for row in rows}) == len(rows)
        assert all(row["evidence"] == "Published table row" for row in original)
        assert all(row["evidence"] != "Published table row" for row in derived)
        assert len(derived) == (13 if table == 8 else 6)
        counts["published"] += len(original)
        counts["derived"] += len(derived)
        if table == 8:
            # d7(D4) has D8 repeat: treating its repeat as D4 would kill 1.
            assert next(row for row in original if row["row"] == 5)["periodStem"] == 64
    assert counts == {"published": 46, "derived": 19}


def test_table_ledger_is_read_only_preserves_disclosure_state_and_escapes_source_text():
    workspace = {
        "page": 7,
        "classes": [{"id": "s", "label": '<img src=x onerror="fail()">'}, {"id": "t", "label": "D^4"}],
        "propositions": [{"id": "p", "conclusion": {"table_number": 8, "table_row": 5},
                          "source_ref": "</td><script>fail()</script>"}],
        "differentials": [{"id": "d", "source_id": "s", "target_id": "t", "proposition_id": "p", "page": 7, "period_stem": 64}],
    }
    for opened in (False, True):
        result = run_ledger({"workspace": workspace, "open": opened}, "render")
        assert result["open"] is opened
        assert result["unmodified"]
        assert result["total"] == "1"
        assert result["summary"] == "1 published · 0 derived"
        assert '<img ' not in result["html"] and '<script>' not in result["html"]
        assert '&lt;img ' in result["html"] and '&lt;script&gt;' in result["html"]
        assert 'class="is-current-page"' in result["html"]
        assert "Derived repeat (stem)" in result["html"]
        assert "not a printed table column" in result["html"]
        assert "up-to-unit" in result["html"]
        assert "permanent 64-stem" in result["html"]


def test_empty_workspace_has_an_explicit_empty_ledger():
    result = run_ledger({"page": 2, "classes": [], "propositions": [], "differentials": []}, "markup")
    assert result["count"] == 0
    assert result["summary"] == "No differential records in this workspace"
    assert "no recorded differentials" in result["html"]


def test_every_workspace_record_is_listed_with_neutral_total_and_provenance_groups():
    claims = [
        {"id": "published", "conclusion": {"table_number": 8, "table_row": 1}},
        {"id": "derived", "conclusion": {"origin_table": 8, "origin_row": 1}},
        {"id": "formal", "status": "review", "source_ref": "formal_notes.tex:903-970",
         "rule": "Source proposition", "conclusion": {"fact_id": "FN-MIX-004"}},
        {"id": "other-derived", "status": "verified", "rule": "Euler derivation",
         "conclusion": {"fact_id": "DER-MIX-EXAMPLE"}},
        {"id": "manual", "rule": "Manual differential", "conclusion": {}},
    ]
    workspace = {
        "page": 5, "classes": [{"id": "s", "label": "A"}, {"id": "t", "label": "B"}],
        "propositions": claims,
        "differentials": [
            {"id": f"d-{claim['id']}", "source_id": "s", "target_id": "t", "page": 5,
             "proposition_id": claim["id"]} for claim in claims
        ] + [
            # Two separate records can refer to the same printed row.
            {"id": "second-published", "source_id": "s", "target_id": "t", "page": 9,
             "proposition_id": "published"},
            {"id": "no-proposition", "source_id": "s", "target_id": "t", "page": 11},
        ],
    }
    rows = run_ledger(workspace)
    assert len(rows) == len(workspace["differentials"]) == 7
    assert {row["differentialId"] for row in rows} == {item["id"] for item in workspace["differentials"]}
    assert len({row["key"] for row in rows}) == 7
    assert [row["kind"] for row in rows].count("published") == 2
    assert [row["kind"] for row in rows].count("derived") == 2
    assert [row["kind"] for row in rows].count("formal") == 1
    assert [row["kind"] for row in rows].count("manual") == 2
    formal = next(row for row in rows if row["kind"] == "formal")
    assert formal["status"] == "review" and formal["page"] == 5 and formal["current"]
    assert formal["sourceRef"] == "formal_notes.tex:903-970"
    assert not formal["tableRecord"] and formal["printedProof"] == ""
    result = run_ledger({"workspace": workspace, "open": True}, "render")
    assert result["total"] == "7"
    assert result["summary"] == "2 published · 1 derived · 4 other records"
    assert result["html"].count("data-differential-id=") == 7
    assert "Formal, other derived and manual records · 4" in result["html"]
    assert "FN-MIX-004" in result["html"] and "formal_notes.tex:903-970" in result["html"]
    assert result["unmodified"] and result["open"]


def coefficient_workspace(metadata):
    return {
        "page": 11,
        "classes": [{"id": "s", "label": "RD^2"}, {"id": "t", "label": "4k^3D^3"}],
        "propositions": [{"id": "claim", "status": "review", "source_ref": "formal_notes.tex:972-991",
                          "conclusion": {"fact_id": "FN-MIX-006", **metadata}}],
        "differentials": [{"id": "d11", "source_id": "s", "target_id": "t", "page": 11,
                           "proposition_id": "claim"}],
    }


def test_formal_only_workspace_displays_resolved_atlas_coefficient_not_the_raw_parameter():
    from domain.atlas_transport import atlas_display_coefficient

    parameter = {"id": "mixed_d11_R", "value": 3, "domain": [3], "frobenius_power": 1}
    display = atlas_display_coefficient({"unit": 2}, {"unit": 3}, parameter)
    assert display["basis_ratio"] == 2 and display["value"] == 3 and display["resolved"]
    workspace = coefficient_workspace({"coefficient_parameter": parameter,
                                       "atlas_display_coefficient": display})
    row = run_ledger(workspace)[0]
    assert row["coefficient"]["status"] == "resolved"
    assert row["coefficient"]["expression"] == r"\zeta^2"
    assert row["target"] == "4k^3D^3"  # Witt factors are endpoint data, not F4 scalar codes.
    result = run_ledger({"workspace": workspace, "open": False}, "render", katex="available")
    assert result["total"] == "1" and result["summary"] == "0 published · 0 derived · 1 other records"
    assert [call["formula"] for call in result["mathCalls"]] == ["RD^2", "4k^3D^3", r"\zeta^2"]
    assert "Normalized basis coefficient" in result["html"]
    assert "unresolved; no implicit" not in result["html"]
    assert result["unmodified"] and not result["open"]


def test_unresolved_atlas_coefficient_does_not_treat_the_basis_ratio_as_a_computed_scalar():
    from domain.atlas_transport import atlas_display_coefficient

    parameter = {"id": "linked-c", "symbol": "c", "value": None,
                 "source_parameter": {"workspace_id": "ws_mixed", "parameter_id": "c"}}
    display = atlas_display_coefficient({"unit": 1}, {"unit": 3}, parameter)
    workspace = coefficient_workspace({"coefficient_parameter": parameter,
                                       "atlas_display_coefficient": display})
    row = run_ledger(workspace)[0]
    assert row["coefficient"]["status"] == "unresolved"
    assert row["coefficient"]["expression"] == "c"
    assert "linked source: ws_mixed / c" in row["coefficient"]["details"]
    result = run_ledger(workspace, "markup")
    assert result["count"] == 1
    assert "unresolved; no implicit unit-1 assignment" in result["html"]
    assert "basis ratio" in result["html"] and "fixed scalar" in result["html"]


def test_relative_coefficient_is_not_prefixed_to_the_whole_target_formula():
    from domain.atlas_transport import atlas_display_coefficient

    parameter = {"id": "mixed_d5_B", "symbol": "b", "target_component": "Q", "value": None}
    for atlas in (False, True):
        metadata = {"coefficient_parameter": parameter}
        if atlas:
            metadata["atlas_display_coefficient"] = atlas_display_coefficient({"unit": 1}, {"unit": 2}, parameter)
        workspace = coefficient_workspace(metadata)
        workspace["classes"][1]["label"] = "P+bQ"
        row = run_ledger(workspace)[0]
        assert row["target"] == "P+bQ" and row["coefficient"]["status"] == "unresolved"
        assert "Relative coefficient on Q only" in row["coefficient"]["basis"]
        html = run_ledger(workspace, "markup")["html"]
        assert "Relative coefficient on Q only" in html
        assert "b(P+Q)" not in html


def test_recorded_fixed_field_coefficient_applies_frobenius_and_retains_witt_target():
    workspace = coefficient_workspace({"coefficient_parameter": {
        "id": "mixed_d11_R", "value": 3, "frobenius_power": 1,
    }})
    row = run_ledger(workspace)[0]
    assert row["coefficient"]["status"] == "resolved"
    assert row["coefficient"]["expression"] == r"\zeta"
    assert row["target"] == "4k^3D^3"


def test_coefficient_details_and_unresolved_expression_are_escaped():
    workspace = coefficient_workspace({"atlas_display_coefficient": {
        "resolved": False, "value": None, "symbolic": '<img onerror="fail()">',
        "source_unit": "<script>source()</script>", "target_unit": "<svg onload=bad()>",
        "basis_ratio": "<img>", "reason": "<script>reason()</script>",
        "formula": "<svg>", "transported_parameter": {
            "target_component": "<img>", "source_parameter": {"workspace_id": "<svg>", "parameter_id": "<script>"},
        },
    }})
    result = run_ledger({"workspace": workspace, "open": True}, "render", katex="throws")
    assert result["total"] == "1" and result["unmodified"]
    assert all(tag not in result["html"] for tag in ("<img", "<script", "<svg"))
    assert all(tag in result["html"] for tag in ("&lt;img", "&lt;script", "&lt;svg"))
    assert all(call["options"]["trust"] is False for call in result["mathCalls"])


def test_manual_record_can_show_its_own_display_coefficient_without_a_proposition():
    workspace = {"page": 3, "differentials": [
        {"page": 3, "source_id": "s", "target_id": "t", "display_coefficient": {
            "value": 2, "resolved": True, "source_unit": 1, "target_unit": 2, "basis_ratio": 2,
        }},
        {"page": 3, "source_id": "s2", "target_id": "t2"},
    ]}
    rows = run_ledger(workspace)
    assert len(rows) == 2 and all(row["kind"] == "manual" for row in rows)
    assert next(row for row in rows if row["source"] == "s")["coefficient"]["expression"] == r"\zeta"
    result = run_ledger(workspace, "markup")
    assert result["count"] == 2 and result["html"].count("data-differential-id=") == 2


def test_invalid_recorded_field_unit_is_not_presented_as_resolved():
    for parameter in (
        {"id": "c", "value": 4},
        {"id": "c", "value": 2, "domain": [1]},
        {"id": "c", "value": 2, "frobenius_power": 2},
    ):
        row = run_ledger(coefficient_workspace({"coefficient_parameter": parameter}))[0]
        assert row["coefficient"]["status"] == "unresolved"
        assert row["coefficient"]["expression"] == "c"


class DisclosureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.disclosures = []
        self.scripts = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "details" and attributes.get("id") == "published-table-ledger":
            self.disclosures.append(attributes)
        if tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"])


def test_both_routes_have_one_collapsed_disclosure_and_load_helper_before_app():
    client = app.test_client()
    for route in ("/", "/review"):
        response = client.get(route)
        assert response.status_code == 200
        parser = DisclosureParser()
        parser.feed(response.get_data(as_text=True))
        assert len(parser.disclosures) == 1
        assert "open" not in parser.disclosures[0]
        assert ("review-table-ledger" in parser.disclosures[0]["class"]) == (route == "/review")
        assert parser.scripts.index("/static/table-ledger.js") < parser.scripts.index("/static/app.js")


def test_all_original_rows_show_actual_bidegrees_and_the_printed_proof_locator():
    for workspace in published_workspaces().values():
        rows = run_ledger(workspace)
        claims = {claim["id"]: claim for claim in workspace["propositions"]}
        differentials = {arrow["id"]: arrow for arrow in workspace["differentials"]}
        for row in rows:
            source, target = row["sourceBidegree"], row["targetBidegree"]
            assert source is not None and target is not None
            assert target == {"stem": source["stem"] - 1, "filtration": source["filtration"] + row["page"]}
            metadata = claims[differentials[row["differentialId"]]["proposition_id"]]["conclusion"]
            assert row["printedProof"] == (metadata["printed_proof"] if row["original"] else "")
        html = run_ledger(workspace, "markup")["html"]
        assert "Source (s, f)" in html and "Target (s, f)" in html and "Printed proof" in html
        assert "Not a printed row" in html
    integer = run_ledger(published_workspaces()["ws_integer"])
    row = next(row for row in integer if row["original"] and row["row"] == 22)
    assert row["sourceBidegree"] == {"stem": -7, "filtration": 1}
    assert row["targetBidegree"] == {"stem": -8, "filtration": 24}
    assert row["printedProof"] == "Proposition 4.14 (vanishing line)"
    html = run_ledger(published_workspaces()["ws_integer"], "markup")["html"]
    assert "(-7, 1)" in html and "(-8, 24)" in html and "Proposition 4.14" in html


def test_optional_katex_uses_untrusted_math_mode_and_safely_falls_back():
    workspace = {
        "page": 3,
        "classes": [{"id": "s", "label": r"\href{javascript:alert(1)}{D}", "grade": {"stem": 8, "filtration": 0}},
                    {"id": "t", "label": '<img src=x onerror="fail()">', "grade": {"stem": 7, "filtration": 3}}],
        "propositions": [{"id": "p", "conclusion": {"table_number": 8, "table_row": 1,
                           "printed_proof": '<script>proof()</script>'}, "source_ref": '<svg onload="source()">'}],
        "differentials": [{"id": "d", "source_id": "s", "target_id": "t", "page": 3,
                           "proposition_id": "p", "period_stem": 8}],
    }
    for mode in ("absent", "available", "throws"):
        result = run_ledger({"workspace": workspace, "open": True}, "render", katex=mode)
        assert result["unmodified"] and result["open"]
        assert '<script>' not in result["html"] and '<svg ' not in result["html"] and '<img ' not in result["html"]
        assert '&lt;script&gt;proof()&lt;/script&gt;' in result["html"]
        assert '(8, 0)' in result["html"] and '(7, 3)' in result["html"]
        if mode == "absent":
            assert not result["mathCalls"]
        else:
            assert [call["formula"] for call in result["mathCalls"]] == [node["label"] for node in workspace["classes"]]
            assert all(call["options"] == {"throwOnError": False, "trust": False, "displayMode": False}
                       for call in result["mathCalls"])
        if mode == "available":
            assert result["html"].count('class="katex"') == 2
        else:
            assert r"\href{javascript:alert(1)}{D}" in result["html"]
            assert '&lt;img src=x onerror=&quot;fail()&quot;&gt;' in result["html"]


def test_missing_or_non_numeric_bidegrees_are_not_invented_or_injected():
    workspace = {
        "page": 3,
        "classes": [{"id": "s", "label": "D", "grade": {"stem": '<script>bad()</script>', "filtration": 0}}],
        "propositions": [{"id": "p", "conclusion": {"table_number": 8, "table_row": 1}}],
        "differentials": [{"id": "d", "source_id": "s", "target_id": "missing", "page": 3, "proposition_id": "p"}],
    }
    row = run_ledger(workspace)[0]
    assert row["sourceBidegree"] is None and row["targetBidegree"] is None
    html = run_ledger(workspace, "markup")["html"]
    assert "Not recorded" in html and "<script>" not in html


def test_table_ledger_static_copies_are_identical():
    assert SCRIPT.read_bytes() == (ROOT / "public/static/table-ledger.js").read_bytes()


def test_atlas_rows_show_transport_provenance_without_changing_source_row_counts():
    project = migrate_project(demo_project())
    original = {row["row"]: row for row in run_ledger(published_workspaces()["ws_sigma_i"]) if row["original"]}
    for ident, action, shift in (("ws_q8-ro-a0-b1", "omega^1", 0), ("ws_q8-ro-a3-b3", "omega^2", -16)):
        workspace = next(asdict(item) for item in project.workspaces if item.id == ident)
        rows = run_ledger(workspace)
        printed = [row for row in rows if row["original"]]
        derived = [row for row in rows if row["tableRecord"] and not row["original"]]
        assert len(printed) == 22 and len(derived) == 6
        assert {row["row"] for row in printed} == set(range(1, 23))
        for row in printed:
            source = original[row["row"]]
            assert row["evidence"] == "Transported table row" and row["transported"]
            assert row["printedProof"] == source["printedProof"]
            assert row["sourceRef"] == source["sourceRef"]
            assert row["sourceBidegree"]["stem"] == source["sourceBidegree"]["stem"] + shift
            assert row["targetBidegree"]["stem"] == source["targetBidegree"]["stem"] + shift
            assert row["transportProvenance"] == f"{action}; stem shift {shift:+d}; from ws_sigma_i"
        result = run_ledger(workspace, "markup")
        assert result["summary"] == "22 published · 6 derived"
        assert "Transported table row" in result["html"]
        assert f"{action}; stem shift {shift:+d}; from ws_sigma_i" in result["html"]
        assert "Proposition 5.8" in result["html"]


def test_transport_provenance_is_escaped_and_missing_shift_is_not_assumed_zero():
    workspace = {
        "page": 3,
        "classes": [{"id": "s", "label": "A"}, {"id": "t", "label": "B"}],
        "propositions": [{"id": "p", "conclusion": {"table_number": 9, "table_row": 1,
            "printed_proof": "Proposition 5.8", "atlas_transport": {
                "action": '<script>alert(1)</script>', "source_workspace_id": '<img src=x onerror="fail()">',
            }}}],
        "differentials": [{"id": "d", "source_id": "s", "target_id": "t", "page": 3, "proposition_id": "p"}],
    }
    row = run_ledger(workspace)[0]
    assert row["original"] and row["transported"] and row["evidence"] == "Transported table row"
    assert "stem shift not recorded" in row["transportProvenance"]
    html = run_ledger(workspace, "markup")["html"]
    assert "<script>" not in html and "<img " not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
