"""Candidate provenance must not masquerade as an assigned F4 coefficient."""
from pathlib import Path

from test_chart_display_conventions import app_helper


def test_conditional_tooltip_lists_possible_values_without_an_assignment():
    result = app_helper(["f4DisplayLatex", "differentialRenderTitle"], r"""(() => {
      const item = {renderAliases: [{id:'d23',label:'historical row',status:'review',sourceRefs:['table']}],
        candidate: {conditional:true,variants:[{coefficient:{value:2}},{coefficient:{value:3}}]}};
      const before=JSON.stringify(item);
      return {title:differentialRenderTitle(item),unchanged:before===JSON.stringify(item)};
    })()""")["result"]
    assert result["unchanged"]
    assert "Source row: d23" in result["title"] and "review" in result["title"]
    assert r"surviving coefficient values \zeta, \zeta^{2}" in result["title"]
    assert "no parameter has been assigned" in result["title"]


def test_candidate_summary_distinguishes_contradictions_from_missing_ports():
    result = app_helper(["differentialCandidateSummary"], """differentialCandidateSummary([
      {id:'row',status:'contradicted'}, {id:'row',status:'contradicted'},
      {id:'other',status:'absent'}, {id:'pending',status:'unknown'}])""")["result"]
    assert "1 candidate family has occurrences excluded" in result
    assert "sources and historical records are retained" in result
    assert "1 candidate family has unresolved" in result
    assert "coefficient-1 substitution" in result
    assert "2 candidate" not in result
    assert app_helper(["differentialCandidateSummary"],
                      "differentialCandidateSummary([{id:'boundary',status:'absent'}])")["result"] == ""


def test_renderer_collects_provenance_and_uses_a_surviving_conditional_endpoint():
    root = Path(__file__).resolve().parents[1]
    source = (root / "backend/static/app.js").read_text(encoding="utf-8")
    assert "candidate = algebra.candidateState(diff, sourceGrade, targetGrade)" in source
    assert "targetNode: pair?.target || target" in source
    assert "periodicDifferentials(ws, buffered, candidateDiagnostics)" in source
    assert "differentialCandidateSummary(candidateDiagnostics)" in source
    assert (root / "backend/static/app.js").read_bytes() == (root / "public/static/app.js").read_bytes()
