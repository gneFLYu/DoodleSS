"""Selected period copies keep exact products and current model labels."""
from pathlib import Path

import pytest

from test_chart_display_conventions import app_helper, run_node


HELPERS = ["latexPower", "shiftPeriodFactor", "shiftDExponent", "shiftKExponent",
           "f4DisplayMultiply", "f4DisplayLatex", "periodicDisplayLabel"]


@pytest.mark.parametrize("label,symbol,delta,expected", [
    ("xD+yD", "D", 8, r"D^{8}\left(xD+yD\right)"),
    ("xk+yk", "k", 3, r"k^{3}\left(xk+yk\right)"),
    (r"(x^2+y^2)D^2u_{\sigma_i}", "D", 8, r"(x^2+y^2)D^{10}u_{\sigma_i}"),
    (r"\{x^2+y^2\}D^2u_{\sigma_i}", "D", -3, r"\{x^2+y^2\}D^{-1}u_{\sigma_i}"),
    (r"D^2h_1D^{-3}", "D", 8, r"D^{7}h_1"),
    (r"k^2h_1k", "k", 3, r"k^{6}h_1"),
    (r"x^{-2}D^{-3}", "D", 8, r"x^{-2}D^{5}"),
    (r"x^-2D^-3", "D", 8, r"x^-2D^{5}"),
    (r"h_1D^2u_{\sigma_k}", "k", 2, r"k^{2}h_1D^2u_{\sigma_k}"),
    (r"\Delta u_{\sigma_i}", "D", 8, r"\Delta D^{8}u_{\sigma_i}"),
    (r"D^{n}u_{\sigma_i}", "D", 8, r"D^{n}D^{8}u_{\sigma_i}"),
    ("0", "D", 8, "0"), ("1", "D", -8, r"D^{-8}"),
    ("D", "D", -1, "1"), ("k", "k", -1, "1"),
    (r"h_1D^{-1}", "D", 1, "h_1"),
    (r"2h_2", "k", 3, r"2k^{3}h_2"),
    ("4", "k", 2, r"4k^{2}"),
])
def test_period_factor_is_applied_to_the_whole_expression(label, symbol, delta, expected):
    result = app_helper(HELPERS, "shiftPeriodFactor(input.label, input.symbol, input.delta)",
                        label=label, symbol=symbol, delta=delta)
    assert result["result"] == expected


def test_two_periods_preserve_a_sum_and_transport_its_common_unit():
    result = app_helper(HELPERS, r"""(() => {
      const record = {periodic: true, horizontalStem: 64, horizontalExponent: -1,
        verticalExponent: 3, item: {label: 'old', style: {
          atlas_display_basis: {status: 'exact', expression: 'xD+yD', unit: 3},
          atlas_transport: {omega_power: 2}}}};
      const before = JSON.stringify(record);
      return {label: periodicDisplayLabel(record), unchanged: before === JSON.stringify(record)};
    })()""")["result"]
    assert result == {"label": r"k^{3}D\left(xD+yD\right)", "unchanged": True}


@pytest.mark.parametrize("change", ["rename", "boundary", "workspace", "page", "selection"])
def test_refresh_rebuilds_or_discards_the_actual_selected_occurrence(change):
    result = app_helper(HELPERS + ["refreshSelectedOccurrence"], r"""(() => {
      const ws = {id: 'ws', page: 9};
      globalThis.workspace = () => ws;
      globalThis.state = {selectedClassId: 'family', selectedOccurrence: {
        workspaceId: 'ws', page: 9, classId: 'family', instanceKey: 'old-key',
        grade: {stem: 205, filtration: 13}, label: 'old name'}};
      const current = {item: {id: 'family', label: 'h_2D^2'},
        periodic: true, horizontalStem: 64, horizontalExponent: 2, verticalExponent: 3,
        instanceKey: 'current-key', grade: {stem: 205, filtration: 13}};
      globalThis.periodicClassInstances = (workspace, bounds) => {
        calls.push(bounds); return input.change === 'boundary' ? [] : [current];
      };
      if (input.change === 'workspace') ws.id = 'other';
      if (input.change === 'page') ws.page = 11;
      if (input.change === 'selection') state.selectedClassId = null;
      const before = JSON.stringify(current);
      refreshSelectedOccurrence();
      return {selected: state.selectedOccurrence, family: state.selectedClassId,
        unchanged: before === JSON.stringify(current)};
    })()""", change=change)
    assert result["result"]["unchanged"] is True
    if change == "rename":
        assert result["result"]["selected"]["label"] == r"k^{3}h_2D^{27}"
        assert result["result"]["selected"]["grade"] == {"stem": 205, "filtration": 13}
        assert result["result"]["selected"]["instanceKey"] == "current-key"
        assert result["result"]["family"] == "family"
    else:
        assert result["result"]["selected"] is None
    assert result["calls"] == ([{"stemMin": 205, "stemMax": 205,
                                  "filtrationMin": 13, "filtrationMax": 13}]
                                if change in {"rename", "boundary"} else [])


def test_project_refresh_updates_selection_before_render_and_mirrors_are_equal():
    root = Path(__file__).resolve().parents[1]
    source = (root / "backend/static/app.js").read_text(encoding="utf-8")
    load = source.split("async function loadProject() {", 1)[1].split("\nfunction ", 1)[0]
    assert load.index("refreshSelectedOccurrence();") < load.index("render();")
    assert (root / "backend/static/app.js").read_bytes() == (root / "public/static/app.js").read_bytes()


def test_periodic_and_quotient_selections_are_exclusive_and_keep_actual_grades():
    root = Path(__file__).resolve().parents[1]
    result = run_node(r"""
const fs = require('node:fs'), vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const source = fs.readFileSync(input.path, 'utf8');
function extract(name) {
  let start = source.indexOf(`function ${name}(`);
  if (start < 0) throw Error(`Missing production helper: ${name}`);
  if (source.slice(start - 6, start) === 'async ') start -= 6;
  const next = /\n(?:async )?function\s/.exec(source.slice(start + 1));
  return source.slice(start, next ? start + 1 + next.index : source.length);
}
const context = vm.createContext({window: {}, atlasSector: () => null,
  document: {createElement() {return {textContent: '', get innerHTML() {
    return String(this.textContent).replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  }};}}});
vm.runInContext(input.functions.map(extract).join('\n'), context);
(async () => {
  const result = await vm.runInContext(`(async () => {
    const node = {id: 'family', label: 'h_1D^2', page: 2,
      grade: {stem: 17, filtration: 1}, style: {}};
    const ws = {id: 'ws', page: 9, classes: [node]};
    globalThis.workspace = () => ws;
    globalThis.state = {workspaceId: 'ws', tool: 'inspect', selectedClassId: null,
      selectedOccurrence: null, selectedQuotientInstance: null,
      connectionStart: null, candidateResults: null, periodicityPreview: null};
    const inspector = [];
    globalThis.renderFateInspector = () => inspector.push({family: state.selectedClassId,
      grade: state.selectedOccurrence?.grade || null});
    globalThis.renderPersistentPeriodicityTool = () => {};
    globalThis.renderChart = () => {};
    globalThis.toast = () => {};
    globalThis.fateFor = () => null;
    globalThis.readOnlyCatalog = () => false;
    const anchor = {item: node, grade: node.grade, periodic: false, instanceKey: 'anchor'};
    const positive = {...anchor, periodic: true, horizontalStem: 64,
      horizontalExponent: 2, verticalExponent: 3,
      grade: {stem: 205, filtration: 13}, instanceKey: 'positive'};
    const negative = {...positive, horizontalExponent: -2,
      grade: {stem: -51, filtration: 13}, instanceKey: 'negative'};
    const quotient = {item: {id: 'computed', label: 'X+Y', style: {}},
      readOnlyRepresentative: true, periodic: false, instanceKey: 'quotient',
      grade: {stem: 206, filtration: 14}};
    const records = {anchor, positive, negative, quotient};
    const before = JSON.stringify({ws, records});
    const bounds = {stemMin: -100, stemMax: 300, filtrationMin: 0, filtrationMax: 20};
    const snapshot = () => ({family: state.selectedClassId,
      occurrence: state.selectedOccurrence, quotient: state.selectedQuotientInstance,
      labels: Object.fromEntries(Object.entries(records).map(([name, record]) =>
        [name, classLabelMarkup(record, {x: 50, y: 40}, {cell: 28}, bounds)]))});
    await onClassClick(node.id, positive);
    const first = snapshot();
    inspectQuotientRepresentative(quotient);
    const middle = snapshot();
    await onClassClick(node.id, negative);
    const last = snapshot();
    return {first, middle, last, inspector, unchanged: before === JSON.stringify({ws, records})};
  })()`, context);
  process.stdout.write(JSON.stringify(result));
})().catch(error => { console.error(error); process.exitCode = 1; });
""", {"path": str(root / "backend/static/app.js"), "functions": [
        *HELPERS, "escapeHtml", "gradeText", "inBounds", "classLabelMarkup",
        "inspectQuotientRepresentative", "onClassClick",
    ]})

    assert result["unchanged"] is True
    for name, selected, grade, label in (
        ("first", "positive", {"stem": 205, "filtration": 13}, r"k^{3}h_1D^{27}"),
        ("last", "negative", {"stem": -51, "filtration": 13}, r"k^{3}h_1D^{-5}"),
    ):
        row = result[name]
        assert row["family"] == "family" and row["quotient"] is None
        assert row["occurrence"]["instanceKey"] == selected
        assert row["occurrence"]["grade"] == grade
        assert row["occurrence"]["label"] == label
        assert [key for key, markup in row["labels"].items() if markup] == [selected]
        assert f'data-latex="{label}"' in row["labels"][selected]
        assert f'({grade["stem"]}, {grade["filtration"]})</small>' in row["labels"][selected]

    middle = result["middle"]
    assert middle["family"] is None and middle["occurrence"] is None
    assert middle["quotient"] == "quotient"
    assert [key for key, markup in middle["labels"].items() if markup] == ["quotient"]
    assert 'data-latex="X+Y"' in middle["labels"]["quotient"]
    assert '(206, 14)</small>' in middle["labels"]["quotient"]
    assert result["inspector"] == [
        {"family": "family", "grade": {"stem": 205, "filtration": 13}},
        {"family": None, "grade": None},
        {"family": "family", "grade": {"stem": -51, "filtration": 13}},
    ]
