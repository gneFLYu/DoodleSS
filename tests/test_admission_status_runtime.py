"""Verifier-marked facts must reach both the chart engine and its fate cache."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.fate import ACCEPTED_STATUSES, is_accepted
from domain.logic_graph import ADMITTED_PROPOSITION_STATUSES


def test_frontend_backend_and_verified_fact_statuses_agree():
    statuses = sorted(ACCEPTED_STATUSES | ADMITTED_PROPOSITION_STATUSES | {
        "review", "under-review", "rejected", "superseded", "source-proved", "candidate",
    })
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const context = vm.createContext({document: {body: {dataset: {}}}, window: {}});
const source = fs.readFileSync('backend/static/app.js', 'utf8');
vm.runInContext(source.slice(0, source.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
context.statuses = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(vm.runInContext(
  'statuses.map(status => differentialVisualState({status}) === "accepted")', context)));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(statuses),
                            text=True, capture_output=True, check=True, timeout=15)
    assert json.loads(result.stdout) == [is_accepted(status) for status in statuses]
    assert ADMITTED_PROPOSITION_STATUSES <= ACCEPTED_STATUSES
