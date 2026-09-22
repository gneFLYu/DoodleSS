"""Exact JS F4 quotients checked against the independent Python backend."""
from itertools import product
import json
from pathlib import Path
import random
import subprocess

from backend.domain.cell_linear_algebra import (
    in_span,
    matrix_vector_product,
    nullspace,
    quotient_basis,
    rref,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "backend" / "static" / "graded-quotient.js"
NAMES = ("0", "1", "zeta", "zeta^2")
NUMBERS = {name: index for index, name in enumerate(NAMES)}


def named(rows):
    return [[NAMES[value] for value in row] for row in rows]


def encoded(rows):
    return [[NUMBERS[value] for value in row] for row in rows]


def js(body, payload=None):
    program = (
        "const fs=require('fs'); const q=require(" + json.dumps(str(SCRIPT)) + ");"
        "const input=JSON.parse(fs.readFileSync(0,'utf8'));\n" + body
    )
    completed = subprocess.run(
        ["node", "-e", program], input=json.dumps(payload), text=True,
        capture_output=True, check=True, timeout=20,
    )
    return json.loads(completed.stdout)


def test_field_arithmetic_and_static_copies_are_exact():
    assert SCRIPT.read_bytes() == (ROOT / "public" / "static" / "graded-quotient.js").read_bytes()
    result = js("""
      const result={z2:q.mul('zeta','zeta'), cube:q.mul(2,3), sum:q.add(1,2),
        inverses:[1,2,3].map(q.inverse), latex:q.scalar('\\\\zeta^{2}'),
        commonjs:globalThis.HFPSSGradedQuotient===q};
      try {q.inverse(0)} catch(e) {result.zeroRejected=true}
      try {q.scalar(4)} catch(e) {result.wittRejected=true}
      const vm=require('vm'), browser={window:{}};
      vm.runInNewContext(fs.readFileSync(require.resolve(input),'utf8'),browser);
      result.browser=browser.window.HFPSSGradedQuotient.mul(2,2);
      console.log(JSON.stringify(result));
    """, str(SCRIPT))
    assert result == {
        "z2": 3, "cube": 1, "sum": 3, "inverses": [1, 3, 2], "latex": 3,
        "commonjs": True, "zeroRejected": True, "wittRejected": True, "browser": 3,
    }


def test_rref_and_nullspace_crosscheck_python_over_random_rectangular_matrices():
    rng = random.Random(20260920)
    examples = [
        {"columns": columns, "matrix": [[rng.randrange(4) for _ in range(columns)] for _ in range(rows)]}
        for rows in range(5) for columns in range(6) for _ in range(2)
    ]
    outputs = js("console.log(JSON.stringify(input.map(x=>({r:q.rref(x.matrix,{columns:x.columns}),k:q.nullspace(x.matrix,{columns:x.columns})}))));", examples)
    for example, output in zip(examples, outputs):
        rows, pivots = rref(named(example["matrix"]))
        assert output["r"]["rows"] == encoded(rows)
        assert output["r"]["pivots"] == pivots
        assert output["r"]["rank"] == len(pivots)
        assert output["k"] == encoded(nullspace(named(example["matrix"]), columns=example["columns"]))


def test_a_plus_b_boundary_leaves_one_dimension_and_identifies_the_two_classes():
    result = js("""
      const z=q.quotient({ambientDimension:2,cycles:[[1,0],[0,1]],boundaries:[[1,1]]});
      console.log(JSON.stringify({dimension:z.dimension,reps:z.representatives,p:z.projectionMatrix,
        a:z.tryProject([1,0]),b:z.tryProject([0,1]),boundary:z.tryProject([1,1]),strict:z.project([1,0]),lift:z.lift([2])}));
    """)
    assert result["dimension"] == 1
    assert result["reps"] == [[1, 0]]
    assert result["p"] == [[1, 1]]
    assert result["a"]["coordinates"] == result["b"]["coordinates"] == [1]
    assert result["boundary"]["coordinates"] == [0]
    assert result["strict"] == [1]
    assert result["lift"] == [2, 0]


def test_quotient_projection_crosschecks_python_and_never_projects_noncycles():
    rng = random.Random(43024)
    examples = []
    for n in range(6):
        for _ in range(5):
            cycles = [[rng.randrange(4) for _ in range(n)] for _ in range(4)]
            normalized, pivots = rref(named(cycles))
            cycle_basis = encoded(normalized[:len(pivots)])
            boundaries = cycle_basis[::2]
            if len(cycle_basis) >= 2:
                boundaries.append([a ^ b for a, b in zip(cycle_basis[0], cycle_basis[1])])
            examples.append({"ambientDimension": n, "cycles": cycles, "boundaries": boundaries})
    outputs = js("""
      console.log(JSON.stringify(input.map(x=>{const z=q.quotient(x);return {
        cycleBasis:z.cycleBasis,boundaryBasis:z.boundaryBasis,reps:z.representatives,p:z.projectionMatrix,
        projected:x.cycles.concat(x.boundaries).map(v=>z.tryProject(v))};})));
    """, examples)
    for example, result in zip(examples, outputs):
        expected = quotient_basis(named(result["cycleBasis"]), named(result["boundaryBasis"]))
        assert result["reps"] == encoded(expected)
        for vector, projected in zip(example["cycles"] + example["boundaries"], result["projected"]):
            assert projected["inCycles"]
            predicted = matrix_vector_product(named(result["p"]), [NAMES[v] for v in vector])
            assert projected["coordinates"] == [NUMBERS[v] for v in predicted]
            difference = [a ^ b for a, b in zip(vector, projected["representative"])]
            assert in_span([NAMES[v] for v in difference], named(result["boundaryBasis"]))
    restricted = js("""
      const z=q.quotient({ambientDimension:2,cycles:[[1,1]],boundaries:[]});
      let rejected=false;try {q.quotient({ambientDimension:2,cycles:[[1,1]],boundaries:[[1,0]]})}catch(e){rejected=/d_r/.test(e.message)}
      let strictRejected=false;try {z.project([1,0])}catch(e){strictRejected=e instanceof RangeError}
      console.log(JSON.stringify({outside:z.tryProject([1,0]),inside:z.tryProject([2,2]),rejected,strictRejected}));
    """)
    assert restricted["outside"] == {"inCycles": False, "coordinates": None, "representative": None}
    assert restricted["inside"]["coordinates"] == [2]
    assert restricted["rejected"]
    assert restricted["strictRejected"]


def test_partial_map_keeps_unspecified_directions_unknown_and_computes_known_kernel():
    result = js("""
      const d=q.partialMap({sourceDimension:2,targetDimension:1,constraints:[{source:[1,1],target:[0]}]});
      const empty=q.partialMap({sourceDimension:2,targetDimension:1,constraints:[]});
      console.log(JSON.stringify({consistent:d.consistent,total:d.isTotal,k:d.knownKernelBasis,
        a:d.evaluate([1,0]),b:d.evaluate([0,1]),sum:d.evaluate([1,1]),
        emptyKernel:empty.knownKernelBasis,emptyA:empty.evaluate([1,0])}));
    """)
    assert result["consistent"] and not result["total"]
    assert result["k"] == [[1, 1]]
    assert not result["a"]["defined"] and not result["b"]["defined"]
    assert result["sum"] == {"defined": True, "value": [0]}
    assert result["emptyKernel"] == []
    assert not result["emptyA"]["defined"]


def test_partial_map_crosscheck_on_every_vector_in_small_ambient_spaces():
    rng = random.Random(9876)
    examples = []
    ambient_vectors = [list(v) for v in product(range(4), repeat=3)]
    for count in range(5):
        actual_map = [[rng.randrange(4) for _ in range(3)] for _ in range(2)]
        sources = [[rng.randrange(4) for _ in range(3)] for _ in range(count)]
        targets = [
            [NUMBERS[v] for v in matrix_vector_product(named(actual_map), [NAMES[v] for v in source])]
            for source in sources
        ]
        examples.append({"actual": actual_map, "sourceDimension": 3, "targetDimension": 2,
                         "constraints": [{"source": a, "target": b} for a, b in zip(sources, targets)]})
    outputs = js("""
      console.log(JSON.stringify(input.examples.map(x=>{const d=q.partialMap(x);return{
        consistent:d.consistent,domain:d.domainBasis,kernel:d.knownKernelBasis,
        evaluated:input.vectors.map(v=>d.evaluate(v))};})));
    """, {"examples": examples, "vectors": ambient_vectors})
    for example, output in zip(examples, outputs):
        assert output["consistent"]
        sources = [constraint["source"] for constraint in example["constraints"]]
        for vector, evaluated in zip(ambient_vectors, output["evaluated"]):
            is_defined = in_span([NAMES[v] for v in vector], named(sources))
            assert evaluated["defined"] == is_defined
            actual = [NUMBERS[v] for v in matrix_vector_product(named(example["actual"]), [NAMES[v] for v in vector])]
            assert in_span([NAMES[v] for v in vector], named(output["kernel"])) == (is_defined and not any(actual))
            if is_defined:
                assert evaluated["value"] == actual
            else:
                assert evaluated["value"] is None


def test_conflicting_constraints_have_a_checkable_linear_dependency_witness():
    constraints = [
        {"id": "a", "source": [1, 0], "target": [1, 0]},
        {"id": "b", "source": [0, 1], "target": [0, 1]},
        {"id": "sum", "source": [2, 2], "target": [2, 3]},
    ]
    result = js("""
      const d=q.partialMap({sourceDimension:2,targetDimension:2,constraints:input});
      console.log(JSON.stringify({consistent:d.consistent,kernel:d.knownKernelBasis,images:d.images,
        conflicts:d.conflicts,evaluated:d.evaluate([0,0])}));
    """, constraints)
    assert not result["consistent"]
    assert result["kernel"] is None and result["images"] is None
    assert not result["evaluated"]["defined"]
    assert result["conflicts"]
    for witness in result["conflicts"]:
        weights = [NAMES[v] for v in witness["combination"]]
        source_columns = [[entry["source"][i] for entry in constraints] for i in range(2)]
        target_columns = [[entry["target"][i] for entry in constraints] for i in range(2)]
        assert matrix_vector_product(named(source_columns), weights) == ["0", "0"]
        residual = [NUMBERS[v] for v in matrix_vector_product(named(target_columns), weights)]
        assert residual == witness["targetResidual"] and any(residual)


def test_zero_dimensional_spaces_validation_and_input_immutability():
    result = js("""
      const basis=[[2,3],[1,1]],original=JSON.stringify(basis);
      q.rref(basis);q.reduce([2,2],basis);q.nullspace(basis);
      let invalid=0;for(const operation of [()=>q.rref([[1],[1,0]]),
        ()=>q.partialMap({sourceDimension:2,targetDimension:1,constraints:[{source:[1],target:[0]}]}),
        ()=>q.nullspace([],{columns:-1})])try{operation()}catch(e){invalid++}
      const z=q.quotient({ambientDimension:0,cycles:[],boundaries:[]});
      const d=q.partialMap({sourceDimension:2,targetDimension:0,constraints:[{source:[1,1],target:[]}]});
      console.log(JSON.stringify({unchanged:JSON.stringify(basis)===original,invalid,
        zero:z.tryProject([]),strict:z.project([]),dimension:z.dimension,kernel:d.knownKernelBasis,value:d.evaluate([2,2])}));
    """)
    assert result == {"unchanged": True, "invalid": 3, "zero": {"inCycles": True, "coordinates": [], "representative": []},
                      "strict": [], "dimension": 0, "kernel": [[1, 1]], "value": {"defined": True, "value": []}}
