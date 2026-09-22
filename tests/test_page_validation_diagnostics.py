"""All independent E_r validators report before an invalid quotient is blocked.

Abstract finite cells use the real page/vector engines and the shared synthetic
runtime.  No validator is mocked, and these examples assert no research formula.
"""
import pytest

from test_vector_page_invariants import runtime


FIXTURE = r"""
const makeFixture = (page, coupled, invalid) => {
  const staleTarget=node('stale-target','I73',5,7);
  const cycleSource=node('cycle-source','I13',20,1);
  const cycleTarget=node('cycle-target','I73',19,6);
  const chainSource=node('chain-source','S13',30,0);
  const chainMiddle=node('chain-middle','S53',29,5);
  const chainTarget=node('chain-target','S02',28,10);
  const goodSource=node('good-source','I13',40,0);
  const goodTarget=node('good-target','I73',39,5);
  const lateSource=node('late-source','I13',50,0);
  const lateTarget=node('late-target','I73',49,7);
  const observed=[staleTarget,cycleSource,cycleTarget,chainSource,chainMiddle,
    chainTarget,goodSource,goodTarget,lateSource,lateTarget];
  const claims=[{id:'cycle-guard',kind:'zero-differential',status:'proven',
    conclusion:{source_id:cycleSource.id,page:5,zero:true,coefficient_scope:'exact-port'}}];
  if(coupled) claims.push({id:'early-zero-B',kind:'zero-differential',status:'proven',
    conclusion:{source_id:B.id,page:3,zero:true}});
  const rows=[diff('early',A.id,T.id),
    diff('chain-first',chainSource.id,chainMiddle.id,5),
    diff('independent-good',goodSource.id,goodTarget.id,5),
    diff('later-good',lateSource.id,lateTarget.id,7)];
  if(invalid) rows.push(
    diff('stale-source',A.id,staleTarget.id,5),
    diff('cycle-contradiction',cycleSource.id,cycleTarget.id,5),
    diff('chain-second',chainMiddle.id,chainTarget.id,5));
  const nodes=[A,T,...(coupled?[B,AB]:[]),...observed];
  const ws=workspace(page,nodes,rows,claims), algebra=compute(ws);
  return {
    blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
    live:Object.fromEntries(nodes.map(n=>[n.id,algebra.live(n,n.grade)])),
    known:Object.fromEntries(nodes.map(n=>[n.id,algebra.knownCycle(n,n.grade)])),
    accepted:rows.map(d=>algebra.canApply(d)),
    goodMaps:algebra.maps(goodSource,goodTarget,goodSource.grade,goodTarget.grade).length,
    blocks:[...algebra.vectorBlocks.values()].map(b=>({rank:b.q.dimension,basis:b.q.representatives})),
    savedRows:ws.differentials.map(d=>d.id),
  };
};
"""


@pytest.mark.parametrize("page", (5, 6, 8))
@pytest.mark.parametrize("coupled,source_state", ((False, "zero"), (True, "noncycle")))
def test_all_three_diagnostics_survive_an_independent_invalid_source(page, coupled, source_state):
    result = runtime(FIXTURE +
                     f"console.log(JSON.stringify(makeFixture({page},{str(coupled).lower()},true)));")
    assert result["blocked"] == 5
    assert len(result["conflicts"]) == 3, result["conflicts"]
    stale = next(c for c in result["conflicts"] if c.get("id") == "stale-source")
    assert stale["page"] == 5 and stale["sourceState"] == source_state
    assert "source that is zero or not a cycle" in stale["reason"]
    cycle = next(c for c in result["conflicts"] if c.get("differential") == "cycle-contradiction")
    assert cycle["page"] == 5 and "zero-outgoing cycle constraint" in cycle["reason"]
    chain = next(c for c in result["conflicts"] if c.get("incoming") == "chain-first")
    assert chain["page"] == 5 and chain["outgoing"] == "chain-second"
    assert chain["reason"] == "d_r^2 != 0 through a scalar coefficient port"

    # E3 was committed, but no part of E5 (even its independent valid row)
    # or any later page may be committed after the three diagnostics.
    assert result["live"]["A"] is False and result["live"]["T"] is False
    assert all(live for ident, live in result["live"].items() if ident not in {"A", "T", "AB"})
    assert not any(result["known"].values()) and not any(result["accepted"])
    assert result["goodMaps"] == 0
    assert set(result["savedRows"]) == {
        "early", "chain-first", "chain-second", "independent-good", "later-good",
        "stale-source", "cycle-contradiction",
    }
    if coupled:
        assert result["blocks"] == [{"rank": 1, "basis": [[0, 1]]}]


@pytest.mark.parametrize("page", (6, 8))
def test_valid_fixture_still_commits_the_simultaneous_quotient_and_later_page(page):
    result = runtime(FIXTURE + f"console.log(JSON.stringify(makeFixture({page},true,false)));")
    assert result["blocked"] is None and not result["conflicts"]
    for ident in ("A", "T", "chain-source", "chain-middle", "good-source", "good-target"):
        assert result["live"][ident] is False, ident
    for ident in ("B", "stale-target", "cycle-source", "cycle-target", "chain-target"):
        assert result["live"][ident] is True, ident
    assert result["live"]["late-source"] is (page < 8)
    assert result["live"]["late-target"] is (page < 8)
    assert result["blocks"] == [{"rank": 1, "basis": [[0, 1]]}]
    assert all(result["accepted"])
