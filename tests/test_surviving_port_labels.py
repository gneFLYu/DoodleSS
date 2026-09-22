"""Finite surviving multiples are named consistently without changing page algebra."""
from pathlib import Path

import pytest

from test_chart_display_conventions import app_helper
from test_selected_occurrence_refresh import HELPERS


@pytest.mark.parametrize("label,two,ports,expected", [
    ("v_1^2", 0, ["0:0", "1:0", "0:1"], "v_1^2"),  # Before the d3 quotient.
    ("v_1^2", 0, ["1:0"], "2v_1^2"),
    ("2v_1^2", 1, ["1:0"], "2v_1^2"),
    ("D", 0, ["2:0"], "4D"),
    ("2D", 1, ["2:0"], "4D"),
    ("4D", 2, ["2:0"], "4D"),
    ("D", 0, ["0:0"], "D"),
    ("D", 0, ["1:0", "2:0"], "D"),  # A tower is not a single finite port.
    ("D", 0, ["3:0"], "D"),  # The compressed free Witt tail is not finite.
    ("D", 0, ["0:1"], "D"),
    ("D", 0, ["1:1"], "D"),
    ("D", 0, ["1:0", "0:1"], "D"),
    ("D", 0, [], "D"),
    ("D", 0, None, "D"),
    ("0", 0, ["1:0"], "0"),
    ("1", 0, ["1:0"], "2"),
    ("-D", 0, ["1:0"], "-2D"),
    (r"D^{-2}", 0, ["1:0"], r"2D^{-2}"),
    ("x+y", 0, ["1:0"], r"2\left(x+y\right)"),
    (r"{\zeta}2D", 1, ["2:0"], r"4{\zeta}D"),
    (r"{\zeta^{2}}D", 0, ["1:0"], r"2{\zeta^{2}}D"),
    (r"\zeta^2D", 0, ["1:0"], r"2\zeta^2D"),
])
def test_single_finite_port_uses_actual_witt_multiple(label, two, ports, expected):
    row = app_helper(HELPERS, """(() => {
      const record = {item: {label: input.label, style: {e2_pattern: 'S40', two_valuation: input.two}},
        periodic: false, modulePorts: input.ports};
      const before = JSON.stringify(record);
      return {label: periodicDisplayLabel(record), unchanged: before === JSON.stringify(record)};
    })()""", label=label, two=two, ports=ports)["result"]
    assert row == {"label": expected, "unchanged": True}


@pytest.mark.parametrize("guard", ["readOnlyRepresentative", "uncertain", "no-pattern"])
def test_computed_or_unresolved_representatives_are_not_rescaled(guard):
    row = app_helper(HELPERS, """(() => {
      const record = {item: {label: '2D', style: {e2_pattern: 'I00'}}, modulePorts: ['2:0']};
      if (input.guard === 'no-pattern') delete record.item.style.e2_pattern;
      else record[input.guard] = true;
      return periodicDisplayLabel(record);
    })()""", guard=guard)["result"]
    assert row == "2D"


@pytest.mark.parametrize("horizontal,expected", [(0, r"2k^{3}v_1^2D^{6}u_{3\sigma_i}"),
                                               (-1, r"2k^{3}v_1^2D^{-2}u_{3\sigma_i}")])
def test_periodic_copy_combines_actual_two_k_and_d_powers(horizontal, expected):
    row = app_helper(HELPERS, r"""periodicDisplayLabel({
      item: {label: 'v_1^2D^{-3}u_{3\\sigma_i}', style: {e2_pattern: 'S40'}},
      periodic: true, verticalExponent: 3, horizontalStem: 64,
      horizontalExponent: input.horizontal, modulePorts: ['1:0']
    })""", horizontal=horizontal)["result"]
    assert row == expected


def test_transported_unit_is_distinct_from_the_witt_two_multiple():
    row = app_helper(HELPERS, r"""periodicDisplayLabel({
      item: {label: 'old', style: {e2_pattern: 'S40', two_valuation: 1,
        atlas_display_basis: {status: 'exact', expression: '2v_1^2D^{-3}', unit: 2},
        atlas_transport: {omega_power: 1}}},
      periodic: true, verticalExponent: 3, horizontalStem: 64,
      horizontalExponent: 0, modulePorts: ['2:0']
    })""")["result"]
    assert row == r"4{\zeta}k^{3}v_1^2D^{6}"


@pytest.mark.parametrize("alias_first", [False, True])
def test_display_slot_deduplication_does_not_change_the_surviving_name(alias_first):
    row = app_helper(HELPERS + ["periodicClassInstances"], r"""(() => {
      const base = {id: 'base', label: 'v_1^2D^{-3}u_{3\\sigma_i}',
        grade: {stem: -20, filtration: 0}, style: {e2_pattern: 'S40'}};
      const alias = {id: 'alias', label: '2k^{3}v_1^2D^{6}u_{3\\sigma_i}',
        grade: {stem: 40, filtration: 12}, style: {e2_pattern: 'S40', two_valuation: 1}};
      const ws = {id: 'ws', page: 9, classes: input.alias_first ? [alias, base] : [base, alias]};
      const finite = new Set(['1:0']);
      globalThis.pageAlgebra = () => ({ports: () => finite, displaySlots: () => ['S40:40:12'], representatives: () => []});
      globalThis.liveClassesAt = () => ws.classes;
      globalThis.periodsForClassOnPage = () => [];
      globalThis.latticeCopies = (grade) => [{grade: {stem: 40, filtration: 12},
        periodic: grade.filtration === 0, verticalExponent: grade.filtration === 0 ? 3 : 0}];
      globalThis.inBounds = () => true;
      globalThis.visualStateFor = () => 'accepted';
      const before = JSON.stringify(ws);
      const records = periodicClassInstances(ws, {});
      return {count: records.length, label: periodicDisplayLabel(records[0]),
        grade: records[0].grade, ports: records[0].modulePorts,
        unchanged: before === JSON.stringify(ws) && [...finite].join() === '1:0'};
    })()""", alias_first=alias_first)["result"]
    assert row == {"count": 1, "label": r"2k^{3}v_1^2D^{6}u_{3\sigma_i}",
                   "grade": {"stem": 40, "filtration": 12}, "ports": ["1:0"], "unchanged": True}


def test_selected_label_and_refresh_use_the_same_surviving_name():
    row = app_helper(HELPERS + ["refreshSelectedOccurrence", "classLabelMarkup", "escapeHtml"], r"""(() => {
      const ws = {id: 'ws', page: 9};
      const record = {item: {id: 'base', label: 'v_1^2D^{-3}u_{3\\sigma_i}', style: {e2_pattern: 'S40'}},
        grade: {stem: 40, filtration: 12}, periodic: true, verticalExponent: 3,
        modulePorts: ['1:0'], instanceKey: 'actual'};
      globalThis.workspace = () => ws;
      globalThis.state = {workspaceId: 'ws', selectedClassId: 'base', selectedOccurrence: {
        workspaceId: 'ws', page: 9, classId: 'base', grade: {...record.grade}, label: 'old'}};
      globalThis.periodicClassInstances = () => [record];
      globalThis.inBounds = () => true;
      refreshSelectedOccurrence();
      return {selected: state.selectedOccurrence,
        markup: classLabelMarkup(record, {x: 30, y: 40}, {cell: 28}, {})};
    })()""")["result"]
    expected = r"2k^{3}v_1^2D^{6}u_{3\sigma_i}"
    assert row["selected"]["label"] == expected
    assert row["selected"]["grade"] == {"stem": 40, "filtration": 12}
    assert f'data-latex="{expected}"' in row["markup"]
    assert '(40, 12)</small>' in row["markup"]


def test_static_mirrors_are_identical():
    root = Path(__file__).resolve().parents[1]
    assert (root / "backend/static/app.js").read_bytes() == (root / "public/static/app.js").read_bytes()
