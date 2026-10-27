"""Independent project identity and legacy read boundaries; no model calls."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest


class ProjectIdentityTests(unittest.TestCase):
    def test_current_package_and_framework_name(self):
        from baseintent.input_isolation import FRAMEWORK_VERSION
        self.assertEqual(FRAMEWORK_VERSION,'BaseIntent')

    def test_legacy_metadata_read_does_not_rewrite_facts_or_identity_values(self):
        from baseintent.compat import normalize_legacy_keys
        raw={'dscg_framework':{'framework_version':'DSCG_v3.5'},'dscg_layer_routing':{'n':1},
             'messages':[{'role':'tool','content':{'dscg_cost':17},'tool_calls':[{'args':{'dscg_key':'native'}}]}],
             'injections':{'dscg_key':'payload'},'native_schema':{'properties':{'dscg_parameter':{}}}}
        normalized=normalize_legacy_keys(raw)
        self.assertEqual(normalized['baseintent_framework']['framework_version'],'DSCG_v3.5')
        self.assertEqual(normalized['baseintent_layer_routing'],{'n':1})
        for key in ('messages','injections','native_schema'):self.assertEqual(normalized[key],raw[key])
        self.assertIn('dscg_framework',raw)

    def test_identity_keyed_containers_keep_run_and_model_names(self):
        from baseintent.compat import normalize_legacy_keys
        raw={'results':{'dscg_run':{'dscg_cost':{'tokens':3}}},
             'models':{'dscg_model':{'dscg_framework':{'framework_version':'DSCG'}}}}
        value=normalize_legacy_keys(raw)
        self.assertIn('dscg_run',value['results'])
        self.assertEqual(value['results']['dscg_run']['baseintent_cost'],{'tokens':3})
        self.assertIn('dscg_model',value['models'])

    def test_legacy_and_new_env_conflicts_do_not_leak_values(self):
        from baseintent.model_config import resolve_model_config,ModelConfigurationError
        c=resolve_model_config(env={'DSCG_MAIN_MODEL_ID':'legacy-model','DSCG_MAIN_API_KEY':'secret-old',
            'DSCG_MAIN_PROVIDER':'openai'},local_settings={})
        self.assertEqual(c.model_id,'legacy-model');self.assertEqual(c.api_key,'secret-old')
        with self.assertRaises(ModelConfigurationError) as caught:
            resolve_model_config(env={'DSCG_MAIN_API_KEY':'secret-old','BASEINTENT_MAIN_API_KEY':'secret-new'},local_settings={})
        self.assertNotIn('secret-old',str(caught.exception));self.assertNotIn('secret-new',str(caught.exception))

    def test_new_diagnostics_are_brand_only_and_old_block_stays_blocked(self):
        from baseintent.task_diagnostics import DiagnosticSession
        from baseintent.failure_policy import is_blocked_error
        with TemporaryDirectory() as tmp:
            logger=SimpleNamespace(dirpath=tmp,context=dict(pipeline_name='BaseIntent',suite_name='s',user_task_id='u',attack_type='none'))
            with DiagnosticSession(logger,'test',{}) as session:session.finish({})
            side=Path(tmp)/'BaseIntent/s/u/none/none.baseintent.jsonl'
            self.assertTrue(side.is_file());self.assertFalse(list(Path(tmp).rglob('*.dscg.*')))
        self.assertTrue(is_blocked_error('DSCG_BLOCKED'))
        self.assertTrue(is_blocked_error('DSCG_BLOCKED:AUDIT_DENY'))

    def test_legacy_sidecar_and_config_are_read_without_rewriting_bytes(self):
        from baseintent.task_diagnostics import load_task_trace,diagnostic_dependencies
        with TemporaryDirectory() as tmp:
            root=Path(tmp);directory=root/'run/s/user/none';directory.mkdir(parents=True)
            cfg=root/'run/s/dscg_config.old.json';cfg.write_text(json.dumps({'framework':{'framework_version':'DSCG_v3.5'}}))
            side=directory/'none.dscg.jsonl';side.write_text('\n'.join(json.dumps(x) for x in [
                dict(schema_version='dscg.task-diagnostics.v2',attempt_id='old',event='task_start',record=dict(config_ref='../../dscg_config.old.json',trace_level='summary')),
                dict(schema_version='dscg.task-diagnostics.v2',attempt_id='old',event='task_end',record=dict(summary={'dscg_cost':{'models':[]}}))])+'\n')
            trace=directory/'none.json';trace.write_text(json.dumps({'messages':[], 'utility':True,'security':False,
                'dscg_diagnostics':{'path':side.name,'offset':0,'attempt_id':'old'}}))
            before={p:p.read_bytes() for p in (cfg,side,trace)}
            data=load_task_trace(trace)
            self.assertEqual(data['baseintent_diagnostics_status'],'complete')
            self.assertEqual(data['baseintent_framework']['framework_version'],'DSCG_v3.5')
            self.assertTrue(data['utility']);self.assertFalse(data['security'])
            self.assertEqual(set(diagnostic_dependencies(trace)),{cfg.resolve(),side.resolve()})
            self.assertEqual({p:p.read_bytes() for p in before},before)

    def test_legacy_v2_response_offsets_and_manifest_identity_are_preserved(self):
        from baseintent.task_diagnostics import load_task_trace,diagnostic_dependencies
        with TemporaryDirectory() as tmp:
            root=Path(tmp);directory=root/'run/s/user/none';directory.mkdir(parents=True)
            cfg=root/'run/s/dscg_config.old.json'
            manifest=cfg.parent/'run_manifest.json'
            manifest.write_text(json.dumps({'dscg_policy_fingerprint':'dscg.original.identity'}))
            cfg.write_text(json.dumps({'framework':{'framework_version':'DSCG_v3.5'},
                'manifest':manifest.name,'framework_manifest_keys':['dscg_policy_fingerprint']}))
            replies=directory/'none.dscg.responses.jsonl'
            prefix=b'{"prior_attempt":true}\n'
            reply={'schema_version':'dscg.model-response.v1','attempt_id':'old','record':{
                'response_id':'r1','phase':'audit','content':'DSCG original reply'}}
            replies.write_bytes(prefix+(json.dumps(reply)+'\n').encode())
            side=directory/'none.dscg.jsonl'
            rows=[dict(event='task_start',record=dict(config_ref='../../dscg_config.old.json',
                      responses_path=replies.name,trace_level='summary')),
                  dict(event='response',record={},response_ref=dict(path=replies.name,offset=len(prefix),response_id='r1')),
                  dict(event='audit_decision_final',record=dict(batch_fingerprint='dscg-original-fingerprint')),
                  dict(event='task_end',record=dict(summary={}))]
            side.write_bytes(prefix+''.join(json.dumps(dict(schema_version='dscg.task-diagnostics.v2',
                attempt_id='old',**row))+'\n' for row in rows).encode())
            trace=directory/'none.json';trace.write_text(json.dumps({'messages':[],
                'dscg_diagnostics':{'path':side.name,'offset':len(prefix),'attempt_id':'old'}}))
            before={p:p.read_bytes() for p in (trace,side,replies,cfg,manifest)}
            result=load_task_trace(trace)
            self.assertEqual(result['baseintent_diagnostics_status'],'complete')
            self.assertEqual(result['baseintent_model_responses'][0]['content'],'DSCG original reply')
            self.assertEqual(result['baseintent_framework']['baseintent_policy_fingerprint'],'dscg.original.identity')
            self.assertEqual(result['baseintent_audit_decisions'][0]['batch_fingerprint'],'dscg-original-fingerprint')
            self.assertEqual(set(diagnostic_dependencies(trace)),{p.resolve() for p in (side,replies,cfg,manifest)})
            self.assertEqual(before,{p:p.read_bytes() for p in before})
