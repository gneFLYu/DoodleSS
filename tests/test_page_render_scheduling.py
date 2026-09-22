"""Page events yield before rendering and only committed SVGs claim a new page."""
from pathlib import Path
import re

import pytest

from test_chart_display_conventions import app_helper


HELPERS = ["schedulePageRender", "setPage", "beginChartPageRender",
           "updateChartPageStatus", "markChartPageCommitted"]
SETUP = r"""
  const frames = [], renders = [];
  let nextFrame = 1, failure = null;
  const svg = {dataset: {renderedPage: '9', renderedWorkspace: 'ws'}, attributes: {'aria-busy': 'false'},
    setAttribute(key, value) { this.attributes[key] = value; }};
  const status = {textContent: 'Showing E9'}, caption = {textContent: '*-3i · E9'};
  globalThis.$ = selector => ({'#chart': svg, '#page-status': status, '#chart-caption': caption})[selector];
  globalThis.pageRenderFrame = 0;
  globalThis.pageRenderRequest = null;
  globalThis.chartPagePresentation = null;
  globalThis.state = {workspaceId: 'ws', project: {workspaces: [
    {id: 'ws', page: 9, grading_label: 'ws'}, {id: 'other', page: 3, grading_label: 'other'}]},
    pageByWorkspace: new Map(), connectionStart: 'source', candidateResults: {}, periodicityPreview: {},
    drawingPeriodicityPreview: {}, connectionPointer: {x: 1, y: 2}};
  globalThis.workspace = () => state.project.workspaces.find(ws => ws.id === state.workspaceId);
  globalThis.clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  globalThis.pageLimit = () => 25;
  globalThis.pageStatusText = ws => `Showing E${ws.page}`;
  globalThis.requestAnimationFrame = callback => {frames.push(callback); return nextFrame++;};
  globalThis.render = () => {
    const ws = workspace();
    renders.push({workspace: ws.id, page: ws.page});
    beginChartPageRender(ws);
    updateChartPageStatus(ws, `Computed E${ws.page}`);
    if (failure === 'before-commit') throw Error('render failed');
    markChartPageCommitted(svg, ws);
    if (failure === 'after-commit') throw Error('controls failed');
  };
  const flush = () => frames.shift()();
  const snapshot = () => JSON.parse(JSON.stringify({svg, status, caption, renders,
    pending: pageRenderRequest, frames: frames.length, current: workspace()}));
"""


def evaluate(body):
    return app_helper(HELPERS, "(() => {" + SETUP + body + "})()")['result']


def test_page_event_writes_state_immediately_but_yields_before_render():
    result = evaluate("""
      setPage('10');
      return {snapshot: snapshot(), remembered: state.pageByWorkspace.get('ws'),
        cleared: ['connectionStart', 'candidateResults', 'periodicityPreview',
          'drawingPeriodicityPreview', 'connectionPointer'].every(key => state[key] === null)};
    """)
    row = result['snapshot']
    assert row['current']['page'] == result['remembered'] == 10
    assert result['cleared'] is True
    assert row['renders'] == [] and row['frames'] == 1
    assert row['svg']['attributes']['aria-busy'] == 'true'
    assert row['svg']['dataset'] == {'renderedPage': '9', 'renderedWorkspace': 'ws',
                                     'requestedPage': '10', 'requestedWorkspace': 'ws'}
    assert row['caption']['textContent'] == 'Rendering E10; chart still E9'
    assert row['status']['textContent'] == row['caption']['textContent']


def test_rapid_page_changes_coalesce_into_one_latest_page_render():
    row = evaluate("""
      setPage(10); setPage(9); setPage(11);
      const pending = snapshot();
      flush();
      return {pending, done: snapshot()};
    """)
    assert row['pending']['frames'] == 1
    assert row['pending']['svg']['dataset']['requestedPage'] == '11'
    assert row['pending']['svg']['dataset']['renderedPage'] == '9'
    assert row['pending']['caption']['textContent'] == 'Rendering E11; chart still E9'
    assert row['done']['renders'] == [{'workspace': 'ws', 'page': 11}]
    assert row['done']['frames'] == 0 and row['done']['pending'] is None
    assert row['done']['svg']['dataset'] == {'renderedPage': '11', 'renderedWorkspace': 'ws'}
    assert row['done']['svg']['attributes']['aria-busy'] == 'false'
    assert row['done']['caption']['textContent'] == 'ws · E11'
    assert row['done']['status']['textContent'] == 'Computed E11'


@pytest.mark.parametrize('requested,expected', [('2', 2), ('9', 9), ('10', 10), ('1', 2), ('99', 25)])
def test_existing_page_clamping_semantics_are_preserved(requested, expected):
    row = evaluate(f"setPage('{requested}'); flush(); return snapshot();")
    assert row['current']['page'] == expected
    assert row['renders'] == [{'workspace': 'ws', 'page': expected}]
    assert row['svg']['dataset']['renderedPage'] == str(expected)


@pytest.mark.parametrize('switch_workspace', [False, True])
def test_stale_request_never_overwrites_a_synchronous_page_or_workspace_render(switch_workspace):
    change = "state.workspaceId = 'other';" if switch_workspace else 'workspace().page = 7;'
    row = evaluate("setPage(10);" + change + "render(); const committed = snapshot(); flush(); return {committed, after: snapshot()};")
    assert row['after']['svg'] == row['committed']['svg']
    assert row['after']['caption'] == row['committed']['caption']
    assert row['after']['renders'] == row['committed']['renders']
    assert row['after']['frames'] == 0
    assert row['after']['svg']['dataset']['renderedWorkspace'] == ('other' if switch_workspace else 'ws')
    assert row['after']['svg']['dataset']['renderedPage'] == ('3' if switch_workspace else '7')


def test_new_workspace_page_request_replaces_the_pending_old_workspace_request():
    row = evaluate("""
      setPage(10); state.workspaceId = 'other'; setPage(7);
      const pending = snapshot(); flush(); return {pending, after: snapshot()};
    """)
    assert row['pending']['frames'] == 1
    assert row['pending']['caption']['textContent'] == 'Rendering E7; chart still previous workspace E9'
    assert row['after']['renders'] == [{'workspace': 'other', 'page': 7}]
    assert row['after']['svg']['dataset'] == {'renderedPage': '7', 'renderedWorkspace': 'other'}
    assert row['after']['caption']['textContent'] == 'other · E7'


def test_render_failure_keeps_old_commit_and_reports_that_new_page_is_not_shown():
    row = evaluate("""
      failure = 'before-commit'; setPage(10); flush(); return snapshot();
    """)
    assert row['current']['page'] == 10
    assert row['svg']['dataset']['renderedPage'] == '9'
    assert row['svg']['dataset']['renderedWorkspace'] == 'ws'
    assert row['svg']['dataset']['requestedPage'] == '10'
    assert row['svg']['dataset']['renderError'] == 'render failed'
    assert row['svg']['attributes']['aria-busy'] == 'false'
    assert 'previous chart is retained' in row['status']['textContent']
    assert 'E10 not rendered' in row['caption']['textContent']


def test_retry_clears_failure_only_when_the_new_svg_is_committed():
    row = evaluate("""
      failure = 'before-commit'; setPage(10); flush();
      failure = null; setPage(11); const pending = snapshot();
      flush(); return {pending, after: snapshot()};
    """)
    assert row['pending']['svg']['dataset']['renderedPage'] == '9'
    assert row['pending']['svg']['attributes']['aria-busy'] == 'true'
    assert 'renderError' not in row['pending']['svg']['dataset']
    assert row['after']['svg']['dataset'] == {'renderedPage': '11', 'renderedWorkspace': 'ws'}
    assert row['after']['svg']['attributes']['aria-busy'] == 'false'


def test_post_commit_controls_error_does_not_misreport_the_new_svg_as_the_old_page():
    row = evaluate("""
      failure = 'after-commit'; setPage(10); flush(); return snapshot();
    """)
    assert row['svg']['dataset']['renderedPage'] == '10'
    assert row['svg']['dataset']['renderError'] == 'controls failed'
    assert row['caption']['textContent'] == 'ws · E10'
    assert row['status']['textContent'].startswith('E10 chart updated, but page controls failed:')


def test_algebra_and_candidate_status_remain_pending_until_the_svg_commit():
    row = evaluate("""
      setPage(10);
      beginChartPageRender(workspace());
      updateChartPageStatus(workspace(), 'E10 quotient has one survivor.');
      updateChartPageStatus(workspace(), 'One unresolved candidate.', true);
      const pending = snapshot();
      markChartPageCommitted(svg, workspace());
      return {pending, done: snapshot()};
    """)
    assert row['pending']['svg']['dataset']['renderedPage'] == '9'
    assert row['pending']['caption']['textContent'] == 'Rendering E10; chart still E9'
    assert row['pending']['status']['textContent'] == 'Rendering E10; chart still E9'
    assert row['done']['caption']['textContent'] == 'ws · E10'
    assert row['done']['status']['textContent'] == 'E10 quotient has one survivor. One unresolved candidate.'


def test_same_page_pan_can_refresh_status_without_reintroducing_pending_copy():
    row = evaluate("""
      setPage(10); flush();
      updateChartPageStatus(workspace(), 'Refreshed E10 quotient.');
      updateChartPageStatus(workspace(), 'No unresolved candidates.', true);
      return snapshot();
    """)
    assert row['svg']['attributes']['aria-busy'] == 'false'
    assert row['caption']['textContent'] == 'ws · E10'
    assert row['status']['textContent'] == 'Refreshed E10 quotient. No unresolved candidates.'


def test_initial_render_does_not_claim_a_previously_committed_page():
    row = evaluate("""
      svg.dataset = {}; setPage(2); const pending = snapshot(); flush();
      return {pending, done: snapshot()};
    """)
    assert row['pending']['caption']['textContent'] == 'Rendering E2; chart not yet rendered'
    assert 'renderedPage' not in row['pending']['svg']['dataset']
    assert row['done']['caption']['textContent'] == 'ws · E2'


def test_real_svg_commit_marks_the_page_after_replace_and_before_postprocessing():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'backend/static/app.js').read_text(encoding='utf-8')
    body = source.split('function renderChart() {', 1)[1].split('\nfunction ', 1)[0]
    assert body.index('replaceSvgMarkup(svg, markup);') < body.index('markChartPageCommitted(svg, ws);')
    assert body.index('markChartPageCommitted(svg, ws);') < body.index('renderMathInChart(m);')
    full_render = source.split('function render() {', 1)[1].split('\nfunction ', 1)[0]
    assert 'beginChartPageRender(ws);' in full_render
    assert '$("#chart-caption").textContent =' not in full_render
    assert '$("#page-status").textContent =' not in full_render
    assert '$("#page-status").textContent' not in body
    page = re.split(r'\n(?:async )?function ', source.split('function setPage(page) {', 1)[1], maxsplit=1)[0]
    assert 'schedulePageRender();' in page and 'render();' not in page and 'api(' not in page
    assert (root / 'backend/static/app.js').read_bytes() == (root / 'public/static/app.js').read_bytes()
