"""Canonical Q8 display names do not infer residue-field or torsion relations."""
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def run(expression):
    result = subprocess.run(
        ["node", "-e", "const D=require('./backend/static/display-basis.js');"
         "console.log(JSON.stringify(" + expression + "));"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True, timeout=10,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("label,expected", [
    (r"(h_1 D^{-2}) D^3", "h_1D"),
    (r"\left(h_1 D^{-2}\right) D^3", "h_1D"),
    (r"h_1D^{-2}D^{3}D^{-1}", "h_1"),
    (r"D^2k^3v_1^4h_2h_1(x+y)u_{\sigma_i+\sigma_j}",
     r"\{x+y\}h_1h_2v_1^{4}k^{3}D^{2}u_{\sigma_i+\sigma_j}"),
    (r"(xh_1v_1+yh_2)kD", r"\{xh_1v_1+yh_2\}kD"),
    (r"k\{yh_2+h_1^2\}Du_{3\sigma_i}", r"\{yh_2+h_1^{2}\}kDu_{3\sigma_i}"),
    (r"h_{2}kD^3h_{1}v_{1}^4", r"h_1h_2v_1^{4}kD^{3}"),
    (r"2(x+y)D", r"2\{x+y\}D"),
    (r"(4D)k^2v_1^2", r"4v_1^{2}k^{2}D"),
    (r"2\zeta D^3D^{-2}", r"2\zeta\,D"),
    (r"\zeta^{2}\zeta^2kD", r"\zeta\,kD"),
    (r"{\zeta}2D", r"2\zeta\,D"),
    (r"\zeta^3D", "D"),
    (r"-D+D", "0"),
    (r"x+x", "2x"),
    (r"2D+2D", "4D"),
    (r"(x+y)^2", r"\{x^{2}+2xy+y^{2}\}"),
    (r"\zeta(x+y)", r"\zeta\{x+y\}"),
    (r"\zeta+\zeta^2", r"\{\zeta+\zeta^{2}\}"),
])
def test_normalize_label_is_context_safe_and_canonical(label, expected):
    result = run("D.normalizeLabel(" + json.dumps(label) + ")")
    assert result == {"supported": True, "label": expected}
    assert run("D.normalizeLabel(" + json.dumps(expected) + ")") == result


@pytest.mark.parametrize("label,symbol,delta,expected", [
    (r"(h_1D^{-2})", "D", 3, "h_1D"),
    (r"(xh_1v_1+yh_2)D^{-2}", "D", 3, r"\{xh_1v_1+yh_2\}D"),
    (r"2v_1^2D^{-3}u_{3\sigma_i}", "k", 3, r"2v_1^{2}k^{3}D^{-3}u_{3\sigma_i}"),
    (r"h_1k^3D", "k", -3, "h_1D"),
    ("0", "D", 3, "0"),
    ("1", "D", -3, r"D^{-3}"),
])
def test_period_shift_collects_powers_inside_products_and_sums(label, symbol, delta, expected):
    assert run("D.shiftPeriodFactor(" + ",".join(map(json.dumps, [label, symbol, delta])) + ")") == {
        "supported": True, "label": expected,
    }


@pytest.mark.parametrize("label", [
    r"\omega(x)", r"\psi(x)", r"\frac{x}{y}", r"h_1^{-1}", r"x^{1/2}",
    r"x+", r"\htmlClass{bad}{x}", "*x", "x*", "x=y", "D^{257}",
    "9007199254740992D", r"u_{\unknown}", r"\zetax",
])
def test_unknown_or_unbounded_syntax_has_explicit_fallback(label):
    result = run("D.normalizeLabel(" + json.dumps(label) + ")")
    assert not result["supported"] and result["label"] is None and result["reason"]


def test_normalization_does_not_assume_g_inverse_or_f4_coefficients():
    assert not run("D.shiftPeriodFactor('h_1D','k',-1)")["supported"]
    assert run("D.normalizeLabel('x+x')")["label"] == "2x"
    assert run("D.combineLabels([{coefficient:1,label:'x+x'}],{coefficientContext:'F4'})")["label"] == "0"
    assert not run("D.combineLabels([{coefficient:1,label:'2D'}],{coefficientContext:'F4'})")["supported"]


def test_f4_base_change_is_collected_then_braced_and_ordered():
    terms = [{"coefficient": 1, "label": r"(xh_1v_1+yh_2)Dk"},
             {"coefficient": 1, "label": r"(xh_1v_1+h_1^2)Dk"}]
    result = run("D.combineLabels(" + json.dumps(terms) + ",{coefficientContext:'F4'})")
    assert result["label"] == r"\{yh_2+h_1^{2}\}kD"


def test_browser_module_mirror_is_identical():
    assert (ROOT / "backend/static/display-basis.js").read_bytes() == (ROOT / "public/static/display-basis.js").read_bytes()
