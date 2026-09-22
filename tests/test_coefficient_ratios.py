"""Source-field coefficient ratios must survive conjugation without guessing units."""
from copy import deepcopy
import json

import pytest

from test_coefficient_runtime import PARAMETER, runtime
from test_parameterized_fate import (
    Proposition,
    add_arrow,
    assert_live,
    fixture,
    parameter,
    sync_workspace_fates,
)


# Independent arithmetic oracle: 2 = zeta, 3 = zeta^2, addition is XOR.
MULTIPLICATION = ((0, 0, 0, 0), (0, 1, 2, 3), (0, 2, 3, 1), (0, 3, 1, 2))
INVERSE = {1: 1, 2: 3, 3: 2}
FROBENIUS = (0, 1, 3, 2)


def ratio(gamma, denominator, offset, power):
    value = MULTIPLICATION[gamma ^ offset][INVERSE[denominator]]
    return FROBENIUS[value] if power else value


def declare(workspace, spec, ident="denominator-declaration"):
    workspace.propositions.append(Proposition(
        ident, "coefficient", "Shared source-field coefficient", status="review",
        conclusion={"coefficient_parameter": deepcopy(spec)},
    ))


def test_all_unit_ratios_and_affine_offsets_scale_targets_not_sources_or_assignments():
    result = runtime(PARAMETER + r"""
      const results=[];
      for (const gamma of [1,2,3]) for (const b of [1,2,3])
      for (const power of [0,1]) for (const offset of [0,1]) {
        const B2=node('B2',null,6,2,{I62Y:2});
        const spec={...parameter('gamma',null,power),affine_offset:offset,inverse_parameter_id:'b'};
        const row=attach(diff('ratio','B2','T'),'ratio-claim');
        const ws=workspace(4,[A,B2,AB,T],[diff('a','A','T'),row],
          [claim('ratio-claim',spec),claim('b-declaration',parameter('b'))]);
        ws.settings.coefficient_assignments={gamma,b};
        const snapshot=JSON.stringify(ws), algebra=compute(ws), pair=algebra.endpoints(row);
        results.push({gamma,b,power,offset,value:algebra.coefficientState(row).value,
          target:pair.target.style.e2_components || {[pair.target.style.e2_pattern]:1},
          source:pair.source.style.e2_components,kernel:kernel(algebra),
          zero:algebra.isZero(row),blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
          unchanged:snapshot===JSON.stringify(ws)});
      }
      console.log(JSON.stringify(results));
    """)
    assert len(result) == 36
    for case in result:
        value = ratio(case["gamma"], case["b"], case["offset"], case["power"])
        assert case["value"] == value, case
        assert case["target"] == {"I13": value}, case
        assert case["source"] == {"I62Y": 2}, case
        # d(A)=T, d(2B)=rT: the ambient kernel is A+(2/r)B, not A+rB.
        expected_kernel = [[1, MULTIPLICATION[2][INVERSE[value]]]] if value else [[0, 1]]
        assert case["kernel"] == expected_kernel, case
        assert case["zero"] is (value == 0), case
        assert case["blocked"] is None and not case["conflicts"], case
        assert case["unchanged"], case


def test_denominator_assignment_and_declaration_changes_invalidate_the_same_workspace_cache():
    result = runtime(PARAMETER + r"""
      const spec={...parameter('gamma'),inverse_parameter_id:'b'};
      const denominator=parameter('b'), row=attach(diff('ratio','B','T'),'ratio-claim');
      const ws=workspace(4,[A,B,AB,T],[diff('a','A','T'),row],
        [claim('ratio-claim',spec),claim('b-declaration',denominator)]);
      ws.settings.coefficient_assignments={gamma:2,b:1};
      const computed=[], states=[];
      function record() {
        const algebra=compute(ws); computed.push(algebra);
        states.push({value:algebra.coefficientState(row).value ?? null,
          blocked:algebra.blockedFromPage,
          kernel:algebra.blockedFromPage===null?kernel(algebra):null,
          live:algebra.live(T,T.grade)});
      }
      record();
      ws.settings.coefficient_assignments.b=2; record();
      ws.settings.coefficient_assignments.b=3; record();
      delete ws.settings.coefficient_assignments.b; record();
      denominator.value=2; record();
      denominator.value=3; record();
      console.log(JSON.stringify({states,distinct:computed.every((a,i)=>!i||a!==computed[i-1]),
        gamma:spec.value,assignments:ws.settings.coefficient_assignments}));
    """)
    assert result["distinct"]
    expected = [(2, [[1, 3]]), (1, [[1, 1]]), (3, [[1, 2]]),
                (None, None), (1, [[1, 1]]), (3, [[1, 2]])]
    for state, (value, kernel) in zip(result["states"], expected, strict=True):
        assert state == {"value": value, "kernel": kernel,
                         "blocked": 3 if value is None else None, "live": value is None}
    assert result["gamma"] is None and result["assignments"] == {"gamma": 2}


@pytest.mark.parametrize("condition_value", [2, 3])
def test_false_zero_euler_condition_skips_unassigned_numerator_and_denominator(condition_value):
    result = runtime(PARAMETER + r"""
      const spec={...parameter('gamma',null,1),inverse_parameter_id:'b'};
      const p=claim('ratio-claim',spec), row=attach(diff('ratio','A','T'),'ratio-claim');
      p.conclusion.coefficient_condition={parameter_id:'c',equals:1,otherwise:'zero-euler-image'};
      const zeroB={id:'zeroB',kind:'zero-differential',status:'proven',
        conclusion:{source_id:'B',page:3,zero:true}};
      const ws=workspace(4,[A,B,AB,T],[row],[p,claim('b-declaration',parameter('b')),
        claim('c-declaration',parameter('c')),zeroB]);
      ws.settings.coefficient_assignments={c:CONDITION};
      const before=JSON.stringify(ws), algebra=compute(ws);
      console.log(JSON.stringify({value:algebra.coefficientState(row).value,
        zero:algebra.isZero(row),live:[A,B,T].map(n=>algebra.live(n,n.grade)),
        blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
        kernel:kernel(algebra),unchanged:before===JSON.stringify(ws)}));
    """.replace("CONDITION", str(condition_value)))
    assert result == {"value": 0, "zero": True, "live": [True, True, True],
                      "blocked": None, "conflicts": [], "kernel": [[1, 0], [0, 1]],
                      "unchanged": True}
    workspace, arrow, claim = fixture(parameter("gamma", inverse_parameter_id="b", frobenius_power=1))
    declare(workspace, parameter("b"))
    declare(workspace, parameter("c"), "condition-declaration")
    claim.conclusion["coefficient_condition"] = {
        "parameter_id": "c", "equals": 1, "otherwise": "zero-euler-image",
    }
    workspace.settings["coefficient_assignments"] = {"c": condition_value}
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow)
    assert workspace.settings["coefficient_assignments"] == {"c": condition_value}


BAD_DENOMINATORS = [
    pytest.param({"assignments": {}}, "coefficient denominator is unresolved", id="unassigned"),
    *[pytest.param({"assignments": {"b": value}}, "invalid coefficient denominator assignment",
                   id=f"invalid-assignment-{index}")
      for index, value in enumerate((0, 4, "bad", True, {}, []))],
    pytest.param({"assignments": {"b": 3}, "value": 2},
                 "conflicting assignments for coefficient denominator", id="conflicting-assignment"),
    pytest.param({"assignments": {"b": 2}, "extra_value": 3},
                 "conflicting assignments for coefficient denominator", id="conflicting-declaration"),
    pytest.param({"assignments": {"b": 2}, "domain": [1]},
                 "coefficient denominator is outside its domain", id="outside-domain"),
    pytest.param({"assignments": {"b": 2}, "declare": False},
                 "coefficient denominator parameter is undeclared", id="undeclared"),
    *[pytest.param({"assignments": {"b": 2}, "inverse_id": value},
                   "invalid coefficient denominator id", id=f"invalid-id-{index}")
      for index, value in enumerate(("", None, 2))],
]


@pytest.mark.parametrize("case,reason", BAD_DENOMINATORS)
def test_bad_denominators_block_frontend_quotients_and_backend_deaths(case, reason):
    result = runtime(PARAMETER + r"""
      const config=CONFIG;
      const spec={...parameter('gamma'),inverse_parameter_id:
        Object.hasOwn(config,'inverse_id')?config.inverse_id:'b'};
      const row=attach(diff('ratio','A','T'),'ratio-claim');
      const props=[claim('ratio-claim',spec)];
      if(config.declare!==false) props.push(claim('b-declaration',
        {...parameter('b',config.value??null),domain:config.domain??[1,2,3]}));
      if(Object.hasOwn(config,'extra_value')) props.push(claim('extra-b',parameter('b',config.extra_value)));
      const ws=workspace(6,[A,B,AB,T,U],[row,diff('later','T','U',5)],props);
      ws.settings.coefficient_assignments={gamma:2,...config.assignments};
      const before=JSON.stringify(ws), algebra=compute(ws);
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,
        reason:algebra.coefficientState(row).reason,conflicts:algebra.conflicts,
        live:[A,T,U].map(n=>algebra.live(n,n.grade)),apply:algebra.canApply(row),
        later:algebra.maps(T,U,T.grade,U.grade).length,unchanged:before===JSON.stringify(ws)}));
    """.replace("CONFIG", json.dumps(case)))
    assert result["blocked"] == 3 and result["reason"] == reason
    assert any(item["reason"] == reason for item in result["conflicts"])
    assert result["live"] == [True, True, True]
    assert not result["apply"] and not result["later"] and result["unchanged"]

    workspace, arrow, _ = fixture(parameter("gamma", inverse_parameter_id=case.get("inverse_id", "b")))
    if case.get("declare", True):
        declare(workspace, parameter("b", case.get("value"), domain=case.get("domain", [1, 2, 3])))
    if "extra_value" in case:
        declare(workspace, parameter("b", case["extra_value"]), "extra-denominator-declaration")
    later, _ = add_arrow(workspace, "later", page=9, spec=parameter("later", 1))
    workspace.settings["coefficient_assignments"] = {"gamma": 2, **case["assignments"]}
    snapshot = deepcopy(workspace.settings)
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow)
    assert_live(workspace, later)
    assert workspace.settings == snapshot


def test_backend_ratio_zero_and_nonzero_deaths_track_all_units_and_conjugates():
    for gamma in (1, 2, 3):
        for denominator in (1, 2, 3):
            for power in (0, 1):
                for offset in (0, 1):
                    workspace, arrow, claim = fixture(parameter(
                        "gamma", inverse_parameter_id="b", affine_offset=offset, frobenius_power=power,
                    ))
                    declare(workspace, parameter("b"))
                    workspace.settings["coefficient_assignments"] = {"gamma": gamma, "b": denominator}
                    snapshot = deepcopy(claim.conclusion)
                    sync_workspace_fates(workspace)
                    assert_live(workspace, arrow, ratio(gamma, denominator, offset, power) == 0)
                    assert claim.conclusion == snapshot
                    assert workspace.settings["coefficient_assignments"] == {"gamma": gamma, "b": denominator}
                    # Cached public fate queries must recheck a removed denominator assignment.
                    del workspace.settings["coefficient_assignments"]["b"]
                    assert_live(workspace, arrow)
