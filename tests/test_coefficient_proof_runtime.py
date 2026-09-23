"""A coefficient certificate is a live proof dependency, not a saved default."""
import pytest

from test_coefficient_runtime import PARAMETER, runtime
from test_coefficient_ratios import ratio


BOUND = PARAMETER + r"""
function fixtureProof() {
  const sourceRow=attach(diff('source-arrow','A','T'),'source-proof');
  const sourceProof={id:'source-proof',kind:'differential',status:'proven',premise_ids:['leaf'],
    conclusion:{source_id:'A',target_id:'T',page:3}};
  const leaf={id:'leaf',kind:'source-premise',status:'proven',premise_ids:[],conclusion:{}};
  const source=workspace(4,[structuredClone(A),structuredClone(T)],[sourceRow],[sourceProof,leaf]);
  source.id='source';
  const proof={id:'unit-proof',kind:'coefficient-proof',status:'proven',premise_ids:['source-proof'],
    conclusion:{parameter_id:'alpha',coefficient_value:3,
      external_premises:[{workspace_id:'source',proposition_id:'source-proof'}]}};
  const spec={...parameter(),proof_binding:{workspace_id:'owner',parameter_id:'alpha',proposition_id:'unit-proof'}};
  const row=attach(diff('bound','B','T'),'bound-claim');
  const consumer=claim('bound-claim',spec);
  Object.assign(consumer.conclusion,{source_id:'B',target_id:'T',page:3});
  consumer.conclusion.coefficient_proof_registration={parameter_id:'alpha',binding:structuredClone(spec.proof_binding)};
  const ws=workspace(4,[A,B,AB,T],[diff('a','A','T'),row],[consumer]); ws.id='target';
  const owner=workspace(4,[],[],[proof]); owner.id='owner';
  helpers.coefficientWorkspaces=[ws,owner,source];
  return {ws,owner,source,sourceRow,sourceProof,leaf,proof,spec,row,consumer};
}
"""


def test_proof_unit_precedes_affine_ratio_and_frobenius_without_mutation():
    result = runtime(BOUND + r"""
      const rows=[];
      for(const denominator of [1,2,3]) for(const power of [0,1]) for(const offset of [0,1]) {
        const f=fixtureProof();
        Object.assign(f.spec,{frobenius_power:power,affine_offset:offset,inverse_parameter_id:'b'});
        f.ws.propositions.push(claim('b',parameter('b',denominator)));
        const snapshot=JSON.stringify([f.ws,f.owner,f.source]), a=compute(f.ws);
        rows.push({denominator,power,offset,value:a.coefficientState(f.row).value,
          unchanged:snapshot===JSON.stringify([f.ws,f.owner,f.source])});
      }
      console.log(JSON.stringify(rows));
    """)
    for row in result:
        assert row['value'] == ratio(3, row['denominator'], row['offset'], row['power'])
        assert row['unchanged']


@pytest.mark.parametrize('mutation', [
    "f.proof.status='review'",
    "f.proof.conclusion.admission_status='review'",
    "f.proof.conclusion.coefficient_value=true",
    "f.proof.conclusion.coefficient_value=0",
    "f.proof.conclusion.parameter_id='wrong'",
    "f.proof.kind='source-premise'",
    "f.proof.premise_ids=[]",
    "f.owner.propositions=[]",
    "f.owner.propositions.push(structuredClone(f.proof))",
    "helpers.coefficientWorkspaces.push(structuredClone(f.owner))",
    "helpers.coefficientWorkspaces=helpers.coefficientWorkspaces.filter(w=>w!==f.owner)",
    "f.sourceProof.status='review'",
    "f.sourceProof.conclusion.admission_status='review'",
    "f.sourceProof.conclusion.source_id='T'",
    "f.sourceProof.conclusion.page=5",
    "f.sourceProof.premise_ids=['missing']",
    "f.sourceProof.premise_ids=['source-proof']",
    "f.leaf.status='review'",
    "f.source.propositions=f.source.propositions.filter(p=>p!==f.leaf)",
    "f.source.differentials=[]",
    "f.source.differentials.push(structuredClone(f.sourceRow))",
    "f.sourceRow.status='review'",
    "f.sourceRow.archived=true",
    "f.sourceRow.page=5",
    "f.sourceRow.source_id='missing'",
    "f.sourceRow.linear_map_id='missing'",
    "f.source.classes.pop()",
    "f.source.classes[0].archived=true",
    "f.source.classes.push(structuredClone(f.source.classes[0]))",
    "f.spec.proof_binding.proposition_id='missing'",
    "f.spec.proof_binding.parameter_id='wrong'",
    "f.spec.proof_binding=null",
    "delete f.spec.proof_binding",
    "delete f.consumer.conclusion.coefficient_parameter",
    "f.spec.id='changed'",
    "f.spec.proof_binding.extra='not-part-of-binding'",
    "f.spec.domain=[1]",
    "f.owner.propositions.push(claim('owner-declaration',parameter()))",
    "f.owner.settings.coefficient_assignments={alpha:2}",
    "f.ws.propositions.push(claim('duplicate',parameter()))",
    "f.ws.propositions.push(claim('bound-claim',parameter()))",
    "f.ws.settings.coefficient_assignments={alpha:1}",
    "f.ws.settings.coefficient_assignments={alpha:true}",
    "f.spec.value=2",
])
def test_proof_changes_invalidate_cache_and_no_raw_or_candidate_fallback(mutation):
    result = runtime(BOUND + r"""
      const f=fixtureProof();
      f.spec.value=3; f.ws.settings.coefficient_assignments={alpha:3};
      const before=compute(f.ws), initial=before.coefficientState(f.row);
      MUTATION;
      const after=compute(f.ws);
      console.log(JSON.stringify({before:initial,after:after.coefficientState(f.row),
        different:before!==after, live:after.live(T,T.grade),
        candidate:after.candidateState(f.row,B.grade,T.grade)}));
    """.replace('MUTATION', mutation))
    assert result['before']['resolved'] and result['before']['value'] == 3
    assert result['different'] and not result['after']['resolved']
    assert result['live']
    assert result['candidate']['variants'] == []


def test_source_matrix_and_recursive_leaf_are_live_dependencies():
    result = runtime(BOUND + r"""
      const f=fixtureProof(), values=[], instances=[];
      f.sourceRow.linear_map_id='matrix';
      const matrix={id:'matrix',status:'proven',archived:false,page:3,proposition_id:'source-proof'};
      f.source.differential_maps=[matrix];
      function read() {const a=compute(f.ws); instances.push(a); values.push(a.coefficientState(f.row).value??null);}
      read(); matrix.archived=true; read(); matrix.archived=false; read();
      matrix.status='review'; read(); matrix.status='proven'; read();
      f.leaf.status='review'; read(); f.leaf.status='proven'; read();
      f.source.differential_maps=[]; read();
      console.log(JSON.stringify({values,distinct:instances.every((a,i)=>!i||a!==instances[i-1])}));
    """)
    assert result == {'values': [3, None, 3, None, 3, None, 3, None], 'distinct': True}


@pytest.mark.parametrize('field', ['page', 'proposition_id', 'source_cell_id', 'target_cell_id'])
def test_external_matrix_identity_changes_invalidate_the_coefficient_cache(field):
    import json
    result = runtime(BOUND + r"""
      const f=fixtureProof(); f.sourceRow.linear_map_id='matrix';
      const matrix={id:'matrix',status:'proven',page:3,proposition_id:'source-proof'};
      f.source.differential_maps=[matrix];
      const before=compute(f.ws), first=before.coefficientState(f.row);
      matrix[FIELD]='changed';
      const after=compute(f.ws);
      console.log(JSON.stringify({first,last:after.coefficientState(f.row),different:before!==after}));
    """.replace('FIELD', json.dumps(field)))
    assert result['first']['value'] == 3
    assert result['different'] and not result['last']['resolved']


@pytest.mark.parametrize('mutation', [
    'delete ownerConsumer.conclusion.coefficient_parameter',
    "ownerConsumer.conclusion.coefficient_parameter.id='changed'",
    'delete ownerConsumer.conclusion.coefficient_parameter.proof_binding',
])
def test_missing_registered_source_declaration_invalidates_its_atlas_consumers(mutation):
    result = runtime(BOUND + r"""
      const f=fixtureProof(), ownerConsumer=structuredClone(f.consumer);
      f.owner.propositions.push(ownerConsumer);
      const before=compute(f.ws), first=before.coefficientState(f.row);
      MUTATION;
      const after=compute(f.ws);
      console.log(JSON.stringify({first,last:after.coefficientState(f.row),different:before!==after}));
    """.replace('MUTATION', mutation))
    assert result['first']['value'] == 3
    assert result['different'] and not result['last']['resolved']


def test_source_parameter_link_reads_certificate_raw_unit_and_its_withdrawal():
    result = runtime(BOUND + r"""
      const f=fixtureProof(); f.consumer.status='proven';
      Object.assign(f.spec,{frobenius_power:1,affine_offset:1});
      const linkedSpec={...parameter(),source_parameter:{workspace_id:f.ws.id,
        parameter_id:'alpha',differential_id:f.row.id,page:3}};
      const row=attach(diff('image','B','T'),'image-claim');
      const target=workspace(4,[A,B,AB,T],[diff('a','A','T'),row],[claim('image-claim',linkedSpec)]);
      target.id='image'; helpers.coefficientWorkspaces.push(target);
      const before=compute(target); f.leaf.status='review'; const after=compute(target);
      console.log(JSON.stringify({value:before.coefficientState(row).value,
        resolved:after.coefficientState(row).resolved,different:before!==after,
        candidate:after.candidateState(row,B.grade,T.grade)}));
    """)
    assert result['value'] == 3 and not result['resolved'] and result['different']
    assert result['candidate']['variants'] == []


def test_bound_condition_reads_raw_unit_even_in_reflected_occurrence():
    result = runtime(BOUND + r"""
      const f=fixtureProof();
      f.consumer.conclusion.coefficient_condition={parameter_id:'alpha',equals:3,otherwise:'zero-euler-image'};
      f.spec.frobenius_power=1;
      const a=compute(f.ws);
      console.log(JSON.stringify({condition:a.conditionState(f.row),coefficient:a.coefficientState(f.row)}));
    """)
    assert result['condition']['nonzero'] and result['condition']['value'] == 3
    assert result['coefficient']['value'] == 2


def test_withdrawn_certificate_cannot_reuse_a_stale_display_scalar():
    from test_chart_display_conventions import display_coefficient
    from test_table_ledger import run_ledger

    metadata = {'coefficient_parameter': {'id': 'alpha', 'value': 3, 'proof_binding': {
        'workspace_id': 'source', 'parameter_id': 'alpha', 'proposition_id': '<proof>'}},
        'atlas_display_coefficient': {'resolved': True, 'value': 3, 'basis_ratio': 1}}
    assert display_coefficient(metadata, {'resolved': False}) is None
    assert display_coefficient(metadata, {'resolved': True, 'value': 2})['value'] == 2
    markup = run_ledger({'conclusion': metadata}, 'audit')
    assert 'Proof-bound coefficient' in markup and '&lt;proof&gt;' in markup
    assert 'Fixed F4 coefficient' not in markup


def test_review_graph_uses_the_same_live_proof_premises():
    from test_coefficient_proof_binding import proof_fixture
    from domain.logic_graph import admitted_proposition_ids

    fixture = proof_fixture()
    assert fixture.proof.id in admitted_proposition_ids(fixture.project)
    fixture.target.archived = True
    assert fixture.proof.id not in admitted_proposition_ids(fixture.project)
    fixture.target.archived = False
    assert fixture.proof.id in admitted_proposition_ids(fixture.project)
    fixture.external.conclusion['admission_status'] = 'review'
    assert fixture.proof.id not in admitted_proposition_ids(fixture.project)


def test_table_ledger_uses_live_bound_unit_after_affine_and_frobenius():
    result = runtime(BOUND + r"""
      require('./backend/static/table-ledger.js');
      const values=[];
      for (const power of [0,1]) for (const offset of [0,1]) {
        const f=fixtureProof();
        Object.assign(f.spec,{frobenius_power:power,affine_offset:offset});
        f.consumer.conclusion.atlas_display_coefficient={resolved:true,value:1};
        function entry() {
          return HFPSSTableLedger.rowsForWorkspace(f.ws,compute(f.ws))
            .find(row=>row.differentialId===f.row.id).coefficient;
        }
        const before=entry(); f.leaf.status='review';
        values.push({power,offset,before,after:entry()});
      }
      console.log(JSON.stringify(values));
    """)
    for item in result:
        value = ratio(3, 1, item['offset'], item['power'])
        assert item['before']['status'] == 'resolved'
        assert item['before']['expression'] == {2: r'\zeta', 3: r'\zeta^2'}[value]
        assert item['after']['status'] == 'unresolved'
        assert item['after']['expression'] != '1'


def test_all_six_real_atlas_scopes_share_the_live_js_certificate():
    from dataclasses import asdict
    import json
    import subprocess
    from domain.migrations import migrate_project
    from domain.seed import demo_project
    from test_vector_page_invariants import ROOT, RUNTIME

    project = asdict(migrate_project(demo_project()))
    script = RUNTIME + r"""
      const project=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
      helpers.coefficientWorkspaces=project.workspaces;
      helpers.accepted=row=>['proven','verified','source-verified','established','admitted'].includes(row.status);
      // This checks coefficient resolution, independent of viewport expansion.
      helpers.copies=()=>[];
      const owner=project.workspaces.find(w=>w.id==='ws_sigma_i_2sigma_j');
      const proof=owner.propositions.find(p=>p.id==='coefficient_proof_mixed_d5_A');
      const scopes=project.workspaces.filter(w=>w===owner
        || w.settings.atlas_transport?.source_workspace_id===owner.id);
      function read() {
        return scopes.map(ws=>{
          const claims=new Map(ws.propositions.map(p=>[p.id,p])), a=compute(ws);
          return {id:ws.id,rows:ws.differentials.flatMap(row=>{
            const spec=claims.get(row.proposition_id)?.conclusion?.coefficient_parameter;
            return spec?.id==='mixed_d5_A' ? [{power:spec.frobenius_power||0,
              offset:spec.affine_offset||0,coefficient:a.coefficientState(row)}] : [];
          })};
        });
      }
      const before=read(); proof.status='review'; const after=read();
      console.log(JSON.stringify({before,after}));
    """
    completed = subprocess.run(['node', '-e', script], cwd=ROOT,
                               input=json.dumps(project), text=True, encoding='utf-8',
                               capture_output=True, check=True, timeout=60)
    result = json.loads(completed.stdout)
    assert len(result['before']) == len(result['after']) == 6
    for scope in result['before']:
        assert len(scope['rows']) == 3
        for row in scope['rows']:
            assert row['coefficient']['resolved'], (scope['id'], row)
            assert row['coefficient']['value'] == ratio(3, 1, row['offset'], row['power'])
    for scope in result['after']:
        assert all(not row['coefficient']['resolved'] for row in scope['rows'])
