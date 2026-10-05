"""Source-review pages must not inherit Q8 HFPSS page/quotient assumptions."""
from pathlib import Path

from test_chart_display_conventions import app_helper


def test_bss_page_one_and_explicit_source_review_cap():
    result = app_helper(["pageMinimum", "pageLimit"], """(() => {
      const bss={spectral_sequence:'2-bss',settings:{page_max:4},differentials:[{page:3}]};
      const q8={spectral_sequence:'hfpss',settings:{},differentials:[]};
      return [pageMinimum(bss),pageLimit(bss),pageMinimum(q8),pageLimit(q8)];
    })()""")["result"]
    assert result == [1, 4, 2, 25]


def test_source_lifetimes_are_inclusive_and_ignore_hfpss_deaths():
    result = app_helper(["liveClassesAt", "visualStateFor"], """(() => {
      const ws={spectral_sequence:'2-bss',settings:{source_reference:true},classes:[
        {id:'a',page:1,style:{last_page:2,bockstein_filtration:0}},
        {id:'b',page:1,style:{bockstein_filtration:3}},
        {id:'c',page:3,style:{}}],fates:[{class_id:'b',first_hfpss_death:{page:1}}]};
      return [liveClassesAt(ws,1).map(x=>x.id),liveClassesAt(ws,2).map(x=>x.id),
        liveClassesAt(ws,3).map(x=>x.id),visualStateFor(ws,ws.classes[0])];
    })()""")["result"]
    assert result == [["a", "b"], ["a", "b"], ["b", "c"], "unknown"]


def test_source_review_never_enters_q8_page_algebra_even_with_stale_metadata():
    result = app_helper(["pageAlgebra"], """(() => {
      window.HFPSSPageAlgebra={compute:()=>{throw new Error('wrong algebra');}};
      return [
        pageAlgebra({spectral_sequence:'2-bss',group:'Q8',settings:{rendering:{enumerated_e2_pattern:'integer'}}},{}),
        pageAlgebra({spectral_sequence:'hfpss',group:'C4',settings:{rendering:{enumerated_e2_pattern:'integer'}}},{}),
        pageAlgebra({spectral_sequence:'hfpss',group:'Q8',settings:{source_reference:true,rendering:{enumerated_e2_pattern:'integer'}}},{})];
    })()""")["result"]
    assert result == [None, None, None]


def test_projected_bss_points_remain_distinct_even_with_equal_labels():
    result = app_helper(["periodicClassInstances", "uniqueClassDisplaySlots", "e2DisplaySlot"], """(() => {
      globalThis.liveClassesAt=ws=>ws.classes;
      globalThis.periodsForClassOnPage=()=>[];
      globalThis.latticeCopies=grade=>[{grade,periodic:false}];
      globalThis.periodicDisplayLabel=record=>record.item.label;
      globalThis.glyphShapeFor=()=> 'dot';
      globalThis.visualStateFor=()=> 'unknown';
      globalThis.inBounds=()=>true;
      const ws={spectral_sequence:'2-bss',settings:{source_reference:true},classes:[0,1].map(i=>({
        id:'h0-level-'+i,label:'same',grade:{stem:0,filtration:0},style:{bockstein_filtration:i}}))};
      return periodicClassInstances(ws,{},null,null).map(record=>record.item.id);
    })()""")["result"]
    assert result == ["h0-level-0", "h0-level-1"]


def test_bss_status_distinguishes_projection_from_coefficient_filtration():
    result = app_helper(["bssSector", "bssProjection", "bssGradingText", "pageStatusText"], """pageStatusText({id:'ws_q8_bss_sigma',page:1,spectral_sequence:'2-bss',settings:{
      literature_review:{coverage:'Appendix A source equations'}}})""")["result"]
    assert "Waiting" in result and "no source catalog" in result
    assert "tridegree is (-1,+1,+r)" in result and "Actual RO stem=1+stem−σᵢ" in result


def test_review_panel_escapes_source_text_and_preserves_math():
    result = app_helper(["literatureReviewMarkup", "sourceProseMarkup", "escapeHtml", "mathMarkup"], """literatureReviewMarkup({
      scope:'<script>unsafe</script>',coverage:'generator equations',
      notation:[{symbol:'\\\\Delta',stem:24,filtration:0,meaning:'C3 invariant'}],
      warnings:['Not the C4 degree-8 Delta'],source_refs:['Appendix A'],relations:['x+y=0']})""")["result"]
    assert "<script>" not in result and "&lt;script&gt;" in result
    assert "(24, 0)" in result and "C3 invariant" in result and "Appendix A" in result


def test_period_prose_typesets_only_explicit_math_and_escapes_html():
    result = app_helper(["sourceProseMarkup", "escapeHtml"], r"""(() => {
      globalThis.mathMarkup=value=>'[math:'+value+']';
      return sourceProseMarkup('Period $\\Delta^4$; \\(h_0\\) <unsafe>.');
    })()""")["result"]
    assert result == r"Period [math:\Delta^4]; [math:h_0] &lt;unsafe&gt;."


def test_bss_algebra_and_basis_are_visible_without_executing_prose_markup():
    result = app_helper(["literatureReviewMarkup", "sourceProseMarkup", "escapeHtml", "mathMarkup"], r"""literatureReviewMarkup({
      e1_algebra:'F4[<unsafe>]',basis_coefficient_ring:'F4[D,k,h0]',
      e1_additive_basis:[{labels:['x','xh_1'],v1_exponents:[0,1]},
        {labels:['1'],v1_exponents:'all nonnegative integers'}],
      notation_dictionary:['<img> no HTML'],differential_rules:['d1(v1)=h0 h1 <test>'],
      hidden_extensions:['2h_2=0']})""")["result"]
    assert "F4[&lt;unsafe&gt;]" in result and "<img>" not in result
    assert "F4[D,k,h0]" in result and "0, 1" in result
    assert "all nonnegative integers" in result and "xh_1" in result
    assert "d1(v1)=h0 h1 &lt;test&gt;" in result
    assert "Hidden extensions in the abutment" in result and "2h_2=0" in result


def test_source_reference_controls_and_static_mirrors():
    root = Path(__file__).resolve().parents[1]
    markup = (root / "backend/templates/index.html").read_text(encoding="utf-8")
    assert 'id="literature-review-panel"' in markup
    assert 'id="fate-inspector-title"' in markup
    for name in ("app.js", "style.css"):
        assert (root / "backend/static" / name).read_bytes() == (root / "public/static" / name).read_bytes()


def test_computed_scope_separates_fallback_catalog_cautions():
    result = app_helper(["literatureReviewMarkup", "sourceProseMarkup", "escapeHtml", "mathMarkup"], """literatureReviewMarkup({
      coverage:'Computed exact quotient within stated bounds',warning_heading:'Computation scope',
      warnings:['Omitted higher powers are not zero'],
      catalog_warnings:['NOT a computed full E_r page <fallback>']})""")["result"]
    before, details = result.split('<details>', 1)
    assert 'Computed exact quotient' in before and 'Omitted higher powers are not zero' in before
    assert 'NOT a computed full' not in before
    assert 'not the computed window above' in details and 'Mathematical errata still apply' in details
    assert '&lt;fallback&gt;' in details and '<fallback>' not in details
