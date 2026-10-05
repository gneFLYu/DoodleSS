"""Three-graded BSS rendering keeps actual map endpoints and dependent vectors."""
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from test_chart_display_conventions import app_helper
from test_bss_window_ui import real_bss_rendering, real_bss_periodic_rendering, runtime


def test_h0_towers_are_vertical_ordered_and_use_one_shared_third_grading_scale():
    packed = app_helper(["packBssInstances"], """(() => {
      const records=[];
      for(const [cell,tower,levels] of [['0:0','a',[0,1,2,3,4]],['0:0','b',[0,2]],['1:1','c',[1,3]]])
        for(const h0 of levels) records.push({key:tower+h0,cellKey:cell,item:{id:tower+h0,
          style:{bss_tower_key:tower,bockstein_filtration:h0,bss_boundary:h0>2?'outgoing_target':''}}});
      return packBssInstances(records.reverse(),{cell:42});
    })()""")["result"]
    towers = defaultdict(list)
    for node in packed:
        towers[node["item"]["style"]["bss_tower_key"]].append(node)
        assert abs(node["dx"]) <= 42 * .35
        assert abs(node["dy"]) <= 42 * .3
    steps = []
    for nodes in towers.values():
        nodes.sort(key=lambda n: n["item"]["style"]["bockstein_filtration"])
        assert len({node["dx"] for node in nodes}) == 1
        for low, high in zip(nodes, nodes[1:]):
            dh = high["item"]["style"]["bockstein_filtration"] - low["item"]["style"]["bockstein_filtration"]
            assert high["dy"] < low["dy"]
            steps.append((low["dy"] - high["dy"]) / dh)
    assert steps == pytest.approx([steps[0]] * len(steps))


def test_pending_e4_has_no_catalog_and_preserves_original_catalog_separately():
    result = runtime("""
      const ws=workspace(); ws.page=4; prepareBssWindow(ws);
      return {shown:ws.classes,saved:storage.catalogs.get(ws).classes.map(n=>n.id),path:requests[0].path};
    """)
    assert result["shown"] == [] and result["saved"] == ["seed"]
    assert "page=4" in result["path"]


def test_every_real_relation_joins_actual_selectable_endpoints_without_summand_fan(real_bss_rendering):
    relation_count = combination_count = 0
    for case in real_bss_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        glyphs = {node.get("data-point"): node for node in xml.iter("g") if node.get("data-point")}
        points = {point["id"]: point["point"] for point in case["points"]}
        lines = {node.get("data-relation"): node for node in xml.iter("line") if node.get("data-relation")}
        relations = [claim for claim in case["propositions"] if claim["kind"] == "relation"]
        assert len(lines) == len(relations)
        relation_count += len(relations)
        for claim in relations:
            conclusion = claim["conclusion"]
            line = lines[claim["id"]]
            for suffix, endpoint in (("1", conclusion["source_id"]), ("2", conclusion["target_id"])):
                assert endpoint in glyphs
                assert float(line.get("x" + suffix)) == pytest.approx(points[endpoint]["x"])
                assert float(line.get("y" + suffix)) == pytest.approx(points[endpoint]["y"])
            if conclusion["chart_connection"]["multiplier"] == "h_0":
                assert float(line.get("x1")) == pytest.approx(float(line.get("x2")))
                assert float(line.get("y2")) < float(line.get("y1"))
            assert "dkllw-" not in line.get("class")
        for node in case["nodes"]:
            if not node["style"].get("bss_combination"):
                continue
            combination_count += 1
            glyph = glyphs[node["id"]]
            assert glyph.get("data-bss-combination") == "true"
            assert any(text.text == "Σ" for text in glyph.iter("text"))
            assert not any("class-point" in mark.get("class", "") for mark in glyph.iter("circle"))
            assert "not an extra basis class" in glyph.get("aria-label")
    assert relation_count > 50
    assert combination_count > 0


def test_real_h0_levels_are_monotone_for_every_tower_including_boundary_nodes(real_bss_rendering):
    boundary_count = 0
    for case in real_bss_rendering:
        points = {point["id"]: point["point"] for point in case["points"]}
        towers = defaultdict(list)
        for node in case["nodes"]:
            if node["id"] not in points:
                continue
            towers[node["style"]["bss_tower_key"]].append(node)
            boundary_count += bool(node["style"].get("bss_boundary"))
        for nodes in towers.values():
            nodes.sort(key=lambda node: node["style"]["bockstein_filtration"])
            for low, high in zip(nodes, nodes[1:]):
                assert points[low["id"]]["x"] == points[high["id"]]["x"]
                assert points[high["id"]]["y"] < points[low["id"]]["y"]
    assert boundary_count > 0


def test_sigma_inspection_reports_actual_ro_degree_and_differential_tridegree(real_bss_rendering):
    case = next(case for case in real_bss_rendering if case["sector"] == "sigma" and case["page"] == 2)
    xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
    node = next(node for node in case["nodes"] if node["grade"] == {"stem": 1, "filtration": 3, "representation": {"sigma_i": -1}}
                and node["style"].get("bss_monomial", {}).get("basis") == "xh1^2"
                and node["style"]["bockstein_filtration"] == 1)
    glyph = next(glyph for glyph in xml.iter("g") if glyph.get("data-point") == node["id"])
    description = glyph.get("aria-label")
    assert "Projection (stem,s)=(1,3); h₀=1" in description
    assert "Actual RO stem=2−σᵢ" in description
    assert "tridegree is (-1,+1,+r)" in description
    assert "(1, 3) -sigma_i" not in description
    assert description.startswith(r"h_0xh_1^2u_{\sigma_i}")


def test_screenshot_sigma_e2_family_has_three_arrows_and_all_three_real_targets(real_bss_rendering):
    case = next(case for case in real_bss_rendering if case["sector"] == "sigma" and case["page"] == 2)
    nodes = {node["id"]: node for node in case["nodes"]}
    xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
    glyphs = {node.get("data-point"): node for node in xml.iter("g") if node.get("data-point")}
    arrows = []
    for arrow in case["differentials"]:
        monomial = nodes[arrow["source_id"]]["style"].get("bss_monomial", {})
        if all(monomial.get(key) == value for key, value in {"basis": "xh1^2", "v1": 0, "k": 0, "D": 0}.items()):
            arrows.append(arrow)
    assert len(arrows) == 3
    targets = [nodes[arrow["target_id"]] for arrow in arrows]
    assert sorted(node["style"]["bockstein_filtration"] for node in targets) == [2, 3, 4]
    assert sum(bool(node["style"].get("bss_boundary")) for node in targets) == 2
    for node in targets:
        assert node["id"] in glyphs
        assert node["grade"]["stem"] == 0 and node["grade"]["filtration"] == 4
        assert not node["style"].get("window_endpoint_only")


def test_class_list_does_not_count_dependent_combinations_as_basis():
    result = app_helper(["renderClassList"], """(() => {
      const elements={'#class-count':{},'#class-list':{querySelectorAll:()=>[]}};
      globalThis.$=id=>elements[id];globalThis.state={};
      globalThis.visualStateFor=()=>'';globalThis.mathMarkup=value=>value;
      const nodes=[{id:'a',label:'a',grade:{stem:0,filtration:0},style:{bss_in_window:true,bockstein_filtration:0}},
        {id:'b',label:'b',grade:{stem:0,filtration:0},style:{bss_in_window:false,bss_boundary:'outgoing_target',bockstein_filtration:3}},
        {id:'sum',label:'a+b',grade:{stem:0,filtration:0},style:{bss_in_window:false,bss_combination:true,bockstein_filtration:0}}];
      renderClassList({spectral_sequence:'2-bss'},nodes);
      return {count:elements['#class-count'].textContent,markup:elements['#class-list'].innerHTML};
    })()""")["result"]
    assert result["count"] == "1 basis · 1 boundary · 1 Σ"
    assert "Σ · a+b" in result["markup"] and "h₀=3" in result["markup"]


def test_bss_has_its_own_visible_chart_key_not_q8_hidden_extension_semantics():
    result = app_helper(["renderLiteratureReview"], """(() => {
      const elements={'#q8-chart-key':{},'#c4-chart-key':{},'#bss-chart-key':{}};
      globalThis.$=id=>elements[id];
      document.body={classList:{toggle(){}}};
      renderLiteratureReview({spectral_sequence:'2-bss',settings:{}});
      return elements;
    })()""")["result"]
    assert result["#q8-chart-key"]["hidden"] is True
    assert result["#c4-chart-key"]["hidden"] is True
    assert result["#bss-chart-key"]["hidden"] is False
    html = (Path(__file__).resolve().parents[1] / "backend/templates/index.html").read_text(encoding="utf-8")
    key = html.split('id="bss-chart-key"', 1)[1].split("</section>", 1)[0]
    assert "Beaudry/Henn" in key and "do not assert hidden extensions" in key
    assert "not an extra basis class" in key and "(−1, +1, +r)" in key


def test_core_relations_hide_extra_products_but_selection_reveals_same_family():
    result = app_helper(["showBssRelation"], """(() => {
      const ws={spectral_sequence:'2-bss',settings:{},classes:[
        {id:'a',style:{bss_periodic_family_key:'same'}},{id:'periodic-a',style:{bss_periodic_family_key:'same'}},
        {id:'b',style:{bss_periodic_family_key:'other'}}]};
      globalThis.state={selectedClassId:null};
      const relations=['two','h1','h2','v1','x','y'].map(kind=>({conclusion:{source_id:'periodic-a',target_id:'b',chart_connection:{kind}}}));
      const core=relations.map(r=>showBssRelation(ws,r));
      state.selectedClassId='a';const focused=relations.map(r=>showBssRelation(ws,r));
      state.selectedClassId=null;ws.settings.bss_relations='all';const all=relations.map(r=>showBssRelation(ws,r));
      return {core,focused,all};
    })()""")["result"]
    assert result == {"core": [True, True, True, False, False, False], "focused": [True] * 6, "all": [True] * 6}


def test_periodic_bss_svg_retains_real_seam_endpoints_and_both_projection_degrees(real_bss_periodic_rendering):
    seams = {"cohomology": 0, "bockstein": 0}
    for case in real_bss_periodic_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        lines = [line for line in xml.iter("line") if line.get("data-differential")]
        points = {(point["id"], point["grade"]["stem"], point["grade"]["filtration"]): point["point"] for point in case["points"]}
        assert len(lines) == len(case["arrowOccurrences"])
        for occurrence in case["arrowOccurrences"]:
            source, target = occurrence["sourceGrade"], occurrence["targetGrade"]
            assert target["stem"] - source["stem"] == -1
            assert target["filtration"] - source["filtration"] == (case["page"] if case["projection"] == "bockstein" else 1)
            source_point = points.get((occurrence["sourceId"], source["stem"], source["filtration"]))
            target_point = points.get((occurrence["targetId"], target["stem"], target["filtration"]))
            if source_point is None or target_point is None:
                continue
            assert any(line.get("data-differential") == occurrence["id"]
                and float(line.get("x1")) == pytest.approx(source_point["x"])
                and float(line.get("y1")) == pytest.approx(source_point["y"])
                and float(line.get("x2")) == pytest.approx(target_point["x"])
                and float(line.get("y2")) == pytest.approx(target_point["y"]) for line in lines)
            seams[case["projection"]] += source["stem"] % 8 == 0 and target["stem"] % 8 == 7
        for node in case["nodes"]:
            expected = node["style"]["bockstein_filtration"] if case["projection"] == "bockstein" else node["style"]["bss_cohomological_filtration"]
            assert node["grade"]["filtration"] == expected
        assert not any("nan" in line.get(axis, "").lower() for line in lines for axis in ("x1", "x2", "y1", "y2"))
    assert all(count > 0 for count in seams.values())


@pytest.mark.parametrize("projection,degree,axis", [("cohomology", "(-1,+1)", "s = group-cohomology degree"),
                                                    ("bockstein", "(-1,+r)", "p = Bockstein filtration")])
def test_bss_projection_caption_keeps_the_three_gradings_explicit(projection, degree, axis):
    result = app_helper(["bssProjection", "bssSector", "bssGradingText"], """bssGradingText({id:'ws_q8_bss_sigma',
      settings:{bss_projection:input.projection}})""", projection=projection)["result"]
    assert axis in result and "plotted degree " + degree in result
    assert "(-1,+1,+r) in (t−s,s,p)" in result and "1+stem−σᵢ" in result


def test_bockstein_variable_bypasses_hfpss_label_normalization():
    result = app_helper(["mathMarkup"], r"""(() => {
      window.HFPSSDisplayBasis={normalizeLabel:()=>{throw new Error('h0 is not an HFPSS variable');}};
      window.katex={renderToString:source=>source};
      return mathMarkup('h_0xh_1^2u_{\\sigma_i}');
    })()""")["result"]
    assert result == r"h_0xh_1^2u_{\sigma_i}"
