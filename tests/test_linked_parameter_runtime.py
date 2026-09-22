"""Transported arrows use the live source-field unit, never a copied assignment."""
import pytest

from test_coefficient_runtime import PARAMETER, runtime
from test_coefficient_ratios import ratio
from test_table_ledger import run_ledger


LINKED = PARAMETER + r"""
function fixtureLinked() {
  const sourceSpec=parameter('alpha'), sourceClaim=claim('source-claim',sourceSpec);
  sourceClaim.status='proven';
  const sourceRow=attach(diff('source-arrow','A','T'),'source-claim');
  const source=workspace(4,[A,T],[sourceRow],[sourceClaim]);
  source.id='source'; source.settings.coefficient_assignments={alpha:2};
  const spec={...parameter('alpha'),source_parameter:{workspace_id:'source',
    parameter_id:'alpha',differential_id:'source-arrow',page:3}};
  const row=attach(diff('linked','B','T'),'linked-claim');
  const ws=workspace(4,[A,B,AB,T],[diff('a','A','T'),row],[claim('linked-claim',spec)]);
  ws.id='target'; helpers.coefficientWorkspaces=[source,ws];
  return {source,sourceSpec,sourceClaim,sourceRow,spec,row,ws};
}
"""


def test_linked_raw_unit_is_transformed_only_at_target_and_never_written_back():
    result = runtime(LINKED + r"""
      const cases=[];
      for(const unit of [1,2,3]) for(const denominator of [1,2,3])
      for(const power of [0,1]) for(const offset of [0,1]) {
        const f=fixtureLinked();
        f.source.settings.coefficient_assignments.alpha=unit;
        // These source-occurrence transforms are NOT part of the raw unit.
        f.sourceSpec.frobenius_power=1; f.sourceSpec.affine_offset=1;
        Object.assign(f.spec,{frobenius_power:power,affine_offset:offset,inverse_parameter_id:'b'});
        f.ws.propositions.push(claim('b',parameter('b',denominator)));
        const before=JSON.stringify([f.source,f.ws]), algebra=compute(f.ws);
        cases.push({unit,denominator,power,offset,value:algebra.coefficientState(f.row).value,
          blocked:algebra.blockedFromPage,zero:algebra.isZero(f.row),
          target:algebra.endpoints(f.row).target.style.e2_components?.I13 ?? 1,
          unchanged:before===JSON.stringify([f.source,f.ws])});
      }
      console.log(JSON.stringify(cases));
    """)
    assert len(result) == 36
    for case in result:
        expected = ratio(case['unit'], case['denominator'], case['offset'], case['power'])
        assert case['value'] == expected and case['target'] == expected, case
        assert case['zero'] is (expected == 0) and case['blocked'] is None, case
        assert case['unchanged'], case


def test_live_source_assignment_and_admission_changes_invalidate_target_cache():
    result = runtime(LINKED + r"""
      const f=fixtureLinked(), results=[], objects=[];
      function record() {
        const a=compute(f.ws); objects.push(a);
        results.push({value:a.coefficientState(f.row).value??null,
          blocked:a.blockedFromPage,live:a.live(T,T.grade)});
      }
      record(); f.source.settings.coefficient_assignments.alpha=3; record();
      delete f.source.settings.coefficient_assignments.alpha; record();
      f.sourceSpec.value=1; record();
      f.sourceRow.status='review'; record(); f.sourceRow.status='proven'; record();
      f.sourceClaim.status='review'; record(); f.sourceClaim.status='proven'; record();
      f.sourceRow.page=5; record(); f.sourceRow.page=3; record();
      f.sourceRow.linear_map_id='matrix';
      f.source.differential_maps=[{id:'matrix',status:'proven'}]; record();
      f.source.differential_maps[0].archived=true; record();
      f.source.differential_maps[0].archived=false; record();
      helpers.coefficientWorkspaces=[]; record();
      console.log(JSON.stringify({results,distinct:objects.every((a,i)=>!i||a!==objects[i-1])}));
    """)
    expected = [2, 3, None, 1, None, 1, None, 1, None, 1, 1, None, 1, None]
    assert result['distinct']
    assert result['results'] == [
        {'value': value, 'blocked': 3 if value is None else None, 'live': value is None}
        for value in expected
    ]


@pytest.mark.parametrize('mutation', [
    "helpers.coefficientWorkspaces=[]",
    "helpers.coefficientWorkspaces.push(f.source)",
    "f.source.differentials=[]",
    "f.source.differentials.push({...f.sourceRow})",
    "f.sourceRow.proposition_id='missing'",
    "f.sourceSpec.id='different'",
    "f.sourceSpec.value=1",
    "f.sourceSpec.domain=[1]",
    "f.source.settings.coefficient_assignments.alpha=0",
    "f.source.settings.coefficient_assignments.alpha=true",
    "f.sourceSpec.source_parameter={...f.spec.source_parameter}",
    "f.spec.value=2",
    "f.ws.settings.coefficient_assignments={alpha:2}",
    "f.ws.propositions.push(claim('unlinked',parameter('alpha')))",
    "f.spec.source_parameter.page=3.5",
    "f.spec.source_parameter.parameter_id='different'",
    "f.spec.source_parameter=null",
    "f.sourceRow.linear_map_id='missing'",
    "f.sourceRow.linear_map_id='m'; f.source.differential_maps=[{id:'m',status:'proven'},{id:'m',status:'proven'}]",
])
def test_bad_source_or_local_override_blocks_quotient_without_erasures(mutation):
    result = runtime(LINKED + r"""
      const f=fixtureLinked(); MUTATION;
      const before=JSON.stringify([f.source,f.ws]), algebra=compute(f.ws);
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,
        state:algebra.coefficientState(f.row),apply:algebra.canApply(f.row),
        live:[A,B,T].map(n=>algebra.live(n,n.grade)),
        unchanged:before===JSON.stringify([f.source,f.ws])}));
    """.replace('MUTATION', mutation))
    assert result['blocked'] == 3 and not result['state']['resolved'], result
    assert 'linked coefficient' in result['state']['reason'], result
    assert not result['apply'] and result['live'] == [True] * 3, result
    assert result['unchanged']


def test_source_compatibility_constraint_and_exact_page_premises_are_rechecked():
    result = runtime(LINKED + r"""
      const f=fixtureLinked(), other=claim('other',parameter('beta',3));
      other.conclusion.fact_id='premise';
      f.source.propositions.push(other);
      f.source.differentials.push(attach(diff('other-row','B','T'),'other'));
      const constraint={id:'equality',kind:'equal-nonzero-parameters',page:3,
        parameter_ids:['alpha','beta'],required_facts:['premise'],
        required_differentials:[{fact_id:'premise',page:3}]};
      f.sourceClaim.conclusion.coefficient_constraints=[constraint];
      const out=[];
      const record=()=>{const a=compute(f.ws);out.push({blocked:a.blockedFromPage,
        value:a.coefficientState(f.row).value??null});};
      record(); other.conclusion.fact_id='wrong'; record();
      other.conclusion.fact_id='premise'; constraint.required_differentials[0].page=5; record();
      constraint.required_differentials[0].page=3; constraint.page=5; record();
      constraint.page=3; other.conclusion.coefficient_parameter.value=2; record();
      constraint.normalization_value=1; record();
      constraint.normalization_value=2; record();
      console.log(JSON.stringify(out));
    """)
    assert result == [{'blocked': 3 if value is None else None, 'value': value}
                      for value in (None, 2, 2, 2, 2, None, 2)]


def test_source_link_is_visible_and_untrusted_identifiers_are_escaped():
    source = {'workspace_id': '<script>source()</script>', 'parameter_id': 'alpha',
              'differential_id': '<img onerror="bad()">', 'page': 9}
    markup = run_ledger({'conclusion': {'coefficient_parameter': {
        'id': 'alpha', 'source_parameter': source,
    }}}, 'audit')
    assert 'Shared source coefficient:' in markup
    assert 'a local assignment cannot override it' in markup
    assert 'Frobenius is applied only after resolving' in markup
    assert '<script>' not in markup and '<img' not in markup
    assert '&lt;script&gt;' in markup and '&lt;img' in markup
