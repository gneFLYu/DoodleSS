"""Periodic highlighting preserves exact C4 coefficient ports and BSS h0 levels."""
import json
from pathlib import Path
import subprocess
import sys
from collections import defaultdict
from xml.etree import ElementTree as ET

import pytest

from test_chart_display_conventions import app_helper


def test_c4_family_highlighting_uses_certified_port_keys_not_entire_towers():
    result = app_helper(["classFamilySelection", "c4CoefficientPorts"], """(() => {
      const make=(id,mu,keys)=>({id,style:{c4_coefficient_branch:{mu_min:mu,two_min:0,two_max:2},c4_periodic_family_keys:keys}});
      const source=make('source',0,{'0:0':'a','1:0':'b','2:0':'c'});
      const related=make('related',0,{'0:0':'a','1:0':'b','2:0':'c'});
      const muTail=make('tail',1,{'0:0':'mu-a','1:0':'mu-b','2:0':'mu-c'});
      const disconnected=make('dead-predecessor',0,{'0:0':'new-a','1:0':'new-b','2:0':'new-c'});
      const ws={id:'ws',page:5,classes:[source,related,muTail,disconnected]};
      globalThis.state={selectedClassId:'source',selectedOccurrence:{workspaceId:'ws',page:5,classId:'source',selectedPort:'1:0'}};
      return ws.classes.map(item=>classFamilySelection(ws,{item}));
    })()""")["result"]
    assert result == [{"selected": True, "ports": ["1:0"]}] * 2 + [{"selected": False, "ports": []}] * 2


def test_bss_family_highlight_preserves_h0_and_v1_and_does_not_require_shared_ids():
    result = app_helper(["classFamilySelection"], """(() => {
      const ws={spectral_sequence:'2-bss',classes:[
        {id:'a',style:{bss_periodic_family_key:'basis-v0-h1'}},
        {id:'D-copy',style:{bss_periodic_family_key:'basis-v0-h1'}},
        {id:'k-copy',style:{bss_periodic_family_key:'basis-v0-h1'}},
        {id:'other-h0',style:{bss_periodic_family_key:'basis-v0-h2'}},
        {id:'other-v1',style:{bss_periodic_family_key:'basis-v1-h1'}}]};
      globalThis.state={selectedClassId:'a'};
      return ws.classes.map(item=>classFamilySelection(ws,{item}).selected);
    })()""")["result"]
    assert result == [True, True, True, False, False]


@pytest.mark.parametrize("shape", ["finite-two-tower", "c4-witt-tower"])
def test_c4_ports_are_individually_clickable_and_only_matching_coefficient_is_blue(shape):
    markup = app_helper(["classGlyphMarkup"], """classGlyphMarkup({shape:input.shape,size:4,
      modulePorts:['0:0','1:0','2:0'],selectedFamilyPorts:['1:0'],
      item:{style:{c4_coefficient_branch:{mu_min:1,two_min:0,two_max:2,completed_mu_tail:true}}}},
      {x:40,y:60},'unknown')""", shape=shape)["result"]
    xml = ET.fromstring(markup)
    marks = [node for node in xml.iter() if node.get("data-coefficient-port")]
    assert len(marks) == 3
    assert "selected" not in xml.get("class", "").split()
    for mark in marks:
        selected = mark.get("data-coefficient-port") == "1:0"
        assert mark.get("role") == "button" and mark.get("tabindex") == "0"
        assert "pointer-events:all" in mark.get("style")
        assert ("color:var(--blue)" in mark.get("style")) == selected
        assert mark.get("aria-pressed") == str(selected).lower()


def test_c4_selected_port_survives_click_then_refresh_with_exact_label():
    root = Path(__file__).resolve().parents[1]
    script = r"""
const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync('backend/static/app.js','utf8');
const context=vm.createContext({window:{},document:{body:{dataset:{}}}});
vm.runInContext(source.slice(0,source.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
Promise.resolve(vm.runInContext(`(async()=>{
 const item={id:'c4',label:'4\\\\Delta_1',style:{c4_coefficient_branch:{mu_min:0,two_min:2,two_max:4,representative_tex:'4\\\\Delta_1'}}};
 const ws={id:'ws_c4_bbhs_integer',page:5,settings:{source_reference:true},classes:[item]};
 state.project={workspaces:[ws]};state.workspaceId=ws.id;state.tool='inspect';
 renderFateInspector=()=>{};renderPersistentPeriodicityTool=()=>{};renderChart=()=>{};toast=()=>{};fateFor=()=>null;
 const record={item,instanceKey:'copy',grade:{stem:40,filtration:0},horizontalExponent:1,selectedPort:'3:0'};
 periodicClassInstances=()=>[{...record,selectedPort:undefined}];
 await onClassClick(item.id,record);
 const clicked=JSON.parse(JSON.stringify(state.selectedOccurrence));
 refreshSelectedOccurrence();
 return {clicked,refreshed:state.selectedOccurrence};
})()`,context)).then(result=>process.stdout.write(JSON.stringify(result))).catch(error=>{console.error(error);process.exitCode=1;});
"""
    completed = subprocess.run(["node", "-e", script], cwd=root, capture_output=True,
                               text=True, encoding="utf-8", check=True, timeout=20)
    result = json.loads(completed.stdout)
    for state in result.values():
        assert state["selectedPort"] == "3:0" and state["c4MuExponent"] == 0
        assert state["label"].replace(" ", "") == r"8\Delta_1^{5}"


def test_refresh_discards_an_absent_coefficient_port_not_relabels_it_as_lower_port():
    result = app_helper(["c4CoefficientPorts", "refreshSelectedOccurrence"], """(() => {
      const ws={id:'ws',page:5};globalThis.workspace=()=>ws;
      globalThis.state={selectedClassId:'a',selectedOccurrence:{workspaceId:'ws',page:5,classId:'a',selectedPort:'3:0',grade:{stem:8,filtration:0}}};
      globalThis.periodicClassInstances=()=>[{item:{id:'a',style:{c4_coefficient_branch:{two_min:0,two_max:1}}}}];
      refreshSelectedOccurrence();return state.selectedOccurrence;
    })()""")["result"]
    assert result is None


@pytest.mark.parametrize("sector", ["integer", "1-minus-sigma"])
def test_real_c4_certificates_highlight_connected_family_without_other_two_or_mu_ports(sector):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from domain.c4_chart import build_c4_periodic_chart
    payload = build_c4_periodic_chart(sector, page=2, filtration_min=0, filtration_max=12)
    nodes = payload["chart"]["classes"]
    families = defaultdict(list)
    for node in nodes:
        for port, key in node["style"]["c4_periodic_family_keys"].items():
            families[key].append((node["id"], port))
    key, expected = next((key, entries) for key, entries in families.items()
                         if len(entries) > 1 and entries[0][1] != "0:0")
    selected_id, selected_port = expected[0]
    actual = app_helper(["classFamilySelection", "c4CoefficientPorts"], """(() => {
      const ws={id:'ws',page:2,classes:input.nodes};
      globalThis.state={selectedClassId:input.selected_id,selectedOccurrence:{workspaceId:'ws',page:2,classId:input.selected_id,selectedPort:input.selected_port}};
      return ws.classes.flatMap(item=>classFamilySelection(ws,{item}).ports.map(port=>[item.id,port]));
    })()""", nodes=nodes, selected_id=selected_id, selected_port=selected_port)["result"]
    assert sorted(map(tuple, actual)) == sorted(expected)
    matching = [node for node in nodes if any(identifier == node["id"] for identifier, _ in expected)]
    assert len({node["style"]["c4_coefficient_branch"]["mu_min"] for node in matching}) == 1
    assert len({port for _, port in actual}) == 1
