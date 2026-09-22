"""An unresolved nonzero unit is visible, never presented as coefficient 1."""
from pathlib import Path
from xml.etree import ElementTree

import pytest

from test_chart_display_conventions import app_helper


@pytest.mark.parametrize("frobenius,ratio,latex", [
    (0, 1, r"\lambda_{17}"), (1, 1, r"(\lambda_{17})^2"),
    (0, 2, r"\zeta\lambda_{17}"), (1, 3, r"\zeta^{2}(\lambda_{17})^2"),
])
def test_unknown_unit_midpoint_label_tracks_atlas_basis_without_assigning_it(frobenius, ratio, latex):
    result = app_helper(["escapeHtml", "f4DisplayMultiply", "f4DisplayLatex",
                         "differentialDisplayCoefficient", "differentialCoefficientMarkup"], r"""(() => {
      const diff = {id:'d17', proposition_id:'claim'}, parameter = {
        id:'mixed_d17_VD3', symbol:String.raw`\lambda_{17}`, value:null,
        domain:[1,2,3], frobenius_power:input.frobenius};
      const ws = {propositions:[{id:'claim', conclusion:{coefficient_parameter:parameter,
        atlas_display_coefficient:{resolved:false,basis_ratio:input.ratio}}}]};
      const algebra = {coefficientState:() => ({resolved:false,reason:'coefficient parameter is unresolved'}),
        unitInvariant:() => true};
      const before = JSON.stringify(ws);
      return {markup:differentialCoefficientMarkup(ws,{diff},algebra,{x:10,y:20},{x:30,y:60}),
        coefficient:differentialDisplayCoefficient(ws,diff,algebra),
        unchanged:before===JSON.stringify(ws)};
    })()""", frobenius=frobenius, ratio=ratio)["result"]
    assert result["unchanged"]
    assert result["coefficient"]["value"] is None
    assert result["coefficient"]["nonzeroUnit"] and result["coefficient"]["latex"] == latex
    host = ElementTree.fromstring(result["markup"])
    assert host.attrib["data-coefficient"] == "nonzero-unit"
    assert (host.attrib["x"], host.attrib["y"]) == ("20", "40")
    div = host.find(".//{*}div")
    assert div.attrib["data-latex"] == latex and "exact value is unassigned" in div.attrib["title"]


def test_no_unit_certificate_leaves_an_unknown_scalar_unknown():
    result = app_helper(["f4DisplayMultiply", "f4DisplayLatex", "differentialDisplayCoefficient"], r"""(() => {
      const diff={id:'x',proposition_id:'p'}, ws={propositions:[{id:'p',conclusion:{
        coefficient_parameter:{symbol:String.raw`\lambda`,value:null}}}]};
      return differentialDisplayCoefficient(ws,diff,{
        coefficientState:()=>({resolved:false}),unitInvariant:()=>false});
    })()""")["result"]
    assert result is None


def test_unit_invariant_arrow_is_not_downgraded_to_a_conditional_candidate():
    result = app_helper(["differentialRenderTitle"], r"""differentialRenderTitle({
      unitInvariant:true,candidate:{conditional:true},renderAliases:[{
        id:'d17',label:'finite d17',status:'verified',sourceRefs:[]}]
    })""")["result"]
    assert "Verified nonzero rank-one map" in result
    assert "Conditional candidate" not in result
    root = Path(__file__).resolve().parents[1]
    source = (root / "backend/static/app.js").read_text(encoding="utf-8")
    assert "candidate?.conditional && !unitInvariant" in source
    assert (root / "backend/static/app.js").read_bytes() == (root / "public/static/app.js").read_bytes()
