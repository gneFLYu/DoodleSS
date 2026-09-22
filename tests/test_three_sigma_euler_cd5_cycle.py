"""A completed low CD5 cycle does not restore its positive-g boundaries.

Euler exactness supplies the constant direction; negative-source Tate d3
supplies the completed positive-j ideal.  The actual chart must retain both
low ports while still taking the positive-filtration primitive d3 quotient.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.seed import demo_project
from test_vector_page_invariants import runtime


FACT = "DER-3I-EULER-CD5-cycle"
ATLAS = {"ws_3sigma_i": 0, "ws_q8-ro-a0-b3": 0, "ws_q8-ro-a1-b1": 16}
D8_POWERS = (-1, 0, 1)
NONZERO = {power: f"formal_diff_three_d9_c_D{power}_euler_derived" for power in (3, 7)}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [w for w in project.workspaces if w.id == "ws_3sigma_i" or
                w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert {w.id for w in selected} == set(ATLAS)
    return selected


def records(workspace):
    claims = [p for p in workspace.propositions if p.conclusion.get("fact_id") == FACT]
    assert len(claims) == 1
    claim = claims[0]
    source = next(n for n in workspace.classes if n.id == claim.conclusion["source_id"])
    return claim, source


def test_completed_cycle_certificate_in_all_three_atlas_images(project):
    for workspace in images(project):
        claim, source = records(workspace)
        data = claim.conclusion
        assert claim.kind == "permanent-cycle" and claim.status == "verified"
        assert data["admission_status"] == "verified" and data["page"] == 2
        assert data["cycle_constraint"] == "outgoing-only"
        assert data["coefficient_scope"] == "all-multiples"
        assert data["source_status"] == "independently-verified"
        assert not data["source_blockers"] and not data.get("withdrawn_dependencies")
        assert data["period_stem"] == 64
        assert data["forward_period"] == {
            "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
        }
        assert (source.grade.stem, source.grade.filtration) == (41 + ATLAS[workspace.id], 1)
        assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                source.style.get("j_order", 0)) == ("S11", 0, 0)
        assert not source.archived and source.page == 2
        certificate = data["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Adjusted Euler preimage and complete C4 filtration"
        assert certificate["source_refs"] and certificate["no_withdrawn_premise"] is True
        assert certificate["source_survival"]["ports"] == ["0:0", "0:1"]
        adjustment = certificate["restriction_adjustment"]
        assert adjustment["coefficient_ring"] == "W(F4)" and adjustment["coefficient_value"] is None
        assert adjustment["leading_class_preserved"] is True
        assert adjustment["filtrations"] == {"y": 2, "g_squared": 8}
        assert certificate["positive_j_cycle"]["source_bidegree"] == [42, -2]
        assert certificate["positive_j_cycle"]["target_bidegree"] == [41, 1]
        assert certificate["forward_boundary_control"]["target_port"] == "0:1"
        assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data["derived_from"])
        assert not any(d.proposition_id == claim.id or d.label == FACT for d in workspace.differentials)


def test_migration_restores_cycle_without_duplicate_sources_or_claims(project):
    candidate = deepcopy(project)
    expected = {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)}
    for workspace in images(candidate):
        claim, _ = records(workspace)
        workspace.propositions = [p for p in workspace.propositions if p.id != claim.id]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)} == expected


def probe(name, pattern, stem, filtration, j=0, two=0):
    return {"name": name, "pattern": pattern, "stem": stem, "filtration": filtration, "j": j, "two": two}


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes = []
    for workspace in workspaces:
        for d8 in D8_POWERS:
            stem = 41 + ATLAS[workspace.id] + 64*d8
            prefix = f"{workspace.id}:D8{d8}"
            probes += [probe(prefix+":low", "S11", stem, 1),
                       probe(prefix+":low-j", "S11", stem, 1, j=1),
                       probe(prefix+":g", "S11", stem+20, 5),
                       probe(prefix+":g-j", "S11", stem+20, 5, j=1),
                       probe(prefix+":d3-source", "S62V", stem+21, 2),
                       probe(prefix+":d3-source-j", "S62V", stem+21, 2, j=1),
                       probe(prefix+":potential-d11-target", "S40", stem-1, 12, two=1)]
            for power in NONZERO:
                control_stem = 8*power + 1 + ATLAS[workspace.id] + 64*d8
                control = prefix+f":CD{power}"
                probes += [probe(control+":source", "S11", control_stem, 1),
                           probe(control+":source-j", "S11", control_stem, 1, j=1),
                           probe(control+":target", "S02", control_stem-1, 10)]
    for d8 in D8_POWERS:
        probes += [probe(f"integer:D8{d8}:cD4", "I02", 40+64*d8, 2),
                   probe(f"integer:D8{d8}:cD4-j", "I02", 40+64*d8, 2, j=1)]
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces] + ["ws_integer"],
        "pages": [3, 4, 9, 10, 11, 12, 24], "vectorAudit": True,
        "pagesByWorkspace": {"ws_integer": [9, 10, 24]},
        "cycleProbes": probes, "fact": FACT, "nonzeroSuffixes": list(NONZERO.values()),
        "boundsByWorkspace": {
            w.id: {"stemMin": ATLAS[w.id]-48, "stemMax": ATLAS[w.id]+135,
                   "filtrationMin": 0, "filtrationMax": 12} for w in workspaces
        } | {"ws_integer": {"stemMin": -32, "stemMax": 112, "filtrationMin": 0, "filtrationMax": 3}},
    }
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    page_marker = "input.pages.map(page => {"
    assert harness.count(page_marker) == 1
    harness = harness.replace(page_marker, "(input.pagesByWorkspace?.[id] || input.pages).map(page => {")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {
      cycleProbes:input.cycleProbes.map(probe=>{
        const node={style:{e2_pattern:probe.pattern,two_valuation:probe.two,j_order:probe.j}};
        const grade={stem:probe.stem,filtration:probe.filtration};
        return {...probe,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      incomingD3:edges.filter(e=>e.diff.id.endsWith('formal_diff_three_d3_h1_2_derived'))
        .map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
          admitted:algebra.canApply(e.diff),status:e.diff.status})),
      nonzeroD9:edges.filter(e=>input.nonzeroSuffixes.some(s=>e.diff.id.endsWith(s)))
        .map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
          admitted:algebra.canApply(e.diff),status:e.diff.status})),
      lowInventory:points.filter(p=>p.grade.filtration<=1)
        .map(p=>({grade:p.grade,pattern:p.item.style.e2_pattern,ports:p.modulePorts})),
      cycleEdges:edges.filter(e=>e.diff.label===input.fact).length,
      page, points: points.length"""
    completed = subprocess.run(
        ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
        input=json.dumps(payload), text=True, encoding="utf-8",
        capture_output=True, check=True, timeout=180,
    )
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(completed.stdout)}


def observation(row, name):
    return next(item for item in row["cycleProbes"] if item["name"] == name)


def test_integer_euler_image_is_present_before_and_after_table8_d9(chart):
    for page in (9, 10, 24):
        row = chart["ws_integer"][page]
        for d8 in D8_POWERS:
            image = observation(row, f"integer:D8{d8}:cD4")
            assert image["live"] and image["ports"] == ["0:0"]
            assert not observation(row, f"integer:D8{d8}:cD4-j")["live"]
        assert row["blockedFromPage"] is None and not row["conflicts"]
        assert not row["dangling"]


@pytest.mark.parametrize("workspace_id", tuple(ATLAS))
def test_low_cd5_constant_and_completed_j_ideal_survive_all_tested_pages(chart, workspace_id):
    rows = chart[workspace_id]
    for d8 in D8_POWERS:
        prefix = f"{workspace_id}:D8{d8}"
        for page in (3, 10, 12, 24):
            for suffix in (":low", ":low-j"):
                low = observation(rows[page], prefix+suffix)
                assert low["live"] and low["ports"] == ["0:0", "0:1"]
            stem = 41 + ATLAS[workspace_id] + 64*d8
            inventory = [p for p in rows[page]["lowInventory"] if p["grade"]["stem"] == stem]
            assert inventory and all(p["grade"]["filtration"] == 1 and p["pattern"] == "S11"
                                     for p in inventory)
        for page in (11, 12):
            target = observation(rows[page], prefix+":potential-d11-target")
            assert target["live"] and target["ports"] == ["1:0"]
    for row in rows.values():
        assert row["blockedFromPage"] is None and not row["conflicts"]
        assert not row["dangling"] and row["cycleEdges"] == 0


@pytest.mark.parametrize("workspace_id", tuple(ATLAS))
def test_forward_g_j_ideal_is_the_actual_d3_image_and_never_returns(chart, workspace_id):
    rows = chart[workspace_id]
    for d8 in D8_POWERS:
        prefix = f"{workspace_id}:D8{d8}"
        before = observation(rows[3], prefix+":g")
        assert before["live"] and before["ports"] == ["0:0", "0:1"]
        assert observation(rows[3], prefix+":g-j")["live"]
        assert observation(rows[3], prefix+":d3-source")["live"]
        assert observation(rows[3], prefix+":d3-source-j")["live"]
        stem = 41 + ATLAS[workspace_id] + 64*d8
        edge = next(e for e in rows[3]["incomingD3"]
                    if e["target"]["stem"] == stem+20 and e["target"]["filtration"] == 5)
        assert edge["source"]["stem"] == stem+21 and edge["source"]["filtration"] == 2
        assert edge["admitted"] and edge["status"] == "verified"
        for page in (4, 10, 12, 24):
            constant = observation(rows[page], prefix+":g")
            assert constant["live"] and constant["ports"] == ["0:0"]
            assert not observation(rows[page], prefix+":g-j")["live"]
            assert not observation(rows[page], prefix+":d3-source")["live"]
            assert not observation(rows[page], prefix+":d3-source-j")["live"]


@pytest.mark.parametrize("workspace_id", tuple(ATLAS))
def test_other_d8_blocks_cd3_cd7_retain_their_nonzero_d9(chart, workspace_id):
    rows = chart[workspace_id]
    for d8 in D8_POWERS:
        for power, suffix in NONZERO.items():
            prefix = f"{workspace_id}:D8{d8}:CD{power}"
            before = observation(rows[9], prefix+":source")
            after = observation(rows[10], prefix+":source")
            assert before["live"] and before["ports"] == ["0:0", "0:1"]
            assert not after["live"] and after["ports"] == ["0:1"]
            assert observation(rows[10], prefix+":source-j")["live"]
            target_before = observation(rows[9], prefix+":target")
            target_after = observation(rows[10], prefix+":target")
            assert target_before["live"] and target_before["ports"] == ["0:0"]
            assert not target_after["live"] and not target_after["ports"]
            stem = 8*power + 1 + ATLAS[workspace_id] + 64*d8
            edge = next(e for e in rows[9]["nonzeroD9"] if e["id"].endswith(suffix)
                        and e["source"]["stem"] == stem and e["source"]["filtration"] == 1)
            assert edge["target"]["stem"] == stem-1 and edge["target"]["filtration"] == 10
            assert edge["admitted"] and edge["status"] == "verified"
    assert not rows[10]["nonzeroD9"]


@pytest.mark.parametrize("j", (0, 1))
def test_actual_certificate_blocks_d11_on_both_ports_but_allows_incoming(project, j):
    workspace = next(w for w in images(project) if w.id == "ws_3sigma_i")
    claim, _ = records(workspace)
    declaration = asdict(claim)
    declaration["conclusion"]["source_id"] = "cycle-anchor"
    declaration["conclusion"]["class_id"] = "cycle-anchor"
    # The hypothetical outgoing arrow is at the exact low certificate grade.
    # Incoming is tested at its forward-g image, where its source is genuinely
    # in nonnegative filtration. No artificial negative HFPSS row is inserted.
    # That source must also be a completed series: a j-annihilated finite
    # source cannot map nontrivially into the free F4[[j]] target module.
    result = runtime(r"""
      bounds.filtrationMax=16;
      helpers.accepted=record=>['proven','verified'].includes(record.status);
      helpers.copies=grade=>grade.stem===41&&grade.filtration===1
        ? [{grade},{grade:{stem:61,filtration:5}}] : [{grade}];
      const data=DECLARATION;
      console.log(JSON.stringify([false,true].map(incoming=>{
        const anchor=node('cycle-anchor','S11',41,1);
        const selected=node('selected','S11',incoming?61:41,incoming?5:1);
        selected.style.j_order=J_ORDER;
        const other=node('other',incoming?'S62V':'I13',incoming?62:40,incoming?2:12);
        const row=diff('hypothetical',incoming?other.id:selected.id,
          incoming?selected.id:other.id,incoming?3:11);
        const ws=workspace(incoming?4:12,[anchor,selected,other],[row],[structuredClone(data)]);
        const algebra=compute(ws);
        return {blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
          selectedLive:algebra.live(selected,selected.grade),otherLive:algebra.live(other,other.grade),
          ports:[...(algebra.ports(selected,selected.grade)||[])],admitted:algebra.canApply(row)};
      })));
    """.replace("DECLARATION", json.dumps(declaration)).replace("J_ORDER", str(j)))
    outgoing, incoming = result
    assert outgoing["blocked"] == 11 and outgoing["selectedLive"] and outgoing["otherLive"]
    assert not outgoing["admitted"]
    assert any("zero-outgoing cycle constraint" in item["reason"] for item in outgoing["conflicts"])
    assert incoming["blocked"] is None and not incoming["conflicts"], incoming
    assert not incoming["selectedLive"] and not incoming["otherLive"]
    assert incoming["ports"] == ([] if j == 0 else ["0:0"])
