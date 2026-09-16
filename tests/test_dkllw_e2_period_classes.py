import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "backend" / "data" / "review" / "dkllw24_q8_e2_period_classes.v1.json"


def load_dataset() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def test_review_dataset_has_two_source_pages_and_is_not_canonical():
    data = load_dataset()

    assert data["schema_version"] == 1
    assert data["status"] == "review-required"
    assert data["canonical"] is False
    assert {page["id"] for page in data["pages"]} == {
        "q8-hfpss-e2-integer",
        "q8-hfpss-e2-sigma-i",
    }


def test_all_families_share_semiperiod_while_module_kinds_stay_distinct():
    data = load_dataset()
    periods = {item["id"]: item for item in data["named_period_classes"]}

    assert periods["hfpss-D8-object-orbit"]["equivalence"] == "x~D^(8q)x"
    assert "g^s" in periods["hfpss-g-D8-semiperiod"]["family_relation"]
    assert periods["hfpss-g-D8-semiperiod"]["translation_parameters"]["s"] == (
        "integer >= 0"
    )
    assert "g^r" in periods["tate-g-D8-lattice"]["equivalence"]
    assert "positive-filtration" in periods["tate-g-D8-lattice"]["equivalence"]

    families = {item["id"]: item for item in data["cycle_families"]}
    assert families["bo-integer-permanent"]["period_class"] == (
        "hfpss-g-D8-semiperiod"
    )
    assert families["bo-sigma-permanent"]["period_class"] == (
        "hfpss-g-D8-semiperiod"
    )
    assert (
        families["tate-visible-integer-complement"]["period_class"]
        == "hfpss-g-D8-semiperiod"
    )
    assert (
        families["tate-visible-integer-complement"]["comparison_period_class"]
        == "tate-g-D8-lattice"
    )
    assert families["bo-integer-permanent"]["module_kind"] == (
        "j-adic-formal-power-series"
    )
    assert families["bo-sigma-permanent"]["module_kind"] == (
        "j-adic-formal-power-series"
    )
    assert families["bo-integer-d3-pairs"]["formal_series_family_id"] == (
        "fs.integer.bo"
    )
    assert families["bo-integer-permanent"]["formal_series_family_id"] == (
        "fs.integer.bo"
    )
    assert families["bo-sigma-d3-pairs"]["formal_series_family_id"] == (
        "fs.sigma-i.bo"
    )
    assert families["bo-sigma-permanent"]["formal_series_family_id"] == (
        "fs.sigma-i.bo"
    )
    assert "including a positive-filtration bo-pattern class" in data[
        "classification_semantics"
    ]["not_a_disjoint_map_theoretic_partition"]
    assert "not a low-filtration tag" in data["classification_semantics"]["bo_tag"]


def test_chart_module_kinds_record_j_adic_completion():
    chart = load_dataset()["chart_semantics"]

    assert chart["module_glyphs"]["j_for_Q8"] == "v1^4D^-1"
    assert "jF4[[j]]" in chart["module_kinds"]["j-adic-formal-power-series"]
    assert "visible height" in chart["classification_warning"]


def test_c3_and_galois_actions_are_explicitly_separate():
    symmetry = load_dataset()["symmetry_and_coefficients"]

    assert symmetry["c3"]["representation_orbit"] == [
        "sigma_i",
        "sigma_j",
        "sigma_k",
    ]
    assert symmetry["galois"]["frobenius"] == {
        "zeta": "zeta^2",
        "zeta^2": "zeta",
    }
    assert "psi transport swaps j and k" in symmetry["galois"]["scope_warning"]
    assert symmetry["galois"]["coefficient_rule"].endswith(
        "zeta and zeta^2 are exchanged"
    )


def test_hidden_h1_and_h2_extensions_are_retained_verbatim():
    extensions = {item["id"]: item for item in load_dataset()["hidden_extensions"]}

    assert extensions["ext-integer-h2"]["formula"] == "h2*(x^2h2)=4kD"
    assert extensions["ext-sigma-h1"]["formula"].startswith("h1*(k^m x^2h1")
    assert extensions["ext-sigma-h2"]["formula"].startswith("h2*(k^m x^3")
    assert extensions["ext-sigma-h1"]["parameters"]["n"] == "any integer"


def test_all_references_and_generator_ids_are_unique_and_resolve():
    data = load_dataset()
    page_ids = {page["id"] for page in data["pages"]}
    family_ids = [item["id"] for item in data["cycle_families"]]
    extension_ids = {item["id"] for item in data["hidden_extensions"]}

    assert len(family_ids) == len(set(family_ids))
    for page in data["pages"]:
        assert set(page["cycle_family_ids"]).issubset(family_ids)
        assert set(page["hidden_extensions"]).issubset(extension_ids)
    for family in data["cycle_families"]:
        assert family["page"] in page_ids


def test_sigma_v1_squared_grade_records_the_arxiv_source_discrepancy():
    data = load_dataset()
    sigma_page = next(page for page in data["pages"] if page["id"].endswith("sigma-i"))
    generator = next(
        item for item in sigma_page["e2_module_generators"] if item["id"] == "sigma-v1-2"
    )

    assert generator["display_grade"] == {"stem": 4, "filtration": 0}
    assert "line 1167 prints (0,2)" in generator["source_note"]
    assert any(
        item["id"] == "dkllw-arxiv-v3-sigma-v1-2-grade"
        for item in data["source_discrepancies"]
    )
