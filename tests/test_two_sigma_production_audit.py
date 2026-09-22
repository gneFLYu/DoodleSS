"""Bounded production convergence, including undisplayed coefficient blocks.

No claim is admitted and no coefficient is assigned by this fixture.  The
existing conditional fixture currently has the same accepted-arrow set, but
this audit never rewrites those statuses.  It checks a larger finite range;
it is not a proof for arbitrary filtration or a general Leibniz verifier.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.fate import is_accepted
from domain.migrations import migrate_project
from domain.seed import demo_project


SOURCE = "ws_2sigma_i"
ATLAS = {SOURCE, "ws_q8-ro-a0-b2", "ws_q8-ro-a2-b2"}
PAGES = (22, 24)
FILTRATION_MAX = 96


@pytest.fixture(scope="module")
def production():
    return migrate_project(demo_project())


def images(project):
    result = [ws for ws in project.workspaces if ws.id == SOURCE or
              ws.settings.get("atlas_transport", {}).get("source_workspace_id") == SOURCE]
    assert {ws.id for ws in result} == ATLAS
    return result


def test_two_sigma_production_needs_no_counterfactual_admission(production):
    for ws in images(production):
        claims = {claim.id: claim for claim in ws.propositions}
        assert not ws.settings.get("coefficient_assignments")
        accepted = [row for row in ws.differentials if is_accepted(row.status)]
        pending = [row for row in ws.differentials if not is_accepted(row.status)]
        assert len(accepted) == 27 and len(pending) == 2
        assert {row.page for row in accepted} == {3, 5, 7, 9, 11, 13, 21}
        assert {row.label for row in pending} == {"FN-2I-002"}
        assert all(row.status == claims[row.proposition_id].status for row in accepted)
        assert all(is_accepted(claims[row.proposition_id].status) for row in accepted)
        # FN003 is a persisted admitted premise, not relabeled as an independent certificate.
        assert all(row.status == "admitted" for row in accepted if row.label == "FN-2I-003")
        assert all(not is_accepted(claims[row.proposition_id].status) for row in pending)
        assert all(node.style.get("e2_pattern") or node.style.get("e2_components")
                   for node in ws.classes if not node.archived)


@pytest.fixture(scope="module")
def late_production(production):
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    # Add read-only diagnostics to the actual chart harness.  In particular,
    # inspect quotient rank even when a renderer has not emitted a point.
    diagnostics = r"""
    const shift = ws.settings.atlas_transport?.stem_shift || 0;
    const sortEntries = value => Object.entries(value || {}).sort(([a], [b]) => a.localeCompare(b));
    const profiles = {"-1": [], "0": [], "1": []};
    for (const point of points) {
      const window = Math.floor((point.grade.stem - shift) / 64);
      const family = point.readOnlyRepresentative
        ? {terms: point.representativeTerms}
        : {pattern: point.item.style.e2_pattern || null,
           components: sortEntries(point.item.style.e2_components)};
      profiles[window].push(JSON.stringify({stem: point.grade.stem - shift - 64 * window,
        filtration: point.grade.filtration, family, ports: [...(point.modulePorts || [])].sort()}));
    }
    for (const profile of Object.values(profiles)) profile.sort();
    const coupledCells = new Set(), highVectorBlocks = [];
    let highVectorAudited = 0;
    for (const block of algebra.vectorBlocks.values()) {
      const [members, residue, filtrationText] = block.id.split(":"), filtration = Number(filtrationText);
      for (const pattern of members.split("+")) coupledCells.add(pattern + ":" + residue + ":" + filtrationText);
      if (filtration < 23 || filtration > input.auditFiltrationMax) continue;
      highVectorAudited++;
      if (block.q.dimension || block.barriers.length)
        highVectorBlocks.push({id: block.id, rank: block.q.dimension, barriers: block.barriers.length});
    }
    let highScalarAudited = 0;
    const highScalarPorts = [];
    for (const [key, ports] of algebra.cells) {
      const filtration = Number(key.split(":")[2]);
      if (coupledCells.has(key) || filtration < 23 || filtration > input.auditFiltrationMax) continue;
      highScalarAudited++;
      if (ports.size) highScalarPorts.push({key, ports: [...ports]});
    }
    const activeMaps = ws.differentials.map(diff => ({id: diff.id, label: diff.label,
      status: diff.status, canApply: algebra.canApply(diff), coefficient: algebra.coefficientState(diff)}));
    const lowPorts = [...algebra.ports({style: {e2_pattern: "I00"}}, {stem: shift + 40, filtration: 0})];
    return {profiles, highVectorAudited, highVectorBlocks, highScalarAudited, highScalarPorts,
      activeMaps, lowPorts, trustedFiltrationMax: algebra.trustedFiltrationMax,
      page, points: points.length"""
    payload = {"project": asdict(production), "pages": list(PAGES),
               "vectorAudit": True, "auditNoClipping": True,
               "auditFiltrationMax": FILTRATION_MAX}
    result = {}
    # Separate processes avoid retaining three complete page-algebra caches.
    # Keep the full project in each process for external coefficient sources.
    for ws in images(production):
        shift = ws.settings.get("atlas_transport", {}).get("stem_shift", 0)
        completed = subprocess.run(
            ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
            input=json.dumps({**payload, "workspaces": [ws.id],
                              "bounds": {"stemMin": shift - 64, "stemMax": shift + 127,
                                         "filtrationMin": 0, "filtrationMax": FILTRATION_MAX}}),
            text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
        )
        output = json.loads(completed.stdout)
        assert [row["id"] for row in output] == [ws.id]
        result[ws.id] = {row["page"]: row for row in output[0]["pages"]}
    return result


def test_production_late_quotients_include_every_finite_coefficient_block(late_production):
    assert set(late_production) == ATLAS
    for ident, pages in late_production.items():
        assert tuple(pages) == PAGES
        for page, row in pages.items():
            assert row["trustedFiltrationMax"] >= FILTRATION_MAX
            assert row["blockedFromPage"] is None and not row["conflicts"], (ident, page, row["conflicts"])
            assert not any(block["barriers"] for block in row["blocks"])
            assert not row["dangling"]
            assert row["highVectorAudited"] > 0 and row["highScalarAudited"] > 0
            assert not row["highVectorBlocks"], (ident, page, row["highVectorBlocks"])
            assert not row["highScalarPorts"], (ident, page, row["highScalarPorts"])
            assert row["high"] == 0 and row["unmappedHigh"] > 0
            assert "3:0" in row["lowPorts"] and "2:1" in row["lowPorts"]
            assert len([item for item in row["activeMaps"] if item["canApply"]]) == 27
            assert all(not item["canApply"] for item in row["activeMaps"] if item["label"] == "FN-2I-002")
            assert all(item["coefficient"]["resolved"] for item in row["activeMaps"] if item["canApply"])


def test_whole_d8_windows_and_final_pages_have_the_same_nonempty_profile(late_production):
    for ident, pages in late_production.items():
        for page, row in pages.items():
            assert row["profiles"]["0"], (ident, page)
            assert row["profiles"]["-1"] == row["profiles"]["0"] == row["profiles"]["1"], (ident, page)
        assert pages[22]["profiles"] == pages[24]["profiles"], ident
