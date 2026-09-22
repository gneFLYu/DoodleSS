"""A Tate negative-source certificate supplies zero outgoing maps, not deaths.

These are abstract local modules run through the actual JavaScript engines.
They do not admit a new mathematical claim about any named Q8 class.
"""
from pathlib import Path

import pytest

from test_vector_page_invariants import runtime


CERTIFICATE = r"""
const cycle = (id, source, extra={}) => ({id,kind:'permanent-cycle',status:'proven',
  conclusion:{source_id:source,page:2,period_stem:64,cycle_constraint:'outgoing-only',
    coefficient_scope:'constant-two-multiples',
    forward_period:{stem:20,filtration:4,nonnegative:true},
    comparison_certificate:{spectral_sequence:'tate',page:3,source_bidegree:[7,-1],
      target_bidegree:[6,2],interpretation:'Never delete the HFPSS target.'},...extra}});
const summarize = (a,nodes,rows) => ({blocked:a.blockedFromPage,conflicts:a.conflicts,
  live:nodes.map(n=>a.live(n,n.grade)),known:nodes.map(n=>a.knownCycle(n,n.grade)),
  accepted:rows.map(row=>a.canApply(row))});
"""


@pytest.mark.parametrize("page", [3, 4, 6])
@pytest.mark.parametrize("kind", ["permanent-cycle", "zero-differential"])
def test_scalar_cycle_conflict_is_visible_on_its_page_and_never_erases_endpoints(page, kind):
    result = runtime(CERTIFICATE + r"""
      const S=node('S','I62X',6,2), p=cycle('cycle','S');
      p.kind='KIND';
      if(p.kind==='zero-differential') p.conclusion.page=3;
      const row=diff('out','S','T'), ws=workspace(PAGE,[S,T],[row],[p]);
      const a=compute(ws);
      console.log(JSON.stringify({...summarize(a,[S,T],[row]),
        maps:a.maps(S,T,S.grade,T.grade).length,rows:ws.differentials.length}));
    """.replace("PAGE", str(page)).replace("KIND", kind))
    assert result["blocked"] == 3
    assert result["live"] == [True, True]
    assert result["known"] == [False, False]
    assert result["accepted"] == [False] and result["maps"] == 0
    assert result["rows"] == 1  # no fabricated incoming Tate differential
    assert any("zero-outgoing cycle constraint" in item["reason"] for item in result["conflicts"])


def test_coupled_zero_conflict_blocks_later_maps_without_partially_taking_the_quotient():
    result = runtime(CERTIFICATE + r"""
      const V=node('V','I73',5,7), rows=[diff('bad','A','T'),diff('later','B','V',5)];
      const ws=workspace(6,[A,B,AB,T,V],rows,[cycle('cycleA','A'),cycle('cycleB','B')]);
      const a=compute(ws);
      console.log(JSON.stringify({...summarize(a,[A,B,T,V],rows),
        maps:a.maps(B,V,B.grade,V.grade).length}));
    """)
    assert result["blocked"] == 3
    assert result["live"] == [True] * 4 and result["known"] == [False] * 4
    assert result["accepted"] == [False, False] and result["maps"] == 0
    assert any("inconsistent linear constraints" in item["reason"] for item in result["conflicts"])


def test_scalar_square_zero_conflict_also_blocks_every_later_page():
    result = runtime(CERTIFICATE + r"""
      const S=node('S','I62X',6,2), V=node('V','I62Y',7,1), W=node('W','I13X',6,6);
      const rows=[diff('first','S','T'),diff('second','T','U'),diff('later','V','W',5)];
      const ws=workspace(6,[S,T,U,V,W],rows), a=compute(ws);
      console.log(JSON.stringify(summarize(a,[S,T,U,V,W],rows)));
    """)
    assert result["blocked"] == 3 and result["live"] == [True] * 5
    assert result["accepted"] == [False] * 3
    assert any("d_r^2 != 0" in item["reason"] for item in result["conflicts"])


@pytest.mark.parametrize("coupled", [False, True])
def test_cycle_certificate_allows_an_incoming_boundary(coupled):
    result = runtime(CERTIFICATE + r"""
      const S=node('S','I13',7,0), nodes=COUPLED ? [S,A,B,AB] : [S,A];
      const row=diff('incoming','S','A',2), p=cycle('cycleA','A');
      const ws=workspace(4,nodes,[row],COUPLED ? [p,cycle('cycleB','B')] : [p]), a=compute(ws);
      console.log(JSON.stringify(summarize(a,[S,A],[row])));
    """.replace("COUPLED", str(coupled).lower()))
    assert result["blocked"] is None and result["live"] == [False, False]
    assert not result["conflicts"]


def test_review_certificate_is_inert_and_does_not_create_a_tate_death():
    result = runtime(CERTIFICATE + r"""
      const S=node('S','I62X',6,2), p=cycle('review','S'); p.status='review';
      const row=diff('out','S','T'), ws=workspace(4,[S,T],[row],[p]), a=compute(ws);
      const noArrow=workspace(30,[S],[],[cycle('tate','S')]), b=compute(noArrow);
      console.log(JSON.stringify({review:summarize(a,[S,T],[row]),
        certificateOnly:summarize(b,[S],[]),rows:noArrow.differentials.length}));
    """)
    assert result["review"]["blocked"] is None and result["review"]["live"] == [False, False]
    assert not result["review"]["conflicts"]
    assert result["certificateOnly"]["live"] == [True]
    assert not result["certificateOnly"]["conflicts"] and result["rows"] == 0


def test_cycle_of_a_linear_combination_does_not_declare_both_columns_zero():
    result = runtime(CERTIFICATE + r"""
      const rows=[diff('dA','A','T'),diff('dB','B','T')];
      const ws=workspace(4,[A,B,AB,T],rows,[cycle('sumCycle','AB')]), a=compute(ws);
      console.log(JSON.stringify({...summarize(a,[A,B,AB,T],rows),
        basis:[...a.vectorBlocks.values()][0].q.representatives}));
    """)
    assert result["blocked"] is None and not result["conflicts"]
    assert result["live"] == [False, False, True, False]
    assert result["basis"] == [[1, 1]]


@pytest.mark.parametrize("two,j,blocked", [(0, 0, False), (1, 0, True), (2, 0, True), (1, 1, False)])
def test_constant_two_multiple_scope_preserves_other_witt_and_j_ports(two, j, blocked):
    result = runtime(CERTIFICATE + r"""
      const W=node('W','S40',4,0), twice=node('twice','S40',4,0);
      twice.style.two_valuation=1;
      const outgoing=node('outgoing','S40',4,0);
      outgoing.style.two_valuation=TWO; outgoing.style.j_order=JORDER;
      const target=node('target','I13',3,3), row=diff('row','outgoing','target');
      const ws=workspace(4,[W,twice,outgoing,target],[row],[cycle('pc','twice')]), a=compute(ws);
      console.log(JSON.stringify({...summarize(a,[twice,outgoing,target],[row]),
        ports:[...a.ports(W,W.grade)]}));
    """.replace("TWO", str(two)).replace("JORDER", str(j)))
    assert (result["blocked"] == 3) is blocked
    assert result["live"] == ([True, True, True] if blocked else [True, False, False])
    assert "0:1" in result["ports"] and "3:0" in result["ports"]
    if not blocked:
        assert not result["conflicts"]


def test_source_alias_status_scope_and_start_page_invalidate_the_same_object_cache():
    result = runtime(CERTIFICATE + r"""
      const W=node('W','S40',4,0), twice=node('twice','S40',4,0);
      twice.style.two_valuation=1;
      const target=node('target','I13',3,3), row=diff('out','twice','target');
      const p=cycle('pc',null,{class_id:'twice'}); p.status='review';
      const ws=workspace(4,[W,twice,target],[row],[p]), results=[];
      const first=compute(ws); results.push(first.blockedFromPage);
      p.status='proven'; const second=compute(ws); results.push(second.blockedFromPage);
      p.conclusion.page=5; const third=compute(ws); results.push(third.blockedFromPage);
      p.conclusion.page=2; p.conclusion.source_id='target';
      const fourth=compute(ws); results.push(fourth.blockedFromPage);
      console.log(JSON.stringify({results,distinct:first!==second&&second!==third&&third!==fourth,
        fourthLive:fourth.live(target,target.grade)}));
    """)
    assert result == {"results": [None, 3, None, None], "distinct": True, "fourthLive": False}


def test_changing_coefficient_scope_invalidates_the_cycle_constraint_cache():
    result = runtime(CERTIFICATE + r"""
      const twice=node('twice','S40',4,0), four=node('four','S40',4,0);
      twice.style.two_valuation=1; four.style.two_valuation=2;
      const target=node('target','I13',3,3), p=cycle('pc','twice');
      const ws=workspace(4,[twice,four,target],[diff('out','four','target')],[p]), first=compute(ws);
      p.conclusion.coefficient_scope='exact-port'; const second=compute(ws);
      console.log(JSON.stringify({first:first.blockedFromPage,second:second.blockedFromPage,
        distinct:first!==second,fourLive:second.live(four,four.grade),twiceLive:second.live(twice,twice.grade)}));
    """)
    assert result == {"first": 3, "second": None, "distinct": True, "fourLive": False, "twiceLive": True}


def test_certificate_transports_only_zero_outgoing_by_d8_and_forward_g():
    result = runtime(CERTIFICATE + r"""
      helpers.copies=(grade,periods,domain)=>{
        const result=[];
        for(let g=0;g<=2;g++) for(let d=-2;d<=2;d++){
          if(g&&!periods.some(p=>p.filtration===4&&p.domain==='nonnegative'))continue;
          if(d&&!periods.some(p=>p.stem===64&&p.filtration===0))continue;
          const v={stem:grade.stem+20*g+64*d,filtration:grade.filtration+4*g};
          if(v.stem>=domain.stemMin&&v.stem<=domain.stemMax&&v.filtration>=0&&v.filtration<=domain.filtrationMax) result.push({grade:v});
        }
        return result;
      };
      const seen=[];
      helpers.diffPeriods=(ws,row)=>{seen.push([row.id,row.period_stem,row.forward_period]);
        return row.zero?[{stem:row.period_stem,filtration:0},
          {stem:row.forward_period.stem,filtration:row.forward_period.filtration,domain:'nonnegative'}]:[];};
      const S=node('S','I62X',-58,2), image=node('image','I62X',26,6), target=node('target','I13',25,9);
      const lower=node('lower','I62X',50,2), lowerTarget=node('lowerTarget','I13',49,5);
      const p=cycle('pc','S'), row=diff('gD8','image','target');
      const ws=workspace(4,[S,image,target],[row],[p]), a=compute(ws);
      // Starting at filtration 6 cannot certify its inverse-g predecessor.
      const p2=cycle('higher','image'), b=compute(workspace(4,[image,lower,lowerTarget],
        [diff('inverseG','lower','lowerTarget')],[p2]));
      console.log(JSON.stringify({translated:summarize(a,[image,target],[row]),
        inverse:summarize(b,[lower,lowerTarget],[]),seen}));
    """)
    assert result["translated"]["blocked"] == 3
    assert result["translated"]["live"] == [True, True]
    assert result["inverse"]["blocked"] is None and result["inverse"]["live"] == [False, False]
    assert any(ident.startswith("pc@") and period == 64 and forward["nonnegative"]
               for ident, period, forward in result["seen"])


def test_legacy_permanent_certificate_never_inherits_a_short_differential_period():
    result = runtime(CERTIFICATE + r"""
      helpers.diffPeriods=(ws,row)=>[{stem:row.period_stem||16,filtration:0}];
      helpers.copies=(grade,periods,domain)=>{
        const period=periods[0]?.stem;
        if(!period)return[{grade}];
        const result=[];
        for(let n=-5;n<=5;n++){
          const v={...grade,stem:grade.stem+n*period};
          if(v.stem>=domain.stemMin&&v.stem<=domain.stemMax)result.push({grade:v});
        }
        return result;
      };
      const d8=node('D8','I00',64,0), d2=node('D2','I00',16,0), target=node('target','I13',15,5);
      const p={id:'legacy-D8',kind:'permanent-cycle',status:'proven',conclusion:{class_id:'D8'}};
      const row={...diff('d5','D2','target',5),period_stem:32};
      const a=compute(workspace(6,[d8,d2,target],[row],[p]));
      console.log(JSON.stringify(summarize(a,[d8,d2,target],[row])));
    """)
    assert result["blocked"] is None and not result["conflicts"]
    assert result["live"] == [True, False, False]


@pytest.mark.parametrize("page", [5, 6, 8])
@pytest.mark.parametrize("coupled,early_role", [(False, "outgoing"), (True, "outgoing"), (True, "incoming")])
def test_known_dead_source_to_live_target_blocks_only_from_the_invalid_page(page, coupled, early_role):
    result = runtime(CERTIFICATE + r"""
      const V=node('V','I73',5,7), W=node('W','I13',4,14), S=node('S','I13',7,0);
      const nodes=COUPLED ? [A,B,AB,T,V,W,S] : [A,T,V,W,S];
      const early=INCOMING ? diff('early','S','A',2) : diff('early','A','T');
      const rows=[early,diff('dead-source','A','V',5),diff('later','V','W',7)];
      const zeros=COUPLED ? [{id:'zeroB',kind:'zero-differential',status:'proven',
        conclusion:{source_id:'B',page:early.page,zero:true}}] : [];
      const a=compute(workspace(PAGE,nodes,rows,zeros));
      console.log(JSON.stringify({...summarize(a,[A,V,W],rows),
        invalidMaps:a.maps(A,V,A.grade,V.grade).length}));
    """.replace("PAGE", str(page)).replace("COUPLED", str(coupled).lower())
                      .replace("INCOMING", str(early_role == "incoming").lower()))
    assert result["blocked"] == 5 and result["live"] == [False, True, True]
    assert result["accepted"] == [False, False, False] and result["invalidMaps"] == 0
    conflict = next(item for item in result["conflicts"] if item.get("id") == "dead-source")
    assert conflict["page"] == 5
    assert conflict["sourceState"] == ("noncycle" if coupled and early_role == "outgoing" else "zero")


def test_zero_to_zero_product_row_is_redundant_not_a_contradiction():
    result = runtime(CERTIFICATE + r"""
      const V=node('V','I73',5,7), S=node('S','I13',6,4);
      const rows=[diff('killA','A','T'),diff('killV','S','V'),diff('redundant','A','V',5)];
      const a=compute(workspace(6,[A,T,S,V],rows));
      console.log(JSON.stringify(summarize(a,[A,T,S,V],rows)));
    """)
    assert result["blocked"] is None and result["live"] == [False] * 4
    assert result["conflicts"] == []


def test_partial_unknown_source_is_underdefined_not_a_proved_zero_source():
    result = runtime(CERTIFICATE + r"""
      const V=node('V','I73',5,7), rows=[diff('partial','A','T'),diff('unknown','B','V',5)];
      const a=compute(workspace(6,[A,B,AB,T,V],rows));
      console.log(JSON.stringify({...summarize(a,[B,V],rows),maps:a.maps(B,V,B.grade,V.grade).length}));
    """)
    assert result["blocked"] is None and result["live"] == [True, True]
    assert result["known"][0] is False and result["maps"] == 0
    assert any("proper subspace" in item["reason"] for item in result["conflicts"])
    assert not any("source that is zero or not a cycle" in item["reason"] for item in result["conflicts"])


def test_outer_halo_endpoint_is_unknown_even_when_an_e2_port_was_seeded():
    result = runtime(CERTIFICATE + r"""
      const high=node('high','I13',5,80), cells=new Map([['I13:5:80',new Set(['0:0'])]]);
      const vectors=HFPSSVectorPageAlgebra.create(workspace(4,[high],[]),cells,[],{filtrationMin:0,filtrationMax:64});
      const outer=vectors.endpoint(high,high.grade);
      // Each earlier quotient spends r levels of the allocated safe halo.
      const ws=workspace(8,[A,T],[]);
      ws.differentials=[{...diff('r3','A','T'),status:'review'},
        {...diff('r5','A','T',5),status:'review'},{...diff('r7','A','T',7),status:'review'}];
      const a=compute(ws);
      console.log(JSON.stringify({outer,maximum:a.trustedFiltrationMax,
        visible:a.inTrustedDomain({filtration:12}),beyond:a.inTrustedDomain({filtration:50})}));
    """)
    assert result["outer"]["unknown"] and result["outer"]["outsideDomain"]
    assert not result["outer"]["live"] and not result["outer"]["zero"]
    assert result["maximum"] == 64 - (3 + 5 + 7)
    assert result["visible"] and not result["beyond"]


@pytest.mark.parametrize("filtration,warning", [(2, True), (62, False)])
def test_partial_map_diagnostic_requires_a_fully_computable_successor_cell(filtration, warning):
    result = runtime(CERTIFICATE + r"""
      const a=node('a','I62X',6,FILTRATION), b=node('b','I62Y',6,FILTRATION);
      const ab=node('ab',null,6,FILTRATION,{I62X:1,I62Y:1});
      const t=node('t','I13',5,FILTRATION+5);
      const zero={id:'known-zero',kind:'zero-differential',status:'proven',
        conclusion:{source_id:'a',page:5,zero:true}};
      // A review arrow reserves the same d5 halo but does not complete d5(b).
      // At f62 its target is outside that halo; the missing direction must
      // not create a diagnostic about a cell outside the successor domain.
      const row={...diff('unknown','b','t',5),status:'review'};
      const algebra=compute(workspace(6,[a,b,ab,t],[row],[zero]));
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,
        warnings:algebra.conflicts.filter(c=>c.reason.includes('proper subspace')),
        blocks:[...algebra.vectorBlocks.values()].map(block=>({id:block.id,barriers:block.barriers.length})),
        representatives:algebra.representatives({...bounds,filtrationMax:80}),
        maximum:algebra.trustedFiltrationMax}));
    """.replace("FILTRATION", str(filtration)))
    assert result["blocked"] is None and result["maximum"] == 59
    assert bool(result["warnings"]) is warning
    assert bool(result["blocks"]) is warning
    assert bool(result["representatives"]) is warning
    if warning:
        assert result["blocks"][0]["barriers"] == 1


def test_all_46_published_rows_keep_runtime_coverage_at_the_finite_domain_boundary():
    # In the old fixed halo, a d23 j-tail source at filtration 77 was paired
    # with a freshly seeded target at filtration 100, beyond the computed 96.
    # The latter must not be mistaken for a known surviving target.
    from test_chart_lifecycle_runtime import (
        chart_audit,
        test_each_printed_row_draws_its_anchor_d8_short_repeat_and_g_translates,
        test_every_table_and_derived_family_reaches_the_actual_renderer,
        test_rendered_arrows_have_live_periodic_endpoints,
        test_vanishing_line_follows_from_maps_not_filtration_clipping,
    )

    audit = chart_audit.__wrapped__()
    test_each_printed_row_draws_its_anchor_d8_short_repeat_and_g_translates(audit)
    test_every_table_and_derived_family_reaches_the_actual_renderer(audit)
    test_rendered_arrows_have_live_periodic_endpoints(audit)
    test_vanishing_line_follows_from_maps_not_filtration_clipping(audit)


def test_static_cycle_engines_match_the_public_deployment_copies():
    root = Path(__file__).resolve().parents[1]
    for name in ("page-algebra.js", "vector-page-algebra.js"):
        assert (root / "backend/static" / name).read_bytes() == (root / "public/static" / name).read_bytes()
