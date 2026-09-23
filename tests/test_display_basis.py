"""Display changes preserve exact computational coordinates and coefficient contexts."""
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run(body):
    result = subprocess.run(
        ["node", "--max-old-space-size=128", "-e", "const D=require('./backend/static/display-basis.js');"
         "const L=require('./backend/static/graded-quotient.js');" + body],
        cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=True, timeout=10,
    )
    return json.loads(result.stdout)


def test_preferred_target_becomes_one_basis_dot_without_changing_vectors_or_matrices():
    result = run("""
const preferred=[[1,2]], matrix=[[1],[2]], before=JSON.stringify({preferred,matrix});
const b=D.create(2,preferred);
console.log(JSON.stringify({rows:b.rows, target:b.project([1,2]), second:b.project([0,1]),
 lifted:b.lift([1,0]), unchanged:before===JSON.stringify({preferred,matrix}),
 frozen:Object.isFrozen(b.rows)&&b.rows.every(Object.isFrozen)}));
""")
    assert result == {"rows": [[1, 2], [1, 0]], "target": [1, 0], "second": [3, 3],
                      "lifted": [1, 2], "unchanged": True, "frozen": True}


def test_display_basis_is_invertible_for_every_f4_vector_and_keeps_dependent_directions_exact():
    result = run("""
const b=D.create(3,[[1,2,0],[2,3,0],[0,1,1],[0,0,0]]);
const vectors=Array.from({length:64},(_,n)=>[n&3,(n>>2)&3,(n>>4)&3]);
console.log(JSON.stringify({rows:b.rows,roundTrips:vectors.every(v=>JSON.stringify(b.lift(b.project(v)))===JSON.stringify(v)),
 dependent:b.project([2,3,0]),sum:b.project([1,3,1]),dimension:b.dimension}));
""")
    assert result["rows"] == [[1, 2, 0], [0, 1, 1], [1, 0, 0]]
    assert result["roundTrips"]
    assert result["dependent"] == [2, 0, 0]
    assert result["sum"] == [1, 1, 0]
    assert result["dimension"] == 3


@pytest.mark.parametrize("expression", [
    "D.create(-1,[])", "D.create(2,[[1]])", "D.create(2,[[1,true]])",
    "D.create(129,[])", "D.create(2,[[1,'unknown']])", "D.create(2,null)",
])
def test_invalid_display_basis_inputs_are_rejected(expression):
    assert run("let rejected=false;try{" + expression + ";}catch(_){rejected=true;}console.log(JSON.stringify(rejected));")


def combine(terms, context="F4"):
    return run("console.log(JSON.stringify(D.combineLabels("
               + json.dumps(terms) + "," + json.dumps({"coefficientContext": context}) + ")));")


def test_sum_labels_collect_equal_monomials_over_f4():
    result = combine([
        {"coefficient": 1, "label": r"xh_1v_1+yh_2"},
        {"coefficient": 1, "label": r"xh_1v_1+h_1^2"},
    ])
    assert result["supported"] and result["label"] == r"yh_2+h_1^{2}"
    assert len(result["terms"]) == 2


def test_commutative_factor_order_and_f4_weights_are_exact():
    result = combine([
        {"coefficient": 2, "label": r"xh_1v_1"},
        {"coefficient": 3, "label": r"v_1h_{1}x"},
    ])
    assert result["supported"] and result["label"] == r"xh_1v_1"
    assert combine([{"coefficient": 1, "label": r"\zeta^3x+x"}])["label"] == "0"
    assert combine([{"coefficient": 2, "label": r"\zeta^{2}x"}])["label"] == "x"
    assert combine([{"coefficient": 2, "label": "x"}])["label"] == r"\zeta\,x"
    assert combine([{"coefficient": 1, "label": r"\zeta\,x"}])["label"] == r"\zeta\,x"


def test_common_k_d_thom_suffix_survives_sum_collection():
    result = combine([
        {"coefficient": 1, "label": r"(xh_1v_1+yh_2)k^2D^{-3}u_{3\sigma_i}"},
        {"coefficient": 1, "label": r"(xh_1v_1+h_1^2)k^2D^{-3}u_{3\sigma_i}"},
    ])
    assert result["supported"]
    assert result["label"] == r"\left(yh_2+h_1^{2}\right)k^{2}D^{-3}u_{3\sigma_i}"


def test_legacy_escaped_brace_sums_collect_with_their_common_thom_suffix():
    result = combine([
        {"coefficient": 1, "label": r"\{yh_2+xh_1v_1\}kDu_{3\sigma_i}"},
        {"coefficient": 1, "label": r"\{xh_1v_1+h_1^2\}kDu_{3\sigma_i}"},
    ])
    assert result["supported"]
    assert result["label"] == r"\left(yh_2+h_1^{2}\right)kDu_{3\sigma_i}"


def test_parentheses_distribute_and_factor_powers_combine_without_a_rewrite_system():
    assert combine([{"coefficient": 1, "label": r"(x+y)^2"}])["label"] == r"x^{2}+y^{2}"
    assert combine([{"coefficient": 1, "label": r"D^{-2}D^3"}])["label"] == "D"
    # No theorem or generator relation x²+y²=0 is inferred.
    assert combine([{"coefficient": 1, "label": r"x^2+y^2"}])["label"] != "0"


@pytest.mark.parametrize("label", [
    r"2D", r"4D", r"2(x+y)", r"\frac{x}{y}", r"\omega(x)", r"\psi(x)",
    r"x^{1/2}", r"x^{-1}", r"x+", r"\htmlClass{bad}{x}", r"(x+y",
    r"\zetax", r"u_{\htmlClass{bad}}",
    r"\leftarrow x", r"\rightfoo(x)", r"\cdotx",
])
def test_unsupported_and_witt_label_syntax_requests_explicit_fallback(label):
    result = combine([{"coefficient": 1, "label": label}])
    assert result["supported"] is False and result["label"] is None and result["reason"]


@pytest.mark.parametrize("context", [None, "q8-witt-f4", "integers", "formal-integer"])
def test_non_f4_context_never_cancels_a_witt_or_integer_sum(context):
    result = combine([{"coefficient": 1, "label": "x"}, {"coefficient": 1, "label": "x"}], context)
    assert result["supported"] is False and result["label"] is None


def test_module_static_mirror_is_identical():
    assert (ROOT / "backend/static/display-basis.js").read_bytes() == (ROOT / "public/static/display-basis.js").read_bytes()
