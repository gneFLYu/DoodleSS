"""Spectral-sequence family selection and family-specific grading atlases."""
from html.parser import HTMLParser
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_chart_display_conventions import app_helper


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "backend/static/workspace-navigation.js"


def navigation(expression, **values):
    result = subprocess.run(["node", "-e", """
      const fs=require('fs'),input=JSON.parse(fs.readFileSync(0,'utf8'));
      const nav=require(input.module);
      process.stdout.write(JSON.stringify(eval(input.expression)));
    """], input=json.dumps({"module": str(MODULE), "expression": expression, **values}),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    return json.loads(result.stdout)


class Inventory(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.nodes = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


@pytest.fixture(scope="module")
def navigation_project():
    sys.path.insert(0, str(ROOT / "backend"))
    from domain.bss_reference import create_bss_reference_workspaces
    from domain.c4_reference import create_c4_reference_workspaces
    from domain.atlas_transport import ensure_q8_atlas_transports
    from domain.grading import ensure_q8_atlas
    from domain.models import Project

    def workspace(key, name, group="Q8", sequence="hfpss", grading_label="", **settings):
        return {"id": key, "name": name, "group": group, "spectral_sequence": sequence,
                "grading_label": grading_label, "classes": [{"id": key + "-class"}], "settings": settings}

    # Exercise the actual representative/transport classification rather than
    # assuming that a workspace without transport metadata is independent.
    source = ensure_q8_atlas(Project(id="hfpss_studio", name="Navigation metadata fixture"))
    ensure_q8_atlas_transports(source)
    sectors = [asdict(sector) for sector in source.grading_sectors]
    workspaces = [workspace(item.id, item.name, item.group, item.spectral_sequence,
                            item.grading_label, **item.settings) for item in reversed(source.workspaces)]
    workspaces.extend([workspace("ws_c4_j", "Historical C4", group="C4"),
                       workspace("ws_H", "Q8 support"), workspace("manual", "User-drawn Q8 chart")])
    for item in create_c4_reference_workspaces(stem_min=0, stem_max=0, filtration_max=0) + create_bss_reference_workspaces():
        workspaces.append(workspace(item.id, item.name, item.group, item.spectral_sequence,
                                    item.grading_label, source_reference=True))
    return {"workspaces": workspaces, "grading_sectors": sectors}


def test_only_three_sequence_families_and_integer_defaults(navigation_project):
    result = navigation("nav.families(input.project)", project=navigation_project)
    assert [(item["id"], item["label"], item["defaultWorkspaceId"]) for item in result] == [
        ("q8-hfpss", "Q8 HFPSS", "ws_integer"),
        ("c4-hfpss", "C4 HFPSS", "ws_c4_bbhs_integer"),
        ("q8-2-bss", "Q8 2-BSS", "ws_q8_bss_integer")]
    listed = [workspace_id for item in result for workspace_id in item["workspaceIds"]]
    assert len(listed) == len(set(listed)) == len(navigation_project["workspaces"])
    assert set(listed) == {item["id"] for item in navigation_project["workspaces"]}


@pytest.mark.parametrize("current,family", [("ws_3sigma_i", "q8-hfpss"), ("manual", "q8-hfpss"),
    ("ws_c4_j", "c4-hfpss"), ("ws_c4_bbhs_1_minus_sigma", "c4-hfpss"), ("ws_q8_bss_sigma", "q8-2-bss")])
def test_selector_value_is_family_not_current_workspace(navigation_project, current, family):
    result = navigation("""(() => {
      const before=JSON.stringify(input.project),selector={};
      nav.renderSelector(selector,input.project,input.project.workspaces.find(item=>item.id===input.current));
      return {...selector,unchanged:before===JSON.stringify(input.project)};
    })()""", project=navigation_project, current=current)
    assert result["value"] == family and result["disabled"] is False and result["unchanged"]
    options = [attrs for tag, attrs in Inventory(result["innerHTML"]).nodes if tag == "option"]
    assert [item["value"] for item in options] == ["q8-hfpss", "c4-hfpss", "q8-2-bss"]
    assert "Computed representatives" not in result["innerHTML"] and "Isomorphic" not in result["innerHTML"]


def test_q8_atlas_keeps_all_sixteen_sectors_and_manual_support(navigation_project):
    result = navigation("nav.atlas(input.project,input.project.workspaces.find(item=>item.id==='ws_3sigma_i'))", project=navigation_project)
    assert result["eyebrow"] == "RO(Q8) ATLAS" and len(result["entries"]) == 16
    assert {item["sectorId"] for item in result["entries"]} == {item["id"] for item in navigation_project["grading_sectors"]}
    assert [item["workspaceId"] for item in result["entries"] if item["active"]] == ["ws_3sigma_i"]
    assert {item["workspaceId"] for item in result["additionalEntries"]} == {"ws_H", "manual"}


def test_c4_atlas_has_independent_slices_and_correct_ro_reduction(navigation_project):
    result = navigation("nav.atlas(input.project,input.project.workspaces.find(item=>item.id==='ws_c4_bbhs_1_minus_sigma'))", project=navigation_project)
    assert result["eyebrow"] == "RO(C4) ATLAS"
    assert [item["workspaceId"] for item in result["entries"]] == ["ws_c4_bbhs_integer", "ws_c4_bbhs_1_minus_sigma"]
    assert [item["active"] for item in result["entries"]] == [False, True]
    assert [item["workspaceId"] for item in result["additionalEntries"]] == ["ws_c4_j"]
    assert result["reduction"]["integerPeriod"] == 32
    assert result["reduction"]["quotient"] == "Z/32{1} ⊕ Z/2{7+σ}"
    assert result["reduction"]["independentSlices"] is True
    assert "not the order-two generator" in result["reduction"]["warning"]
    assert "does not identify the two slices" in result["summary"]


def test_bss_atlas_does_not_show_q8_hfpss_sixteen_sectors(navigation_project):
    result = navigation("nav.atlas(input.project,input.project.workspaces.find(item=>item.id==='ws_q8_bss_sigma'))", project=navigation_project)
    assert result["eyebrow"] == "Q8 2-BSS SLICES"
    assert [item["workspaceId"] for item in result["entries"]] == ["ws_q8_bss_integer", "ws_q8_bss_sigma"]
    assert all(item["kind"] == "workspace" and "sectorId" not in item for item in result["entries"])
    assert "not HFPSS pages" in result["summary"]


def test_other_sequences_remain_accessible_with_safe_family_defaults():
    project = {"workspaces": [{"id": "s", "group": "C2", "spectral_sequence": "tate", "grading_label": "sigma"},
                              {"id": "i", "group": "C2", "spectral_sequence": "tate", "grading_label": "integer"}]}
    result = navigation("nav.families(input.project)", project=project)
    assert len(result) == 1 and result[0]["label"] == "C2 TATE"
    assert result[0]["workspaceIds"] == ["s", "i"] and result[0]["defaultWorkspaceId"] == "i"


def test_atlas_buttons_accessible_and_prose_is_escaped(navigation_project):
    result = navigation("""(() => {
      const ws=input.project.workspaces.find(item=>item.id==='manual');ws.name='<img onerror="unsafe">';
      const model=nav.atlas(input.project,ws);return nav.atlasMarkup(model);
    })()""", project=navigation_project)
    nodes = Inventory(result).nodes
    buttons = [attrs for tag, attrs in nodes if tag == "button"]
    assert len(buttons) == 18
    assert all(item["type"] == "button" and item.get("aria-label") and item.get("aria-pressed") in ("true", "false") for item in buttons)
    assert len([item for item in buttons if item["aria-pressed"] == "true"]) == 1
    assert any(tag == "details" and "open" in attrs for tag, attrs in nodes)
    assert "<img" not in result and "&lt;img" in result


def test_atlas_callback_returns_sector_or_workspace_entry(navigation_project):
    result = navigation("""(() => {
      const ws=input.project.workspaces.find(item=>item.id==='ws_integer'), model=nav.atlas(input.project,ws);
      const events=[],buttons=[...model.entries,...model.additionalEntries].map((entry,index)=>({
        dataset:{navigationIndex:String(index)},addEventListener(name,handler){this.click=handler;}}));
      const root={dataset:{},querySelector:()=>null,setAttribute(){},querySelectorAll:()=>buttons};
      nav.renderAtlas(root,model,entry=>events.push(entry));buttons[0].click();buttons.at(-1).click();
      return {events,family:root.dataset.familyId};
    })()""", project=navigation_project)
    assert result["family"] == "q8-hfpss"
    assert result["events"][0]["kind"] == "sector" and result["events"][0]["sectorId"] == "q8-ro-a0-b0"
    assert result["events"][1]["kind"] == "workspace" and result["events"][1]["workspaceId"] == "manual"


def test_template_loads_module_and_preserves_archive_without_c4_manual_bounds():
    markup = (ROOT / "backend/templates/index.html").read_text(encoding="utf-8")
    assert markup.index("workspace-navigation.js") < markup.index("filename='app.js'")
    for element_id in ("grading-atlas-eyebrow", "grading-atlas-title", "grading-atlas-summary", "c4-period-info",
                       "c4-window-panel", "c4-window-status", "legacy-catalog-reference", "legacy-catalog-select",
                       "open-legacy-catalog", "close-legacy-catalog"):
        assert f'id="{element_id}"' in markup
    assert 'id="c4-window-form"' not in markup and 'id="support-workspace-select"' not in markup
    for name in ("workspace-navigation.js", "style.css"):
        assert (ROOT / "public/static" / name).read_bytes() == (ROOT / "backend/static" / name).read_bytes()


def app_navigation(functions, expression, project):
    prelude = """(() => {
      eval(input.navigationSource);
      window.HFPSSWorkspaceNavigation=HFPSSWorkspaceNavigation;
      globalThis.state={project:input.project,workspaceId:'ws_integer',catalogMode:false,
        selectedClassId:'old',selectedOccurrence:{id:'old'},classFilter:'old',suggestions:[1],
        candidateResults:{},periodicityPreview:{},drawingPeriodicityPreview:{},connectionStart:'old'};
      const controls=new Map();
      globalThis.$=key=>{if(!controls.has(key))controls.set(key,{textContent:'stale',title:'stale',value:'old'});return controls.get(key);};
      globalThis.workspace=()=>state.project.workspaces.find(item=>item.id===state.workspaceId);
      globalThis.render=()=>calls.push('render');
      globalThis.selectAtlasSector=id=>calls.push('sector:'+id);
    """
    return app_helper(functions, prelude + expression + "})()", project=project,
                      navigationSource=MODULE.read_text(encoding="utf-8"))["result"]


def test_app_select_workspace_resets_selection_not_saved_pages_or_data(navigation_project):
    result = app_navigation(["selectWorkspace"], """
      const before=JSON.stringify(state.project);
      selectWorkspace(window.HFPSSWorkspaceNavigation.defaultWorkspaceId(state.project,'c4-hfpss'));
      return {selected:state.workspaceId,occurrence:state.selectedOccurrence,classId:state.selectedClassId,
        filter:state.classFilter,input:$('#class-filter').value,view:state.view,calls,
        unchanged:before===JSON.stringify(state.project)};
    """, navigation_project)
    assert result == {"selected": "ws_c4_bbhs_integer", "occurrence": None, "classId": None,
                      "filter": "", "input": "", "view": {"zoom": 1, "panX": 0, "panY": 0},
                      "calls": ["render"], "unchanged": True}


@pytest.mark.parametrize("current,family,eyebrow", [("ws_integer", "q8-hfpss", "RO(Q8) ATLAS"),
    ("ws_c4_bbhs_1_minus_sigma", "c4-hfpss", "RO(C4) ATLAS"), ("ws_q8_bss_sigma", "q8-2-bss", "Q8 2-BSS SLICES")])
def test_app_renders_matching_family_and_atlas(navigation_project, current, family, eyebrow):
    project = dict(navigation_project, testCurrent=current)
    result = app_navigation(["renderWorkspaceNavigation", "readOnlyCatalog", "renderGradingAtlas", "selectWorkspace"], """
      state.workspaceId=state.project.testCurrent;
      let model,choose;
      window.HFPSSWorkspaceNavigation.renderAtlas=(_root,value,callback)=>{model=value;choose=callback;};
      renderWorkspaceNavigation(workspace());renderGradingAtlas();
      choose(model.entries[0]);
      return {family:$('#workspace-select').value,eyebrow:$('#grading-atlas-eyebrow').textContent,
        title:$('#grading-atlas-title').textContent,summary:$('#grading-atlas-summary').textContent,
        entryCount:model.entries.length,calls,selected:state.workspaceId};
    """, project)
    assert result["family"] == family and result["eyebrow"] == eyebrow
    assert result["title"] and result["summary"]
    if family == "q8-hfpss":
        assert result["entryCount"] == 16 and result["calls"] == ["sector:q8-ro-a0-b0"]
    else:
        assert result["entryCount"] == 2 and result["calls"] == ["render"]
        assert result["selected"] == ("ws_c4_bbhs_integer" if family == "c4-hfpss" else "ws_q8_bss_integer")


@pytest.mark.parametrize("current", ["ws_c4_bbhs_integer", "ws_q8_bss_integer"])
def test_non_q8_atlas_does_not_retain_c3_transport_text(navigation_project, current):
    project = dict(navigation_project, testCurrent=current)
    result = app_navigation(["renderAtlasPath"], """
      state.workspaceId=state.project.testCurrent;
      renderAtlasPath(workspace());
      return {text:$('#c3-summary').textContent,title:$('#c3-summary').title};
    """, project)
    assert result == {"text": "", "title": ""}


def test_app_toolbar_change_selects_integer_default_of_family():
    script = (ROOT / "backend/static/app.js").read_text(encoding="utf-8")
    assert 'selectWorkspace(window.HFPSSWorkspaceNavigation.defaultWorkspaceId(state.project, event.target.value))' in script
    assert 'window.HFPSSWorkspaceNavigation.renderSelector(selector, state.project, ws)' in script


def test_exact_five_backend_representatives_highlighted_without_status_promotion(navigation_project):
    result = navigation("""(() => {
      const before=JSON.stringify(input.project), model=nav.atlas(input.project,input.project.workspaces.find(w=>w.id==='ws_integer'));
      return {model,unchanged:before===JSON.stringify(input.project)};
    })()""", project=navigation_project)
    entries = result["model"]["entries"]
    representatives = {(entry["a"], entry["b"]): entry["workspaceId"] for entry in entries if entry["independent"]}
    assert representatives == {(0, 0): "ws_integer", (1, 0): "ws_sigma_i", (2, 0): "ws_2sigma_i",
                               (3, 0): "ws_3sigma_i", (1, 2): "ws_sigma_i_2sigma_j"}
    assert result["unchanged"] and len(entries) == 16
    statuses = {sector["id"]: sector["status"] for sector in navigation_project["grading_sectors"]}
    assert all(entry["status"] == statuses[entry["sectorId"]] for entry in entries)


def test_transported_and_unmarked_tiles_are_not_independent(navigation_project):
    result = navigation("""(() => {
      const transported=input.project.workspaces.find(w=>w.id==='ws_q8-ro-a0-b1');
      transported.settings.atlas_representative=true;
      const unmarked=input.project.workspaces.find(w=>w.id==='ws_q8-ro-a0-b2');
      delete unmarked.settings.atlas_transport;delete unmarked.settings.atlas_representative;
      return nav.atlas(input.project,transported).entries.filter(e=>[transported.id,unmarked.id].includes(e.workspaceId));
    })()""", project=navigation_project)
    assert len(result) == 2 and all(entry["independent"] is False for entry in result)
    assert next(entry for entry in result if entry["workspaceId"] == "ws_q8-ro-a0-b1")["active"] is True


@pytest.mark.parametrize("current,is_independent", [("ws_3sigma_i", True), ("ws_q8-ro-a0-b1", False)])
def test_independent_badge_is_distinct_from_active_selection(navigation_project, current, is_independent):
    result = navigation("""(() => {
      const model=nav.atlas(input.project,input.project.workspaces.find(w=>w.id===input.current));
      return nav.atlasMarkup(model);
    })()""", project=navigation_project, current=current)
    nodes = Inventory(result).nodes
    buttons = [attrs for tag, attrs in nodes if tag == "button"]
    independent = [attrs for attrs in buttons if "independent-representative" in attrs.get("class", "").split()]
    active = [attrs for attrs in buttons if attrs.get("aria-pressed") == "true"]
    assert len(independent) == 5 and result.count(">Independent<") == 5
    assert len(active) == 1 and active[0]["data-atlas-workspace"] == current
    assert ("independent-representative" in active[0]["class"].split()) is is_independent
    assert len(buttons) == 18  # all 16 tiles, plus retained support/manual pages


def test_retired_computed_representatives_group_not_reintroduced(navigation_project):
    result = navigation("""(() => {
      const ws=input.project.workspaces.find(w=>w.id==='ws_integer'), selector={};
      nav.renderSelector(selector,input.project,ws);
      return selector.innerHTML+nav.atlasMarkup(nav.atlas(input.project,ws));
    })()""", project=navigation_project)
    assert "Computed representatives" not in result
    assert "Isomorphic atlas pages" not in result
    assert not any(tag == "optgroup" for tag, _ in Inventory(result).nodes)
