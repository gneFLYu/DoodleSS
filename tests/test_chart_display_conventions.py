"""Small Node VM checks for chart layout and safe mathematical presentation."""
import itertools
import json
import math
from pathlib import Path
import subprocess
from xml.etree import ElementTree

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backend/static/app.js"
LAYOUT = ROOT / "backend/static/cell-layout.js"


def run_node(script, payload):
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=20,
    )
    return json.loads(completed.stdout)


def app_helper(functions, expression, **values):
    return run_node(r"""
const fs = require('fs'), vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const source = fs.readFileSync(input.path, 'utf8');
function extract(name) {
  const start = source.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`Missing production helper: ${name}`);
  const tail = source.slice(start + 1);
  const next = /\n(?:async )?function\s/.exec(tail);
  return source.slice(start, next ? start + 1 + next.index : source.length);
}
const escapeText = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const context = {
  input, calls: [], window: {}, atlasSector: () => null,
  document: {createElement() {return {
    textContent: '', get innerHTML() {return escapeText(this.textContent);}
  };}}
};
vm.createContext(context);
vm.runInContext(input.functions.map(extract).join('\n'), context);
const result = vm.runInContext(input.expression, context);
process.stdout.write(JSON.stringify({result, calls: context.calls}));
""", {"path": str(APP), "functions": functions, "expression": expression, **values})


@pytest.fixture(scope="module", params=(1.35, 2.4))
def packed_samples(request):
    envelope = request.param
    records = []
    for density in (1, 2, 4, 9, 16):
        for index in range(density):
            records.append({
                "key": f"{density}-{index}", "cellKey": f"{density}:0",
                "label": f"x^{index}",
                "shape": ("finite-two-tower" if envelope == 2.4 else "square") if index % 3 == 0 else "circle",
                "size": (0.8, 4.2, 9)[index % 3],
                "periodic": index % 3 == 1, "readOnly": index % 3 == 2,
            })
    return run_node(r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const layout = require(input.path);
const options = {uniformSize: true, glyphEnvelope: input.envelope, baseYOffset: 0.16};
const samples = input.cells.map(cell => ({cell, envelope: input.envelope,
  packed: layout.packInstances(input.records, cell, options),
  reversed: layout.packInstances([...input.records].reverse(), cell, options)
}));
process.stdout.write(JSON.stringify(samples));
""", {"path": str(LAYOUT), "records": records, "envelope": envelope,
      "cells": [1.5, 2, 3, 6, 14, 28, 56]})


def test_uniform_glyph_size_ignores_origin_requested_size_and_local_cell_density(packed_samples):
    for sample in packed_samples:
        packed = sample["packed"]
        assert len(packed) == 32 and len({node["key"] for node in packed}) == 32
        assert {node["packCount"] for node in packed} == {1, 2, 4, 9, 16}
        assert any(node["periodic"] for node in packed) and any(node["readOnly"] for node in packed)
        assert all(node["size"] == pytest.approx(packed[0]["size"]) for node in packed)
        assert all(node["hitRadius"] >= node["size"] for node in packed)
        coordinates = lambda nodes: {node["key"]: (node["dx"], node["dy"], node["size"]) for node in nodes}
        assert coordinates(packed) == coordinates(sample["reversed"])


def test_uniform_glyph_size_scales_with_zoom(packed_samples):
    radii = [sample["packed"][0]["size"] for sample in packed_samples]
    assert all(left < right for left, right in itertools.pairwise(radii))


def test_low_zoom_threshold_eases_sparse_glyph_toward_cell_fill():
    sample = run_node(r"""
const layout = require(input.path);
const options = {uniformSize: true, glyphEnvelope: 1.35};
const records = [{key: 'a', cellKey: '0:0', size: 5.5}, {key: 'b', cellKey: '1:0', size: 5.5}];
const low = layout.packInstances(records, 2, options);
const normal = layout.packInstances(records, 28, options);
process.stdout.write(JSON.stringify({low, normal}));
""", {"path": str(LAYOUT)})
    low_radius = sample["low"][0]["size"]
    normal_radius = sample["normal"][0]["size"]
    assert all(node["size"] == pytest.approx(low_radius) for node in sample["low"])
    assert 0.35 <= 1.35 * low_radius / 2 <= 0.45
    assert low_radius < normal_radius


def test_full_glyph_envelopes_stay_in_cells_without_colliding(packed_samples):
    for sample in packed_samples:
        groups = {}
        for node in sample["packed"]:
            radius = sample["envelope"] * node["size"]
            assert abs(node["dx"]) + radius <= sample["cell"] / 2 + 1e-9
            assert abs(node["dy"]) + radius <= sample["cell"] / 2 + 1e-9
            groups.setdefault(node["cellKey"], []).append(node)
        for group in groups.values():
            for left, right in itertools.combinations(group, 2):
                distance = math.hypot(left["dx"] - right["dx"], left["dy"] - right["dy"])
                assert distance + 1e-9 >= sample["envelope"] * (left["size"] + right["size"])


def test_math_labels_use_untrusted_katex_mode_without_changing_the_expression():
    result = app_helper(["escapeHtml", "mathMarkup"], r"""(() => {
      window.katex = {renderToString(source, options) {
        calls.push({source, options}); return '<span class="katex">rendered</span>';
      }};
      return mathMarkup(input.label);
    })()""", label=r"\zeta^2h_1D^3u_{\sigma_i}")
    assert result["result"] == '<span class="katex">rendered</span>'
    assert result["calls"] == [{
        "source": r"\zeta^2h_1D^3u_{\sigma_i}",
        "options": {"throwOnError": False, "trust": False, "displayMode": False},
    }]


@pytest.mark.parametrize("renderer_throws", [False, True])
def test_math_label_fallback_escapes_html_when_katex_is_unavailable(renderer_throws):
    result = app_helper(["escapeHtml", "mathMarkup"], """(() => {
      if (input.renderer_throws) window.katex = {renderToString() {throw new Error('unavailable');}};
      return mathMarkup(input.label);
    })()""", renderer_throws=renderer_throws, label='<img src=x onerror="boom()"> & D')
    assert result["result"] == '&lt;img src=x onerror="boom()"&gt; &amp; D'
    assert "<img" not in result["result"]


def test_mixed_prose_renders_only_math_and_escapes_the_remaining_text():
    result = app_helper(["escapeHtml", "mathMarkup", "mathTextMarkup"], r"""(() => {
      window.katex = {renderToString(source, options) {
        calls.push({source, options}); return '<span class="katex">rendered</span>';
      }};
      return mathTextMarkup(input.text);
    })()""", text=r"Compare $h_1D$ and \(\zeta^2\); <img src=x>.")
    assert [call["source"] for call in result["calls"]] == ["h_1D", r"\zeta^2"]
    assert all(call["options"]["trust"] is False for call in result["calls"])
    assert result["result"].count('class="katex"') == 2
    assert result["result"].startswith("Compare ") and "&lt;img src=x&gt;" in result["result"]


def test_compact_sector_labels_do_not_expose_internal_atlas_ids():
    result = app_helper(["compactSectorLabel"], "input.sectors.map(compactSectorLabel)", sectors=[
        "q8-ro-a3-b1", "q8-ro-a0-b1", "q8-ro-a1-b0", "q8-ro-a0-b0",
        {"a": 3, "b": 2}, "reference workspace",
    ])
    assert result["result"] == ["*-3i-j", "*-j", "*-i", "*", "*-3i-2j", "reference workspace"]


COEFFICIENT_HELPERS = ["f4DisplayMultiply", "f4DisplayLatex", "differentialDisplayCoefficient"]


def display_coefficient(metadata, coefficient):
    return app_helper(COEFFICIENT_HELPERS, """(() => {
      const workspace = {propositions: [{id: 'claim', conclusion: input.metadata}]};
      const differential = {id: 'arrow', proposition_id: 'claim'};
      const algebra = {coefficientState: () => input.coefficient};
      return differentialDisplayCoefficient(workspace, differential, algebra);
    })()""", metadata=metadata, coefficient=coefficient)["result"]


def test_runtime_scalar_two_is_displayed_as_zeta_not_the_integer_two():
    result = display_coefficient({}, {"resolved": True, "value": 2})
    assert result == {"value": 2, "latex": r"\zeta", "basis": "recorded generators",
                      "sourceUnit": 1, "targetUnit": 1}


def test_expanded_basis_ratio_is_applied_once_and_unit_one_is_omitted():
    result = display_coefficient({"atlas_display_coefficient": {
        "basis_ratio": 3, "source_unit": 3, "target_unit": 1,
    }}, {"resolved": True, "value": 2})
    assert result == {"value": 1, "latex": "", "basis": "unscaled expanded generators",
                      "sourceUnit": 3, "targetUnit": 1}


def test_already_transported_runtime_scalar_is_not_frobenius_transformed_again():
    result = display_coefficient({"coefficient_parameter": {
        "value": 2, "frobenius_power": 1,
    }}, {"resolved": True, "value": 3})
    assert result["value"] == 3 and result["latex"] == r"\zeta^{2}"


def test_precomputed_expanded_coefficient_is_not_multiplied_by_its_basis_ratio_again():
    result = display_coefficient({"atlas_display_coefficient": {
        "resolved": True, "value": 3, "basis_ratio": 3,
        "source_unit": 3, "target_unit": 1,
    }}, {"resolved": False})
    assert result["value"] == 3 and result["latex"] == r"\zeta^{2}"


@pytest.mark.parametrize("metadata,coefficient", [
    ({}, {"resolved": False}),
    ({"coefficient_parameter": {"target_component": "Q"}}, {"resolved": False}),
    ({"coefficient_parameter": {"target_component": "Q"}}, {"resolved": True, "value": 2}),
    ({}, {"resolved": True, "value": 2, "component": "Q"}),
    ({"atlas_display_coefficient": {"resolved": True, "value": 2, "basis_ratio": None}},
     {"resolved": True, "value": 3}),
])
def test_unresolved_or_component_coefficients_are_not_shown_as_global_arrow_scalars(metadata, coefficient):
    assert display_coefficient(metadata, coefficient) is None


def test_unit_one_produces_no_arrow_coefficient_badge():
    result = app_helper(["escapeHtml", *COEFFICIENT_HELPERS, "differentialCoefficientMarkup"], """(() => {
      const workspace = {propositions: [{id: 'claim', conclusion: {
        atlas_display_coefficient: {basis_ratio: 3}
      }}]};
      const item = {diff: {id: 'arrow', proposition_id: 'claim'}};
      return differentialCoefficientMarkup(workspace, item,
        {coefficientState: () => ({resolved: true, value: 2})}, {x: 0, y: 0}, {x: 4, y: 8});
    })()""")
    assert result["result"] == ""


@pytest.mark.parametrize("horizontal,vertical,expected", [
    (1, 0, r"h_1D^{10}u_{\sigma_j}"),
    (-1, 0, r"{\zeta}h_1D^{-6}u_{\sigma_j}"),
    (0, 1, r"{\zeta^{2}}kh_1D^{5}u_{\sigma_j}"),
    (1, 1, r"kh_1D^{13}u_{\sigma_j}"),
])
def test_periodic_label_uses_exact_basis_and_omega_unit_for_d8_and_forward_g(horizontal, vertical, expected):
    result = app_helper(["latexPower", "shiftPeriodFactor", "shiftDExponent", "shiftKExponent", "f4DisplayMultiply",
                         "f4DisplayLatex", "periodicDisplayLabel"], """(() => {
      const record = {periodic: true, horizontalStem: 64,
        horizontalExponent: input.horizontal, verticalExponent: input.vertical,
        item: {label: 'stored-source-label', style: {
          atlas_display_basis: {status: 'exact', expression: input.basis_expression, unit: 3},
          atlas_transport: {omega_power: 1}
        }}
      };
      const before = JSON.stringify(record);
      const label = periodicDisplayLabel(record);
      return {label, unchanged: JSON.stringify(record) === before,
        anchor: periodicDisplayLabel({...record, periodic: false})};
    })()""", horizontal=horizontal, vertical=vertical, basis_expression=r"h_1D^2u_{\sigma_j}")
    assert result["result"] == {"label": expected, "unchanged": True, "anchor": "stored-source-label"}


LABEL_HELPERS = ["escapeHtml", "latexPower", "shiftPeriodFactor", "shiftDExponent", "shiftKExponent",
                 "f4DisplayMultiply", "f4DisplayLatex", "periodicDisplayLabel",
                 "inBounds", "classLabelMarkup"]


def occurrence_labels(*, selected_workspace="ws", selected_page=9, selected_class="family", tight_bounds=False):
    return app_helper(LABEL_HELPERS, r"""(() => {
      globalThis.workspace = () => ({page: 9});
      globalThis.state = {workspaceId: 'ws', selectedClassId: 'family',
        selectedQuotientInstance: null,
        selectedOccurrence: {workspaceId: input.selected_workspace, page: input.selected_page, classId: input.selected_class,
          instanceKey: 'family:205:13'}};
      const anchor = {item: {id: 'family', label: String.raw`h_1D^2u_{\sigma_i}`, style: {}},
        grade: {stem: 17, filtration: 1}, periodic: false, instanceKey: 'family:17:1'};
      const selected = {...anchor, periodic: true, horizontalStem: 64,
        horizontalExponent: 2, verticalExponent: 3, grade: {stem: 205, filtration: 13},
        instanceKey: 'family:205:13'};
      const sibling = {...selected, horizontalExponent: 3,
        grade: {stem: 269, filtration: 13}, instanceKey: 'family:269:13'};
      const visible = input.tight_bounds
        ? {stemMin: 205, stemMax: 205, filtrationMin: 13, filtrationMax: 13}
        : {stemMin: 0, stemMax: 300, filtrationMin: 0, filtrationMax: 20};
      const render = record => classLabelMarkup(record, {x: 50, y: 40}, {cell: 28}, visible);
      return {selected: render(selected), sibling: render(sibling), anchor: render(anchor),
        selectedClassId: state.selectedClassId};
    })()""", selected_workspace=selected_workspace, selected_page=selected_page, selected_class=selected_class,
                      tight_bounds=tight_bounds)["result"]


@pytest.mark.parametrize("tight_bounds", [False, True])
def test_only_selected_periodic_occurrence_displays_its_full_high_powers_and_bidegree(tight_bounds):
    result = occurrence_labels(tight_bounds=tight_bounds)
    assert r'data-latex="k^{3}h_1D^{27}u_{\sigma_i}"' in result["selected"]
    assert '<small class="selected-bidegree">(205, 13)</small>' in result["selected"]
    assert "selected-occurrence-label" in result["selected"]
    assert result["sibling"] == result["anchor"] == ""
    # Label selection does not replace the class-family selection used by highlighting.
    assert result["selectedClassId"] == "family"


@pytest.mark.parametrize("selected_workspace,selected_page,selected_class", [
    ("other", 9, "family"), ("ws", 11, "family"), ("ws", 9, "other-class"),
])
def test_stale_occurrence_falls_back_to_the_current_class_anchor(selected_workspace, selected_page, selected_class):
    result = occurrence_labels(selected_workspace=selected_workspace, selected_page=selected_page, selected_class=selected_class)
    assert result["selected"] == result["sibling"] == ""
    assert r'data-latex="h_1D^2u_{\sigma_i}"' in result["anchor"]
    assert '<small class="selected-bidegree">(17, 1)</small>' in result["anchor"]
    assert "selected-occurrence-label" not in result["anchor"]
    assert result["selectedClassId"] == "family"


def test_fate_inspector_uses_occurrence_grade_and_labels_the_unshifted_family_basis():
    result = app_helper(["escapeHtml", "mathMarkup", "gradeText", "renderFateInspector"], r"""(() => {
      const elements = new Map();
      globalThis.$ = selector => {
        if (!elements.has(selector)) elements.set(selector, {
          innerHTML: '', textContent: '', addEventListener() {}
        });
        return elements.get(selector);
      };
      const representation = {sigma_i: -1};
      const node = {id: 'family', label: String.raw`h_1D^2u_{\sigma_i}`,
        grade: {stem: 17, filtration: 1, representation},
        style: {atlas_display_basis: {
          expression: String.raw`h_1D^2u_{\sigma_i}`,
          expanded_expression: String.raw`\zeta^{2}h_1D^2u_{\sigma_i}`,
          thom_basis: 'transported orientation'
        }}
      };
      const ws = {id: 'ws', page: 9, classes: [node], differentials: [], propositions: []};
      globalThis.workspace = () => ws;
      globalThis.fateFor = () => null;
      globalThis.visualStateFor = () => 'unknown';
      globalThis.state = {workspaceId: 'ws', selectedClassId: 'family', candidateResults: null,
        selectedOccurrence: {workspaceId: 'ws', page: 9, classId: 'family', instanceKey: 'family:205:13',
          grade: {stem: 205, filtration: 13, representation},
          label: String.raw`k^{3}h_1D^{27}u_{\sigma_i}`}};
      window.katex = {renderToString(source) {
        return `<span class="katex">${escapeHtml(source)}</span>`;
      }};
      const before = JSON.stringify(node);
      renderFateInspector();
      const selected = $('#fate-inspector').innerHTML;
      state.selectedOccurrence = null;
      renderFateInspector();
      return {selected, anchor: $('#fate-inspector').innerHTML,
        unchanged: JSON.stringify(node) === before};
    })()""")["result"]
    assert r'<strong><span class="katex">k^{3}h_1D^{27}u_{\sigma_i}</span></strong>' in result["selected"]
    assert "Selected occurrence: (205, 13) · E9" in result["selected"]
    assert "<dt>Grade</dt><dd>(205, 13) -sigma_i</dd>" in result["selected"]
    assert "<dt>Grade</dt><dd>(17, 1)" not in result["selected"]
    assert r'<dt>Family anchor: unscaled basis</dt><dd><span class="katex">h_1D^2u_{\sigma_i}</span></dd>' in result["selected"]
    assert r'<dt>Family anchor: transported element</dt><dd><span class="katex">\zeta^{2}h_1D^2u_{\sigma_i}</span></dd>' in result["selected"]
    assert "<dt>Grade</dt><dd>(17, 1) -sigma_i</dd>" in result["anchor"]
    assert "Selected occurrence:" not in result["anchor"]
    assert result["unchanged"] is True


@pytest.mark.parametrize("levels", [2, 3])
def test_finite_two_tower_uses_ordinary_dot_radius_and_fits_its_envelope(levels):
    result = app_helper(["classGlyphMarkup"], """(() => {
      const point = {x: 40, y: 60}, size = 5;
      const ports = Array.from({length: input.levels}, (_, level) => `${level}:0`);
      ports.push('0:1');
      return {tower: classGlyphMarkup({shape: 'finite-two-tower', size, modulePorts: ports}, point, 'selected'),
        dot: classGlyphMarkup({shape: 'dot', size}, point, 'selected'), point, size};
    })()""", levels=levels)["result"]
    circles = ElementTree.fromstring(result["tower"]).findall("circle")
    dot = ElementTree.fromstring(result["dot"])
    assert len(circles) == levels
    dot_radius = float(dot.attrib["r"])
    assert dot_radius == pytest.approx(0.72 * result["size"])
    positions = []
    for circle in circles:
        radius = float(circle.attrib["r"])
        assert radius == pytest.approx(dot_radius)
        assert float(circle.attrib["cx"]) == result["point"]["x"]
        position = float(circle.attrib["cy"])
        assert abs(position - result["point"]["y"]) + radius < 2.4 * result["size"]
        positions.append(position)
    for left, right in itertools.pairwise(positions):
        assert abs(left - right) == pytest.approx(1.6 * result["size"])
        assert abs(left - right) >= 2 * dot_radius


@pytest.mark.parametrize("shape,envelope", [("dot", 1.35), ("finite-two-tower", 2.4)])
def test_chart_packer_reserves_the_finite_tower_envelope_without_changing_uniform_size(shape, envelope):
    result = app_helper(["packedClassInstances"], """(() => {
      globalThis.clamp = (value, low, high) => Math.max(low, Math.min(high, value));
      globalThis.periodicClassInstances = () => [{instanceKey: 'a:0:0',
        item: {id: 'a', label: 'a'}, grade: {stem: 0, filtration: 0}, shape: input.shape}];
      globalThis.quotientGlyph = record => record.shape;
      globalThis.glyphShapeFor = () => 'dot';
      window.HFPSSCellLayout = {packInstances(records, cell, options) {
        calls.push({cell, options, count: records.length}); return records;
      }};
      return packedClassInstances({settings: {}}, {}, {cell: 28}).length;
    })()""", shape=shape)
    assert result["result"] == 1
    assert result["calls"] == [{"cell": 28, "count": 1, "options": {
        "baseYOffset": 0.16, "uniformSize": True, "glyphEnvelope": envelope,
    }}]
