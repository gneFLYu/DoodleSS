"""Regressions for page-level F4 invariants, using the actual browser modules.

These are small abstract local cells, not new claims about published classes.
Their pattern names select finite residue-field ports in the real engine.
"""
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]

RUNTIME = r"""
require('./backend/static/graded-quotient.js');
require('./backend/static/vector-page-algebra.js');
require('./backend/static/page-algebra.js');
const helpers = {
  copies: grade => [{grade}], classPeriods: () => [], diffPeriods: () => [],
  accepted: diff => diff.status === 'proven',
};
const bounds = {stemMin:0,stemMax:63,filtrationMin:0,filtrationMax:12};
const node = (id,pattern,stem,filtration,components) => ({
  id, label:id, grade:{stem,filtration}, page:2,
  style:components ? {e2_components:components} : {e2_pattern:pattern},
});
const diff = (id,source,target,page=3) => ({
  id, source_id:source, target_id:target, page, status:'proven',
});
const A = node('A','I62X',6,2), B = node('B','I62Y',6,2);
const AB = node('AB',null,6,2,{I62X:1,I62Y:1});
const T = node('T','I13',5,5), U = node('U','I73',4,8);
const workspace = (page,classes,differentials,propositions=[]) => ({
  page, settings:{}, classes, differentials, propositions,
});
const compute = ws => HFPSSPageAlgebra.compute(ws,bounds,helpers);
"""


def runtime(body):
    completed = subprocess.run(
        ["node", "-e", RUNTIME + body], cwd=ROOT, text=True,
        encoding="utf-8", capture_output=True, check=True, timeout=20,
    )
    return json.loads(completed.stdout)


def test_same_page_square_through_scalar_cell_cannot_erase_endpoints():
    """d3(A)=T, d3(T)=U violates d3² even though T is not a vector block."""
    result = runtime(r"""
      const zeroB = {id:'zeroB',kind:'zero-differential',status:'proven',
        conclusion:{source_id:'B',page:3,zero:true}};
      const ws = workspace(4,[A,B,AB,T,U],
        [diff('a','A','T'),diff('b','T','U')],[zeroB]);
      const algebra = compute(ws);
      console.log(JSON.stringify({
        live:[A,B,T,U].map(n=>algebra.live(n,n.grade)), conflicts:algebra.conflicts,
      }));
    """)
    assert result["live"] == [True, True, True, True], (
        "An inconsistent same-page map must not delete source or target ports."
    )
    assert result["conflicts"], "The nonzero d3² composition must be reported."


def test_unknown_prior_direction_is_not_an_accepted_later_differential():
    """Knowing d3(A) does not prove that B survives to support an accepted d5."""
    result = runtime(r"""
      const V=node('V','I73',5,7);
      const rows=[5,6].map(page=>{
        const ws=workspace(page,[A,B,AB,T,V],
          [diff('early','A','T'),diff('later','B','V',5)]);
        const algebra=compute(ws);
        return {page,acceptedMaps:algebra.maps(B,V,B.grade,V.grade).length,
          sourceLive:algebra.live(B,B.grade),targetLive:algebra.live(V,V.grade),
          conflicts:algebra.conflicts};
      });
      console.log(JSON.stringify(rows));
    """)
    assert all(row["acceptedMaps"] == 0 for row in result), (
        "Unknown cycle status must not be returned among accepted maps."
    )
    assert result[1]["sourceLive"] and result[1]["targetLive"], (
        "An unverified later differential must not erase either endpoint."
    )
    assert all(row["conflicts"] for row in result)


def test_new_kernel_basis_is_exposed_when_no_existing_class_names_it():
    """d3(A)=T, d3(B)=zeta*T leaves A+zeta² B, not A, B, or A+B."""
    result = runtime(r"""
      const zT=node('zT',null,5,5,{I13:2});
      const ws=workspace(4,[A,B,AB,T,zT],
        [diff('a','A','T'),diff('b','B','zT')]);
      const algebra=compute(ws);
      console.log(JSON.stringify({
        blocks:[...algebra.vectorBlocks.values()].map(b=>({
          rank:b.q.dimension,basis:b.q.representatives})),
        hasRepresentatives:typeof algebra.representatives==='function',
        representatives:algebra.representatives?.(bounds)||[],
        conflicts:algebra.conflicts,
      }));
    """)
    assert result["blocks"] == [{"rank": 1, "basis": [[1, 3]]}]
    assert not result["conflicts"]
    assert result["hasRepresentatives"], (
        "Every quotient basis needs a display representative, including unnamed combinations."
    )
    representatives = [
        item for item in result["representatives"]
        if item["grade"]["stem"] == 6 and item["grade"]["filtration"] == 2
    ]
    assert len(representatives) == 1
    representative = representatives[0]
    assert representative["slot"]
    assert sorted(representative["terms"], key=lambda term: term["pattern"]) == [
        {"pattern": "I62X", "two": 0, "j": 0, "coefficient": 1},
        {"pattern": "I62Y", "two": 0, "j": 0, "coefficient": 3},
    ]
