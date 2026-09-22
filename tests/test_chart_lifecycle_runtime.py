"""Behavioral regression checks for periodic occurrences, not JS string checks."""
import json
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from domain.migrations import migrate_project
from domain.seed import demo_project


@pytest.fixture(scope='module')
def chart_audit():
    result = subprocess.run(
        ['node', 'tests/chart_runtime.cjs'], cwd=ROOT, text=True,
        input=json.dumps({'project': asdict(migrate_project(demo_project())),
                         'workspaces': ['ws_integer', 'ws_sigma_i'],
                         'auditNoClipping': True,
                         'tableOccurrenceAudit': True,
                         'pages': [3, 4, 5, 6, 7, 8, 9, 11, 13, 17, 23, 24],
                         'probes': [{'pattern':p,'stem':s,'filtration':f} for p,s,f in [
                             ('I00',0,0), ('I00',8,0), ('I00',16,0), ('I00',32,0),
                             ('I33',43,3), ('I31',3,1), ('I00',20,4), ('S11',1,1), ('S40',4,0)]]}),
        capture_output=True, check=True, encoding='utf-8',
    )
    return json.loads(result.stdout)


def test_rendered_arrows_have_live_periodic_endpoints(chart_audit):
    invalid = [(w['id'], p['page'], p['dangling']) for w in chart_audit
               for p in w['pages'] if p['dangling']]
    assert not invalid, invalid


def test_witt_kernels_j_quotients_and_permanent_unit(chart_audit):
    def ports(ws, page, pattern, stem):
        row = next(p for w in chart_audit if w['id'] == ws for p in w['pages'] if p['page'] == page)
        return set(next(p['ports'] for p in row['probes'] if p['pattern'] == pattern and p['stem'] == stem))
    assert '0:0' in ports('ws_integer',24,'I00',0)  # neither 1 nor D^8 dies
    assert {'0:0','1:0'}.isdisjoint(ports('ws_integer',6,'I00',8))
    assert '2:0' in ports('ws_integer',6,'I00',8)  # 4D survives d5
    assert '0:0' not in ports('ws_integer',6,'I00',16)
    assert '1:0' in ports('ws_integer',6,'I00',16)  # 2D^2 survives d5
    assert '1:0' in ports('ws_integer',8,'I00',32)  # 2D^4 survives d7
    assert ports('ws_integer',23,'I33',43) == {'0:0'}  # d23 source, positive j tail already hit
    assert ports('ws_sigma_i',4,'S11',1) == {'0:1'}  # C's permanent bo tail
    assert '1:0' in ports('ws_sigma_i',4,'S40',4)  # 2v1^2u survives d3


def test_all_printed_table_anchors_survive_to_their_claimed_page(chart_audit):
    invalid = [(w['id'], p['page'], a) for w in chart_audit for p in w['pages']
               for a in p['anchors'] if a['id'].startswith('published_diff_')
               and (a['sourceDead'] or a['targetDead'])]
    assert not invalid, invalid


def test_every_table_and_derived_family_reaches_the_actual_renderer(chart_audit):
    for workspace in chart_audit:
        rows = {row for page in workspace['pages'] for row in page['rows']}
        expected = (24, 13) if workspace['id'] == 'ws_integer' else (22, 6)
        assert sum(row.startswith('published_diff_') for row in rows) == expected[0]
        assert sum(row.startswith('leibniz_diff_') for row in rows) == expected[1]


def test_each_printed_row_draws_its_anchor_d8_short_repeat_and_g_translates(chart_audit):
    project = migrate_project(demo_project())
    expected_page_counts = {
        'ws_integer': {3: 1, 5: 1, 7: 3, 9: 8, 11: 4, 13: 4, 23: 3},
        'ws_sigma_i': {3: 2, 5: 2, 9: 8, 11: 6, 13: 1, 17: 1, 23: 2},
    }
    for audit in chart_audit:
        workspace = next(w for w in project.workspaces if w.id == audit['id'])
        nodes = {node.id: node for node in workspace.classes}
        for page in audit['pages']:
            originals = [d for d in workspace.differentials
                         if d.id.startswith('published_diff_') and d.page == page['page']]
            assert len(originals) == expected_page_counts[workspace.id].get(page['page'], 0)
            rendered = {(item['id'], item['source']['stem'], item['source']['filtration'],
                         item['target']['stem'], item['target']['filtration'])
                        for item in page['tableOccurrences']}
            for row in originals:
                source, target = nodes[row.source_id].grade, nodes[row.target_id].grade
                # These are distinct operations: permanent D^8, a row's
                # repeated pattern, and forward multiplication by g=kD^3.
                # Assert actual arrows, not merely period metadata. Never
                # treat inverse-g or a short repeat as a permanent unit.
                shifts = {(0, 0), (64, 0), (row.period_stem, 0),
                          (20, 4), (row.period_stem + 20, 4)}
                for stem_shift, filtration_shift in shifts:
                    if source.stem + stem_shift > 127:
                        continue  # outside this fixture's viewport
                    assert (row.id, source.stem + stem_shift, source.filtration + filtration_shift,
                            target.stem + stem_shift, target.filtration + filtration_shift) in rendered


def test_vanishing_line_follows_from_maps_not_filtration_clipping(chart_audit):
    # Three adjacent D^8 blocks and f=23..64: both the boundary and well
    # above it. Disabling the actual maps must restore the E2 occurrences.
    for workspace in chart_audit:
        stable = next(page for page in workspace['pages'] if page['page'] == 24)
        before = next(page for page in workspace['pages'] if page['page'] == 23)
        assert before['high'] > 0
        assert stable['high'] == 0, stable['highPatterns']
        assert stable['unmappedHigh'] > 0


def test_witt_square_is_not_used_for_finite_positive_filtration_two_towers(chart_audit):
    early = next(p for w in chart_audit if w['id'] == 'ws_integer' for p in w['pages'] if p['page'] == 3)
    def glyph(pattern, stem):
        return next(p['glyph'] for p in early['probes'] if p['pattern'] == pattern and p['stem'] == stem)
    assert glyph('I00', 0) == 'witt-j-series'
    assert glyph('I31', 3) == 'finite-two-tower'
    assert glyph('I00', 20) == 'finite-two-tower'
