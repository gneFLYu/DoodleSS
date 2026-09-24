"""Noncritical requests and optional typesetting must not gate the chart."""
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backend/static/app.js"


def run_startup_test(body, functions):
    script = r"""
const fs = require('fs'), vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const source = fs.readFileSync(input.path, 'utf8');
function extract(name) {
  const match = new RegExp(`(?:async )?function ${name}\\(`).exec(source);
  const next = /\n(?:async )?function\s/.exec(source.slice(match.index + 1));
  return source.slice(match.index, next ? match.index + 1 + next.index : source.length);
}
const calls = [], pending = [], controls = new Map();
const ctx = {calls, pending, console, encodeURIComponent, decodeURIComponent,
  state: {workspaceId: null, project: null, pageByWorkspace: new Map(), catalogEntries: []},
  projectLoadSequence: 0, historyLoadSequence: 0, catalogManifestRequest: null,
  api: path => {calls.push(path); return new Promise((resolve,reject)=>pending.push({path,resolve,reject}));},
  workspace: () => ctx.state.project?.workspaces.find(w=>w.id===ctx.state.workspaceId),
  defaultWorkspaceId: () => ctx.state.project.workspaces[0].id,
  pageLimit: () => 25, clamp: (n,a,b) => Math.min(b,Math.max(a,n)),
  refreshSelectedOccurrence: () => calls.push('selection'), render: () => calls.push('render'),
  renderHistoryControls: () => calls.push('history-render'), toast: message=>calls.push(message),
  renderGradingAtlas: () => calls.push('atlas'), escapeHtml: String,
  $: key => {if (!controls.has(key)) controls.set(key, {}); return controls.get(key);},
  project: () => ({workspaces:[{id:'w',page:2}]}),
};
vm.createContext(ctx);
vm.runInContext(input.functions.map(extract).join('\n'),ctx);
Promise.resolve(vm.runInContext(`(async()=>{${input.body}})()`,ctx)).then(result=>process.stdout.write(JSON.stringify(result))).catch(e=>{console.error(e);process.exitCode=1;});
"""
    result = subprocess.run(["node", "-e", script], input=json.dumps({
        "path": str(APP), "body": body, "functions": functions,
    }), text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    return json.loads(result.stdout)


def test_chart_paints_before_history_or_archive_and_history_failure_is_nonfatal():
    result = run_startup_test("""
      const loading=loadProject(); pending[0].resolve(project()); await loading;
      const before=[...calls]; pending[1].reject(new Error('offline'));
      await Promise.resolve(); await Promise.resolve();
      return {before, after:calls, loaded:!!state.project};
    """, ["loadProject", "refreshHistory"])
    assert result["before"] == ["/api/project", "selection", "render", "/api/history"]
    assert result["loaded"]
    assert "history unavailable: offline" in result["after"][-1]


def test_out_of_order_project_and_history_requests_cannot_restore_stale_controls():
    result = run_startup_test("""
      const a=loadProject(), b=loadProject();
      pending[1].resolve(project()); await b;
      pending[0].resolve({workspaces:[{id:'stale',page:2}]}); await a;
      const c=loadProject(); pending[3].resolve(project()); await c;
      pending[4].resolve({undo_depth:2}); await Promise.resolve();
      pending[2].resolve({undo_depth:99}); await Promise.resolve();
      return {id:state.workspaceId,history:state.history,calls};
    """, ["loadProject", "refreshHistory"])
    assert result["id"] == "w"
    assert result["history"]["undo_depth"] == 2
    assert result["calls"].count("render") == 2
    assert result["calls"].count("history-render") == 1


def test_archive_is_deduplicated_cached_and_retryable_after_failure():
    result = run_startup_test("""
      let a=loadLegacyCatalogManifest(), b=loadLegacyCatalogManifest();
      pending[0].reject(new Error('offline'));
      await Promise.allSettled([a,b]);
      a=loadLegacyCatalogManifest(); pending[1].resolve({entries:[{id:'archive',status:'source',title:'Original'}]}); await a;
      await loadLegacyCatalogManifest();
      return {calls,entries:state.catalogEntries};
    """, ["loadLegacyCatalogManifest"])
    assert result["calls"] == ["/api/v2/legacy-catalog", "/api/v2/legacy-catalog"]
    assert result["entries"][0]["id"] == "archive"


def test_newer_history_on_same_project_wins_after_page_limit_edit():
    result = run_startup_test("""
      const loading=loadProject(); pending[0].resolve(project()); await loading;
      const edited=refreshHistory(state.project, projectLoadSequence);
      pending[2].resolve({undo_depth:1}); await edited;
      pending[1].resolve({undo_depth:0}); await Promise.resolve();
      return state.history;
    """, ["loadProject", "refreshHistory"])
    assert result["undo_depth"] == 1
    source = APP.read_text(encoding="utf-8").split("async function extendPageLimit()", 1)[1].split("function setTool", 1)[0]
    assert "await refreshHistory(state.project, projectLoadSequence)" in source


def test_optional_external_assets_are_nonblocking_and_have_late_math_hydration():
    from html.parser import HTMLParser
    assets = []

    class Assets(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag in ("script", "link") and str(attrs.get("src", attrs.get("href", ""))).startswith("https://"):
                assets.append((tag, attrs))

    Assets().feed((ROOT / "backend/templates/index.html").read_text(encoding="utf-8"))
    for tag, attrs in assets:
        if tag == "script":
            assert "async" in attrs
            assert "math-renderer-ready" in attrs["onload"]
        elif attrs.get("rel") == "stylesheet":
            assert attrs["media"] == "print"
            assert "this.media='all'" in attrs["onload"]
    source = APP.read_text(encoding="utf-8")
    assert 'window.addEventListener("math-renderer-ready", hydrateMathLabels)' in source
    assert 'node.outerHTML = mathMarkup(decodeURIComponent(node.dataset.mathSource))' in source
    startup = source.split('if (PAGE_MODE === "reviewing") bindReviewEvents();', 1)[1]
    assert "loadLegacyCatalogManifest" not in startup


def test_same_render_reuses_algebra_without_changing_cross_render_invalidation():
    source = APP.read_text(encoding="utf-8")
    assert "periodicDifferentials(ws, buffered, candidateDiagnostics, algebra)" in source
    assert "packedClassInstances(ws, buffered, m, previewInstances, presentation, algebra)" in source
    assert "periodicRelations(ws, liveIds, buffered, algebra)" in source
    assert (ROOT / "public/static/app.js").read_bytes() == APP.read_bytes()
