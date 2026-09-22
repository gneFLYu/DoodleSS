"""Unknown units must not become silent unit-one maps or stale cached kernels."""
import pytest

from test_vector_page_invariants import runtime


PARAMETER = r"""
const parameter = (id='alpha', value=null, power=0) => ({id,symbol:id,value,
  domain:[1,2,3],frobenius_power:power});
const claim = (id,spec) => ({id,kind:'differential',conclusion:{coefficient_parameter:spec}});
const attach = (row,id) => ({...row,proposition_id:id});
const kernel = algebra => [...algebra.vectorBlocks.values()][0].q.representatives;
"""


def test_unresolved_admitted_unit_blocks_later_quotients_and_known_cycle_claims():
    result = runtime(PARAMETER + r"""
      const ws=workspace(6,[A,B,AB,T,U],
        [diff('a','A','T'),attach(diff('b','B','T'),'pb'),diff('later','T','U',5)],
        [claim('pb',parameter())]);
      const algebra=compute(ws);
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
        live:[A,B,T,U].map(n=>algebra.live(n,n.grade)),known:[A,B,T,U].map(n=>algebra.knownCycle(n,n.grade)),
        later:algebra.maps(T,U,T.grade,U.grade).length,apply:algebra.canApply(ws.differentials[1]),
        uncertain:algebra.representatives(bounds).every(r=>r.uncertain)}));
    """)
    assert result["blocked"] == 3
    assert result["live"] == [True] * 4 and result["known"] == [False] * 4
    assert result["later"] == 0 and not result["apply"] and result["uncertain"]
    assert result["conflicts"][0]["reason"] == "coefficient parameter is unresolved"


def test_assignment_and_psi_change_the_actual_kernel_and_invalidate_the_same_object_cache():
    result = runtime(PARAMETER + r"""
      const spec=parameter(), ws=workspace(4,[A,B,AB,T],
        [diff('a','A','T'),attach(diff('b','B','T'),'pb')],[claim('pb',spec)]);
      const unresolved=compute(ws);
      ws.settings.coefficient_assignments={alpha:'zeta'};
      const z=compute(ws);
      spec.frobenius_power=1;
      const conjugate=compute(ws);
      spec.frobenius_power=0;
      ws.settings.coefficient_assignments.alpha='zeta^2';
      const z2=compute(ws);
      console.log(JSON.stringify({blocked:unresolved.blockedFromPage,
        kernels:[z,conjugate,z2].map(kernel),cleared:[z,conjugate,z2].every(a=>a.blockedFromPage===null),
        distinct:unresolved!==z && z!==conjugate && conjugate!==z2,
        untouched:!T.style.e2_components,value:spec.value,errors:[z,conjugate,z2].flatMap(a=>a.conflicts)}));
    """)
    assert result["blocked"] == 3
    assert result["kernels"] == [[[1, 3]], [[1, 2]], [[1, 2]]]
    assert result["cleared"] and result["distinct"] and result["untouched"]
    assert result["value"] is None and not result["errors"]


@pytest.mark.parametrize("value", ["0", "4", "alpha", "-1"])
def test_invalid_unit_assignment_is_an_explicit_conflict_not_a_render_crash(value):
    import json
    result = runtime(PARAMETER + r"""
      const ws=workspace(4,[A,B,AB,T],
        [attach(diff('a','A','T'),'pa'),attach(diff('b','B','T'),'pb')],
        [claim('pa',parameter()),claim('pb',parameter())]);
      ws.settings.coefficient_assignments={alpha:VALUE};
      const a=compute(ws);
      console.log(JSON.stringify({blocked:a.blockedFromPage,errors:a.conflicts,live:a.live(T,T.grade)}));
    """.replace("VALUE", json.dumps(value)))
    assert result["blocked"] == 3 and result["live"]
    assert all(c["reason"] == "invalid F4 unit assignment" for c in result["errors"])


def test_same_parameter_cannot_take_two_independent_values():
    result = runtime(PARAMETER + r"""
      const ws=workspace(4,[A,B,AB,T],
        [attach(diff('a','A','T'),'pa'),attach(diff('b','B','T'),'pb')],
        [claim('pa',parameter('alpha',2)),claim('pb',parameter('alpha',3))]);
      const a=compute(ws);
      console.log(JSON.stringify({blocked:a.blockedFromPage,errors:a.conflicts}));
    """)
    assert result["blocked"] == 3
    assert all("conflicting assignments" in c["reason"] for c in result["errors"])


def test_rebinding_a_claim_invalidates_the_cached_coefficient_map():
    result = runtime(PARAMETER + r"""
      const row=attach(diff('b','B','T'),'pb');
      const ws=workspace(4,[A,B,AB,T],[diff('a','A','T'),row],
        [claim('pb',parameter('alpha',2)),claim('pc',parameter('beta',3))]);
      const before=compute(ws);
      row.proposition_id='pc';
      const after=compute(ws);
      console.log(JSON.stringify({same:before===after,kernels:[kernel(before),kernel(after)]}));
    """)
    assert result == {"same": False, "kernels": [[[1, 3]], [[1, 2]]]}


def test_compatibility_and_its_source_fact_invalidate_the_quotient_cache():
    result = runtime(PARAMETER + r"""
      const pa=claim('pa',parameter('alpha',1)), pb=claim('pb',parameter('beta',2));
      pb.conclusion.fact_id='premise';
      const constraint={id:'compat',kind:'equal-nonzero-parameters',page:3,
        parameter_ids:['alpha','beta'],required_facts:['premise'],
        required_differentials:[{fact_id:'premise',page:3}]};
      const ws=workspace(4,[A,B,AB,T],
        [attach(diff('a','A','T'),'pa'),attach(diff('b','B','T'),'pb')],[pa,pb]);
      const initial=compute(ws);
      pa.conclusion.coefficient_constraints=[constraint];
      const blocked=compute(ws);
      pb.conclusion.fact_id='not-the-premise';
      const cleared=compute(ws);
      console.log(JSON.stringify({distinct:initial!==blocked && blocked!==cleared,
        blocked:blocked.blockedFromPage,reason:blocked.conflicts[0].reason,
        cleared:cleared.blockedFromPage,kernels:[initial,cleared].map(kernel)}));
    """)
    assert result == {"distinct": True, "blocked": 3,
                      "reason": "Leibniz coefficient compatibility violated",
                      "cleared": None, "kernels": [[[1, 3]], [[1, 3]]]}


@pytest.mark.parametrize("unit,expected", [(1, 0), (2, 3), (3, 2)])
def test_affine_coefficients_are_linked_and_zero_is_an_actual_zero_map(unit, expected):
    result = runtime(PARAMETER + r"""
      const spec={...parameter(),affine_offset:1}, row=attach(diff('a','A','T'),'pa');
      const zeroB={id:'zeroB',kind:'zero-differential',status:'proven',
        conclusion:{source_id:'B',page:3,zero:true}};
      const ws=workspace(4,[A,B,AB,T],[row],[claim('pa',spec),zeroB]);
      ws.settings.coefficient_assignments={alpha:UNIT};
      const algebra=compute(ws);
      const before=algebra.coefficientState(row).value;
      spec.frobenius_power=1;
      const image=compute(ws);
      console.log(JSON.stringify({value:before,image:image.coefficientState(row).value,
        live:[A,B,T].map(n=>algebra.live(n,n.grade)),errors:algebra.conflicts,
        kernel:kernel(algebra),changed:algebra!==image}));
    """.replace("UNIT", str(unit)))
    assert result["value"] == expected
    assert result["image"] == {0: 0, 2: 3, 3: 2}[expected]
    assert result["live"] == ([True, True, True] if unit == 1 else [False, True, False])
    assert result["kernel"] == ([[1, 0], [0, 1]] if unit == 1 else [[0, 1]])
    assert not result["errors"] and result["changed"]


@pytest.mark.parametrize("unit", [1, 2, 3])
def test_a_common_unknown_nonzero_factor_does_not_change_a_resolved_kernel(unit):
    result = runtime(PARAMETER + r"""
      const ws=workspace(4,[A,B,AB,T],
        [attach(diff('a','A','T'),'pa'),attach(diff('b','B','T'),'pb')],
        [claim('pa',parameter()),claim('pb',parameter())]);
      ws.settings.coefficient_assignments={alpha:UNIT};
      const a=compute(ws);
      console.log(JSON.stringify({kernel:kernel(a),errors:a.conflicts}));
    """.replace("UNIT", str(unit)))
    assert result == {"kernel": [[1, 1]], "errors": []}


@pytest.mark.parametrize("unit,power,expected", [(1, 0, 1), (2, 0, 2), (3, 0, 3), (2, 1, 3)])
def test_relative_target_coefficient_changes_only_one_basis_column(unit, power, expected):
    result = runtime(PARAMETER + r"""
      const S=node('S','I73',7,1), P=node('P','I62X',6,4), Q=node('Q','I62Y',6,4);
      const PQ=node('PQ',null,6,4,{I62X:1,I62Y:1});
      const spec={...parameter('b',UNIT,POWER),target_component:'I62Y'};
      const row=attach(diff('relative','S','PQ'),'relativeClaim');
      const ws=workspace(4,[S,P,Q,PQ],[row],[claim('relativeClaim',spec)]);
      const snapshot=JSON.stringify(ws), algebra=compute(ws), target=algebra.endpoints(row).target;
      const line={...PQ,style:{e2_components:{I62X:1,I62Y:EXPECTED}}};
      console.log(JSON.stringify({components:target.style.e2_components,
        live:[S,P,Q,PQ,line].map(n=>algebra.live(n,n.grade)),errors:algebra.conflicts,
        untouched:snapshot===JSON.stringify(ws),zero:algebra.isZero(row)}));
    """.replace("UNIT", str(unit)).replace("POWER", str(power)).replace("EXPECTED", str(expected)))
    assert result["components"] == {"I62X": 1, "I62Y": expected}
    assert result["live"] == [False, True, True, expected != 1, False]
    assert not result["errors"] and result["untouched"] and not result["zero"]


def test_zero_relative_coefficient_is_not_a_zero_map_when_another_column_remains():
    result = runtime(PARAMETER + r"""
      const S=node('S','I73',7,1), P=node('P','I62X',6,4), Q=node('Q','I62Y',6,4);
      const PQ=node('PQ',null,6,4,{I62X:1,I62Y:1});
      const spec={...parameter('b',1),affine_offset:1,target_component:'I62Y'};
      const row=attach(diff('relative','S','PQ'),'relativeClaim');
      const ws=workspace(4,[S,P,Q,PQ],[row],[claim('relativeClaim',spec)]);
      const algebra=compute(ws);
      console.log(JSON.stringify({components:algebra.endpoints(row).target.style.e2_components,
        zero:algebra.isZero(row),live:[S,P,Q,PQ].map(n=>algebra.live(n,n.grade)),errors:algebra.conflicts}));
    """)
    assert result == {"components": {"I62X": 1, "I62Y": 0}, "zero": False,
                      "live": [False, False, True, True], "errors": []}


def test_invalid_relative_component_blocks_quotient_instead_of_scaling_the_whole_map():
    result = runtime(PARAMETER + r"""
      const ws=workspace(4,[A,B,AB,T],[attach(diff('a','A','T'),'pa')],
        [claim('pa',{...parameter('b',2),target_component:'missing'})]);
      const algebra=compute(ws);
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,reason:algebra.conflicts[0].reason,
        live:[A,T].map(n=>algebra.live(n,n.grade))}));
    """)
    assert result == {"blocked": 3, "reason": "invalid coefficient target component", "live": [True, True]}


@pytest.mark.parametrize("c,gamma,blocked,zero,dead", [
    (None, 1, 3, False, False), (1, None, 3, False, False),
    (1, 2, None, False, True), (2, None, None, True, False),
    (3, None, None, True, False),
])
def test_conditional_euler_image_distinguishes_unknown_zero_and_nonzero(c, gamma, blocked, zero, dead):
    import json
    result = runtime(PARAMETER + r"""
      const p=claim('pa',parameter('gamma',GAMMA)), row=attach(diff('a','A','T'),'pa');
      p.conclusion.coefficient_condition={parameter_id:'c',equals:1,otherwise:'zero-euler-image'};
      const zeroB={id:'zeroB',kind:'zero-differential',status:'proven',conclusion:{source_id:'B',page:3,zero:true}};
      const ws=workspace(4,[A,B,AB,T],[row],[p,claim('pc',parameter('c',C)),zeroB]);
      const snapshot=JSON.stringify(ws), algebra=compute(ws);
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,zero:algebra.isZero(row),
        live:[A,T].map(n=>algebra.live(n,n.grade)),unchanged:snapshot===JSON.stringify(ws)}));
    """.replace("GAMMA", json.dumps(gamma)).replace("parameter('c',C)", "parameter('c'," + json.dumps(c) + ")"))
    assert result == {"blocked": blocked, "zero": zero, "live": [not dead, not dead], "unchanged": True}


def test_condition_is_in_source_field_and_changing_it_invalidates_the_cached_quotient():
    result = runtime(PARAMETER + r"""
      const p=claim('pa',parameter('gamma',2,1)), row=attach(diff('a','A','T'),'pa');
      p.conclusion.coefficient_condition={parameter_id:'c',equals:2,otherwise:'zero-euler-image'};
      const zeroB={id:'zeroB',kind:'zero-differential',status:'proven',conclusion:{source_id:'B',page:3,zero:true}};
      const ws=workspace(4,[A,B,AB,T],[row],[p,claim('pc',parameter('c',2,1)),zeroB]);
      const active=compute(ws);
      const activeValue=active.coefficientState(row).value;
      p.conclusion.coefficient_condition.equals=3;
      const zero=compute(ws);
      console.log(JSON.stringify({different:active!==zero,values:[activeValue,zero.coefficientState(row).value],
        live:[active,zero].map(a=>a.live(A,A.grade))}));
    """)
    assert result == {"different": True, "values": [3, 0], "live": [False, True]}


@pytest.mark.parametrize("condition", [None, {}, {"parameter_id": "c", "equals": 1},
    {"parameter_id": "c", "equals": True, "otherwise": "zero-euler-image"},
    {"parameter_id": "undeclared", "equals": 1, "otherwise": "zero-euler-image"}])
def test_invalid_condition_cannot_silently_activate_a_map(condition):
    import json
    result = runtime(PARAMETER + r"""
      const p=claim('pa',parameter('gamma',1)); p.conclusion.coefficient_condition=CONDITION;
      const ws=workspace(4,[A,B,AB,T],[attach(diff('a','A','T'),'pa')],[p,claim('pc',parameter('c',1))]);
      const a=compute(ws); console.log(JSON.stringify({blocked:a.blockedFromPage,live:a.live(A,A.grade)}));
    """.replace("CONDITION", json.dumps(condition)))
    assert result == {"blocked": 3, "live": True}


@pytest.mark.parametrize("condition", [None, False, 0, ""])
def test_adding_a_falsy_invalid_condition_invalidates_a_previous_unconditional_quotient(condition):
    import json
    result = runtime(PARAMETER + r"""
      const p=claim('pa',parameter('gamma',1)), row=attach(diff('a','A','T'),'pa');
      const zeroB={id:'zeroB',kind:'zero-differential',status:'proven',conclusion:{source_id:'B',page:3,zero:true}};
      const ws=workspace(4,[A,B,AB,T],[row],[p,zeroB]);
      const before=compute(ws);
      p.conclusion.coefficient_condition=CONDITION;
      const invalid=compute(ws);
      const invalidReason=invalid.coefficientState(row).reason;
      delete p.conclusion.coefficient_condition;
      const restored=compute(ws);
      console.log(JSON.stringify({different:before!==invalid && invalid!==restored,
        blocked:invalid.blockedFromPage,reason:invalidReason,
        live:[before,invalid,restored].map(a=>a.live(A,A.grade))}));
    """.replace("CONDITION", json.dumps(condition)))
    assert result == {"different": True, "blocked": 3,
                      "reason": "invalid coefficient condition", "live": [False, True, False]}
