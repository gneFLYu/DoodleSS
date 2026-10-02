"""Manual arrows use selected occurrences and remain atomic, unproved candidates."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import app as app_module
from domain.chart_editing import prepare_connection, prepare_endpoint
from domain.models import ClassNode, Grade, Project, Workspace


@pytest.fixture
def workspace():
    return Workspace(id="manual", name="Manual test", page=5, classes=[
        ClassNode("source", "kD", Grade(4, 4), style={"e2_pattern": "I04"}),
        ClassNode("target", "x", Grade(3, 9), style={"e2_pattern": "I13"}),
        ClassNode("other", "y", Grade(3, 9), style={"e2_pattern": "I23"}),
        ClassNode("plain", "plain", Grade(0, 0)),
    ])


def endpoint(identifier, stem, filtration, label, two=0, j=0):
    return {"classId": identifier, "grade": {"stem": stem, "filtration": filtration},
            "label": label, "two": two, "j": j}


def connection():
    return {"kind": "differential", "page": 5,
            "source": endpoint("source", 4, 4, "kD"),
            "target": endpoint("target", 3, 9, "x")}


def test_existing_exact_endpoints_are_reused_without_mutation_or_proof(workspace):
    before = asdict(workspace)
    nodes, proposition, differential = prepare_connection(workspace, connection())
    assert nodes == [] and asdict(workspace) == before
    assert proposition.status == differential.status == "candidate"
    assert proposition.rule == "manual" and not proposition.premise_ids
    assert proposition.conclusion["coefficient_scope"] == "exact-port"
    assert differential.source_id == "source" and differential.target_id == "target"
    assert not differential.period_family_id
    assert differential.period_stem == differential.period_filtration == 0
    assert differential.unperiodic_reason == "manual-chart-occurrence"


def test_translated_higher_coefficient_ports_get_separate_nonperiodic_aliases(workspace):
    body = connection()
    body["source"] = endpoint("source", 68, 4, "4kD^9", two=2)
    body["target"] = endpoint("target", 67, 9, "2xD^8", two=1)
    before = asdict(workspace)
    nodes, proposition, differential = prepare_connection(workspace, body)
    assert asdict(workspace) == before
    assert len(nodes) == 2
    assert [node.label for node in nodes] == ["4kD^9", "2xD^8"]
    assert [node.style["two_valuation"] for node in nodes] == [2, 1]
    assert all(node.style["chart_occurrence_only"] for node in nodes)
    assert all(node.page == 5 for node in nodes)
    assert differential.source_id == nodes[0].id and differential.target_id == nodes[1].id
    assert proposition.conclusion["selected_occurrences"] == {"source": body["source"], "target": body["target"]}


def test_adapted_f4_target_preserves_exact_vector_not_a_global_scalar(workspace):
    body = connection()
    body["target"].update(classId="computed-display-basis", label=r"\{x+\zeta y\}", terms=[
        {"pattern": "I13", "coefficient": 1}, {"pattern": "I23", "coefficient": 2},
    ])
    nodes, proposition, differential = prepare_connection(workspace, body)
    assert len(nodes) == 1
    assert nodes[0].style["e2_components"] == {"I13": 1, "I23": 2}
    assert nodes[0].coefficient_context_id == "q8-residue-f4"
    assert not differential.display_coefficient
    assert "coefficient" not in proposition.conclusion
    assert proposition.status == "candidate"


def test_vector_collection_uses_f4_xor_and_rejects_zero(workspace):
    body = connection()
    body["target"]["terms"] = [{"pattern": "I13", "coefficient": 2},
                               {"pattern": "I13", "coefficient": 3}]
    nodes, _, _ = prepare_connection(workspace, body)
    assert nodes[0].style["e2_components"] == {"I13": 1}
    body["target"]["terms"][1]["coefficient"] = 2
    with pytest.raises(ValueError, match="zero vector"):
        prepare_connection(workspace, body)


@pytest.mark.parametrize("change", [
    {"page": True}, {"page": 1}, {"page": 3.5}, {"kind": "proved"},
    {"source": None},
    {"source": endpoint("source", 4.5, 4, "kD")},
    {"source": endpoint("source", 4, -1, "kD")},
    {"source": endpoint("source", 4, 4, "kD", two=-1)},
    {"source": endpoint("source", 4, 4, "kD", two=4)},
    {"source": endpoint("source", 4, 4, "kD", j=2)},
    {"target": endpoint("missing", 3, 9, "x")},
    {"target": endpoint("target", 4, 9, "x")},
    {"target": endpoint("target", 3, 10, "x")},
    {"target": endpoint("target", 3, 9, "")},
])
def test_invalid_candidate_is_rejected_before_workspace_changes(workspace, change):
    before = asdict(workspace)
    with pytest.raises(ValueError):
        prepare_connection(workspace, {**connection(), **change})
    assert asdict(workspace) == before


def test_cross_representation_and_mixed_vector_ports_are_not_silently_merged(workspace):
    workspace.classes[1].grade.representation = {"sigma_i": -1}
    with pytest.raises(ValueError, match="same representation"):
        prepare_connection(workspace, connection())
    workspace.classes[1].grade.representation = {}
    body = connection()
    body["target"]["terms"] = [{"pattern": "I13", "coefficient": 1, "two": 0},
                               {"pattern": "I23", "coefficient": 1, "two": 1}]
    with pytest.raises(ValueError, match="mixes coefficient levels"):
        prepare_connection(workspace, body)


@pytest.fixture
def api(workspace, monkeypatch):
    project = Project("test", "Atomic chart edit", workspaces=[workspace])
    calls = []
    monkeypatch.setattr(app_module, "load_project", lambda: project)
    monkeypatch.setattr(app_module, "checkpoint", lambda value, label: calls.append(("checkpoint", asdict(value))))
    monkeypatch.setattr(app_module, "sync_workspace_fates", lambda *args, **kwargs: calls.append(("sync", None)))
    monkeypatch.setattr(app_module, "save_project", lambda value: calls.append(("save", asdict(value))))
    return app_module.app.test_client(), project, calls


def test_route_applies_aliases_proposition_and_arrow_in_one_checkpoint(api):
    client, project, calls = api
    before = asdict(project)
    body = connection()
    body["source"].update(label="2kD", two=1)
    body["target"].update(label="2x", two=1)
    response = client.post("/api/workspaces/manual/chart-connections", json=body)
    assert response.status_code == 201, response.get_json()
    assert [name for name, _ in calls] == ["checkpoint", "sync", "save"]
    assert calls[0][1] == before
    workspace = project.workspaces[0]
    assert len(workspace.classes) == 6
    assert len(workspace.propositions) == len(workspace.differentials) == 1
    assert workspace.propositions[0].status == workspace.differentials[0].status == "candidate"


def test_route_relations_do_not_infer_differentials_or_algebraic_truth(api):
    client, project, calls = api
    body = {**connection(), "kind": "relation"}
    response = client.post("/api/workspaces/manual/chart-connections", json=body)
    assert response.status_code == 201, response.get_json()
    assert project.workspaces[0].differentials == []
    assert project.workspaces[0].propositions[0].status == "candidate"
    assert [name for name, _ in calls].count("checkpoint") == 1


@pytest.mark.parametrize("mutation", [
    lambda body: body.update(source={**body["source"], "grade": None}),
    lambda body: body.update(source={**body["source"], "grade": []}),
    lambda body: body["target"].update(terms=[None]),
    lambda body: body["target"].update(terms="I13"),
    lambda body: body["target"].update(terms=[{"pattern": None, "coefficient": 1}]),
    lambda body: body["target"].update(terms=[{"pattern": "missing", "coefficient": 1}]),
    lambda body: body["target"].update(two=True),
    lambda body: body["target"]["grade"].update(filtration=10),
    lambda body: body.update(kind="relation", chart_connection_kind="not-a-connection-kind"),
])
def test_route_rejects_bad_structure_grade_and_semantics_atomically(api, mutation):
    client, project, calls = api
    before = asdict(project)
    body = connection()
    mutation(body)
    response = client.post("/api/workspaces/manual/chart-connections", json=body)
    assert response.status_code == 400, response.data
    assert response.get_json()["error"]
    assert calls == [] and asdict(project) == before


def test_route_rejects_nonobject_json_atomically(api):
    client, project, calls = api
    before = asdict(project)
    response = client.post("/api/workspaces/manual/chart-connections", json=[])
    assert response.status_code == 400
    assert calls == [] and asdict(project) == before


def run_browser_helper(expression):
    script = r'''
const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync('backend/static/app.js','utf8');
function extract(name) {
  let start=source.indexOf(`function ${name}(`);
  if (source.slice(start-6,start)==='async ') start-=6;
  const rest=source.slice(start+1),next=/\n(?:async )?function\s/.exec(rest);
  return source.slice(start,next?start+1+next.index:source.length);
}
const context=vm.createContext({window:{HFPSSDisplayBasis:require('./backend/static/display-basis.js')},
  messages:[],requests:[],loads:0,
  workspace:()=>({page:5}),state:{workspaceId:'manual',connectionStart:'source',connectionOccurrence:{old:true},connectionPointer:{x:0}},
  toast(message){context.messages.push(message)},
  api:async(path,options)=>{context.requests.push({path,body:JSON.parse(options.body)})},
  loadProject:async()=>{context.loads++}});
for(const name of ['latexPower','shiftPeriodFactor','shiftDExponent','shiftKExponent',
  'periodicDisplayLabel','rawPeriodicDisplayLabel','f4DisplayMultiply','f4DisplayLatex',
  'selectedPortLabel','chartEndpointPayload','createDifferential']) vm.runInContext(extract(name),context);
Promise.resolve(vm.runInContext(EXPRESSION,context)).then(value=>process.stdout.write(JSON.stringify(value)));
'''
    result = subprocess.run(["node", "-e", script.replace("EXPRESSION", json.dumps(expression))],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True, timeout=10)
    return json.loads(result.stdout)


@pytest.mark.parametrize("port,expected", [("0:0", "kD"), ("1:0", "2kD"), ("2:0", "4kD")])
def test_frontend_payload_uses_clicked_two_adic_point_not_tower_midpoint(port, expected):
    result = run_browser_helper("""(() => {
      const record={item:{id:'source',label:'kD',style:{e2_pattern:'I04'}},grade:{stem:4,filtration:4},
        modulePorts:['0:0','1:0','2:0'],selectedPort:PORT};
      const before=JSON.stringify(record),payload=chartEndpointPayload(record);
      return {payload,unchanged:JSON.stringify(record)===before};
    })()""".replace("PORT", json.dumps(port)))
    assert result["unchanged"]
    assert result["payload"]["label"] == expected
    assert result["payload"]["two"] == int(port[0])


def test_frontend_validates_grade_before_post_and_keeps_source_selected():
    result = run_browser_helper("""(async() => {
      const source={item:{id:'source',label:'kD',style:{e2_pattern:'I04'}},grade:{stem:4,filtration:4}};
      const target={item:{id:'target',label:'x',style:{e2_pattern:'I13'}},grade:{stem:3,filtration:8}};
      await createDifferential(source,target);return {requests,messages,loads,state};
    })()""")
    assert not result["requests"] and not result["loads"]
    assert result["state"]["connectionStart"] == "source"
    assert "(3, 9)" in result["messages"][0]


def test_frontend_submits_one_candidate_request_with_exact_selected_ports():
    result = run_browser_helper("""(async() => {
      const source={item:{id:'source',label:'kD',style:{e2_pattern:'I04'}},grade:{stem:4,filtration:4},selectedPort:'2:0'};
      const target={item:{id:'target',label:'x',style:{e2_pattern:'I13'}},grade:{stem:3,filtration:9},selectedPort:'1:0'};
      await createDifferential(source,target);return {requests,messages,loads,state};
    })()""")
    assert len(result["requests"]) == result["loads"] == 1
    assert result["requests"][0]["body"]["source"]["label"] == "4kD"
    assert result["requests"][0]["body"]["target"]["label"] == "2x"
    assert result["state"]["connectionStart"] is None
    assert "no proof or periodic family" in result["messages"][0]
