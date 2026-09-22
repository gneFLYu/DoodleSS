"""Only valid referenced matrices extend a declared target coefficient family."""
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("case", [
    "valid", "unused", "missing", "archived", "wrong_width", "wrong_height",
    "duplicate_basis", "invalid_basis", "source_archived", "target_archived",
    "diff_archived", "invalid_unit",
])
def test_only_valid_referenced_basis_creates_a_coupled_family(case):
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = vm.createContext({window: {}, input});
for (const name of ['graded-quotient', 'vector-page-algebra'])
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`, 'utf8'), context);
const result = vm.runInContext(`
const source = {id: 'source', coordinates: [1], style: {e2_pattern: 'X'}};
const target = {id: 'target', style: {e2_pattern: 'B', e2_basis_patterns: ['B','C']}};
const diff = {id: 'diff', source_id: 'source', target_id: 'target', linear_map_id: 'matrix'};
const matrix = {id: 'matrix', matrix: [[1], [1]]};
const ws = {classes: [source, target], differentials: [diff], differential_maps: [matrix]};
if (input.case === 'unused') ws.differentials = [];
if (input.case === 'missing') ws.differential_maps = [];
if (input.case === 'archived') matrix.archived = true;
if (input.case === 'wrong_width') source.coordinates = [1, 2];
if (input.case === 'wrong_height') matrix.matrix = [[1]];
if (input.case === 'duplicate_basis') target.style.e2_basis_patterns = ['B','B'];
if (input.case === 'invalid_basis') target.style.e2_basis_patterns = ['B','C:0'];
if (input.case === 'source_archived') source.archived = true;
if (input.case === 'target_archived') target.archived = true;
if (input.case === 'diff_archived') diff.archived = true;
if (input.case === 'invalid_unit') matrix.matrix = [[1], [7]];
const cells = new Map([['B:0:3', new Set(['0:0'])], ['C:0:3', new Set(['0:0'])]]);
const before = JSON.stringify(ws), beforeCells = JSON.stringify([...cells].map(([key,ports])=>[key,[...ports]]));
const conflicts = [];
const vectors = window.HFPSSVectorPageAlgebra.create(ws, cells, conflicts);
({blocks: [...vectors.blocks.values()].map(block=>({id:block.id,dimension:block.q.dimension,tokens:block.tokens})),
  unchanged: before===JSON.stringify(ws) && beforeCells===JSON.stringify([...cells].map(([key,ports])=>[key,[...ports]])),
  conflicts});
`, context);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps({"case": case}),
                            text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    output = json.loads(result.stdout)
    assert output["unchanged"] and not output["conflicts"]
    assert output["blocks"] == ([{"id": "B+C:0:3", "dimension": 2, "tokens": ["B:0:0", "C:0:0"]}]
                                if case == "valid" else [])


def test_public_vector_page_algebra_is_identical():
    assert (ROOT / "backend/static/vector-page-algebra.js").read_bytes() == (
        ROOT / "public/static/vector-page-algebra.js").read_bytes()
