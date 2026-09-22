"""Chart highlight rules preserve the geometry used by the cell packer."""
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "backend/static/style.css"


@pytest.fixture(scope="module")
def rules():
    source = re.sub(r"/\*.*?\*/", "", STYLES.read_text(encoding="utf-8"), flags=re.S)
    result = []
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", source):
        declarations = dict(part.strip().split(":", 1) for part in body.split(";") if ":" in part)
        declarations = {key.strip(): value.strip() for key, value in declarations.items()}
        for selector in selectors.split(","):
            result.append((selector.strip(), declarations))
    return result


def cascade(rules, selectors):
    """Resolve the explicitly matched chart selectors in specificity/source order."""
    matched = [(selector.count(".") + selector.count(":"), index, declarations)
               for index, (selector, declarations) in enumerate(rules) if selector in selectors]
    result = {}
    for _, _, declarations in sorted(matched):
        result.update(declarations)
    return result


@pytest.mark.parametrize("shape", ["dot-glyph", "circle", "square", "fat-dot", "j-series",
                                    "j-positive-series", "witt-j-series", "finite-two-tower", "unknown-glyph"])
@pytest.mark.parametrize("interaction", ["selected", "hover", "focus"])
@pytest.mark.parametrize("periodic", [False, True])
def test_highlight_changes_color_but_not_glyph_geometry(rules, shape, interaction, periodic):
    selectors = {".class-point", ".class-point.unknown", f".class-point.{shape}"}
    if periodic:
        selectors.add(".class-point.periodic")
    before = cascade(rules, selectors)
    active = ".class-point.selected" if interaction == "selected" else f".class-instance:{interaction} .class-point"
    highlighted = selectors | {active}
    if interaction == "selected":
        highlighted.add(".selected")  # Detect a generic rule enlarging the glyph again.
    after = cascade(rules, highlighted)
    assert after["--point-color"] == "var(--blue)"
    assert after["color"] == "var(--point-color)"
    assert after.get("transform", "none") == "none"
    for property_name in ("stroke", "stroke-width", "fill", "r", "width", "height", "scale"):
        assert after.get(property_name) == before.get(property_name)


def test_finite_tower_children_inherit_highlight_and_keep_their_small_strokes(rules):
    line = cascade(rules, {".finite-two-tower line"})
    circle = cascade(rules, {".finite-two-tower circle"})
    assert line["stroke"] == "currentColor"
    assert circle["fill"] == "currentColor"
    assert "color" not in line and "color" not in circle
    assert line["stroke-width"] == "1"
    assert circle["stroke-width"] == "0.6"
    assert circle["stroke"] == "white"


@pytest.mark.parametrize("shape", ["dot-glyph", "circle", "square", "fat-dot", "j-series",
                                    "j-positive-series", "witt-j-series", "finite-two-tower", "unknown-glyph"])
def test_periodic_copy_keeps_its_anchor_stroke_width(rules, shape):
    selectors = {".class-point", f".class-point.{shape}"}
    anchor = cascade(rules, selectors)
    periodic = cascade(rules, selectors | {".class-point.periodic"})
    assert periodic["stroke-width"] == anchor["stroke-width"]


@pytest.mark.parametrize("interaction", [None, ".class-point.selected",
                                       ".class-instance:hover .class-point", ".class-instance:focus .class-point"])
def test_ordinary_and_finite_level_dots_share_the_same_white_stroke(rules, interaction):
    selectors = {".class-point", ".class-point.dot-glyph"} | ({interaction} if interaction else set())
    anchor = cascade(rules, selectors)
    periodic = cascade(rules, selectors | {".class-point.periodic"})
    finite = cascade(rules, {".finite-two-tower circle"})
    assert anchor["stroke-width"] == periodic["stroke-width"] == finite["stroke-width"] == "0.6"
    assert anchor["stroke"] == periodic["stroke"] == "#ffffff"
    assert finite["stroke"] == "white"


@pytest.mark.parametrize("selector", [".class-point.j-positive-series .series-hole",
                                       ".class-point.witt-j-series .series-inner"])
def test_hollow_series_marks_keep_their_semantic_white_centers(rules, selector):
    style = cascade(rules, {selector})
    assert style["fill"] == "white"
    assert style["stroke"] == "var(--point-color)"
    assert "--point-color" not in style


def test_public_selection_styles_match_backend():
    assert STYLES.read_bytes() == (ROOT / "public/static/style.css").read_bytes()
