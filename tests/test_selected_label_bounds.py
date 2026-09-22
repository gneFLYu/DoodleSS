"""Keep complete selected occurrence labels inside the SVG viewport."""
from pathlib import Path
from xml.etree import ElementTree

import pytest

from test_chart_display_conventions import LABEL_HELPERS, app_helper


def fitted_label(width=875, height=400, x=855, y=220, label_width=140,
                 label_height=38, next_width=None, next_height=None):
    return app_helper(["fitClassLabelsToViewport"], r"""(() => {
      const measurements = [];
      const label = {style: {transform: 'scale(0.1)'}, textContent: 'k^3 h1 D^-5 (205, 13)',
        get offsetWidth() {measurements.push(this.style.transform); return input.label_width;},
        get offsetHeight() {return input.label_height;},
        getBoundingClientRect() {throw Error('Screen pixels are not SVG layout units');}};
      const point = {cx: input.x, cy: input.y, r: 3.5};
      const attrs = {}, dataset = {labelPointX: String(input.x), labelPointY: String(input.y), labelGap: '13'};
      const host = {dataset, querySelector: () => label,
        setAttribute: (name, value) => attrs[name] = Number(value)};
      const svg = {querySelectorAll(selector) {
        if (selector !== '.label-host[data-label-point-x]') throw Error('Unexpected glyph selection');
        return [host];
      }};
      const original = JSON.stringify({point, dataset, text: label.textContent});
      const snapshot = () => ({attrs: {...attrs}, style: {...label.style}});
      fitClassLabelsToViewport(svg, {width: input.width, height: input.height});
      const first = snapshot();
      fitClassLabelsToViewport(svg, {width: input.width, height: input.height});
      const repeated = snapshot();
      if (input.next_width !== null) fitClassLabelsToViewport(svg, {
        width: input.next_width, height: input.next_height});
      return {first, repeated, final: snapshot(), measurements,
        unchanged: original === JSON.stringify({point, dataset, text: label.textContent})};
    })()""", width=width, height=height, x=x, y=y, label_width=label_width,
                      label_height=label_height, next_width=next_width,
                      next_height=next_height)["result"]


def test_right_edge_label_sits_immediately_left_of_its_point_using_typeset_width():
    result = fitted_label()
    assert result["first"]["attrs"] == {"x": 855 - 13 - 140, "y": 210,
                                        "width": 140, "height": 38}
    assert result["first"]["style"]["transform"] == ""
    assert result["unchanged"] is True


def test_room_on_right_keeps_the_label_next_to_the_point():
    result = fitted_label(x=100)
    assert result["first"]["attrs"]["x"] == 113


@pytest.mark.parametrize("width,height,x,y,label_width,label_height", [
    (875, 400, 855, 0, 140, 38),
    (875, 400, 855, 400, 140, 38),
    (875, 400, 0, 220, 140, 38),
    (875, 400, -2, 220, 140, 38),
    (875, 400, 878, 220, 140, 38),
    (120, 100, 110, 90, 280, 38),
    (120, 100, 0, 0, 280, 38),
    (25, 20, 12, 10, 280, 38),
    (875, 20, 855, 18, 140, 38),
    (2, 2, 1, 1, 140, 38),
])
def test_whole_name_and_bidegree_fit_all_edges_and_narrow_viewports(
        width, height, x, y, label_width, label_height):
    result = fitted_label(width, height, x, y, label_width, label_height)
    attrs = result["first"]["attrs"]
    assert attrs["x"] >= 0 and attrs["y"] >= 0
    assert attrs["x"] + attrs["width"] <= width + 1e-9
    assert attrs["y"] + attrs["height"] <= height + 1e-9
    assert attrs["width"] / label_width == pytest.approx(attrs["height"] / label_height)
    assert result["first"] == result["repeated"]
    assert all(transform == "" for transform in result["measurements"])
    assert result["unchanged"] is True


def test_resize_restores_unscaled_label_without_cumulative_shrinking():
    result = fitted_label(width=120, height=100, x=100, y=50, label_width=280,
                          next_width=875, next_height=400)
    assert result["first"]["style"]["transform"].startswith("scale(")
    assert result["final"]["style"]["transform"] == ""
    assert result["final"]["attrs"] == {"x": 113, "y": 40, "width": 280, "height": 38}
    assert result["unchanged"] is True


@pytest.mark.parametrize("horizontal,stem,exponent", [(2, 205, 27), (-2, -51, -5)])
def test_bounded_label_retains_actual_periodic_name_grade_and_selection(horizontal, stem, exponent):
    result = app_helper(LABEL_HELPERS, r"""(() => {
      globalThis.workspace = () => ({page: 9});
      globalThis.state = {workspaceId: 'ws', selectedClassId: 'family',
        selectedOccurrence: {workspaceId: 'ws', page: 9, classId: 'family', instanceKey: 'chosen'}};
      const record = {item: {id: 'family', label: String.raw`h_1D^2u_{\sigma_i}`, style: {}},
        periodic: true, horizontalStem: 64, horizontalExponent: input.horizontal, verticalExponent: 3,
        grade: {stem: input.stem, filtration: 13}, instanceKey: 'chosen'};
      const before = JSON.stringify({state, record});
      const point = {x: 855, y: 399}, metrics = {width: 875, height: 400, cell: 28};
      const visible = {stemMin: -100, stemMax: 300, filtrationMin: 0, filtrationMax: 20};
      return {markup: classLabelMarkup(record, point, metrics, visible),
        sibling: classLabelMarkup({...record, instanceKey: 'sibling'}, point, metrics, visible),
        outside: classLabelMarkup(record, point, metrics, {...visible, filtrationMax: 12}),
        unchanged: before === JSON.stringify({state, record})};
    })()""", horizontal=horizontal, stem=stem)["result"]
    label = ElementTree.fromstring(result["markup"])
    assert label.attrib["data-label-point-x"] == "855"
    assert label.attrib["data-label-point-y"] == "399"
    assert label.find(".//{*}span").attrib["data-latex"] == rf"k^{{3}}h_1D^{{{exponent}}}u_{{\sigma_i}}"
    assert label.find(".//{*}small").text == f"({stem}, 13)"
    assert result["sibling"] == result["outside"] == ""
    assert result["unchanged"] is True


def test_chart_fits_labels_after_safe_katex_typesetting_and_static_mirror_matches():
    result = app_helper(["renderMathInChart"], r"""(() => {
      const svg = {querySelectorAll: () => [{dataset: {latex: 'h_1D'}}]};
      globalThis.$ = () => svg;
      window.katex = globalThis.katex = {render(latex, node, options) {
        calls.push({action: 'typeset', latex, options});
      }};
      globalThis.fitClassLabelsToViewport = (chart, metrics) => {
        calls.push({action: 'fit', sameChart: chart === svg, metrics});
      };
      renderMathInChart({width: 875, height: 400});
      return true;
    })()""")
    assert [call["action"] for call in result["calls"]] == ["typeset", "fit"]
    assert result["calls"][0]["options"]["trust"] is False
    assert result["calls"][1] == {"action": "fit", "sameChart": True,
                                    "metrics": {"width": 875, "height": 400}}
    root = Path(__file__).resolve().parents[1]
    assert (root / "backend/static/app.js").read_bytes() == (root / "public/static/app.js").read_bytes()
