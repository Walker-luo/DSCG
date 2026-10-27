import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from baseintent import audit_router as a


class DatasetTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('experiments.calibration.l3_router_dataset'),'dataset tooling missing')
        from experiments.calibration.l3_router_dataset import build_dataset
        return build_dataset

    def record(self,group='g',split='development',source='environment_oracle'):
        p=dict(schema_version=a.INPUT_SCHEMA,trusted_user_request='Read budget',current_actions=[dict(tool_name='read_data',host_tool_description='Read budget',untrusted_argument_data={})],
               recent_tool_results=[],action_history=[],history_truncated=False,tool_results_window_truncated=False,
               policy_features=dict(allowlist_matches=[True],candidate_metadata_states={'read_data':dict(metadata_state='valid',effect='read',sink='none',sensitivity='internal',idempotent=True)}))
        return dict(episode_group_id=group,episode_id=group+'-1',correlation_key='task-'+group,split=split,label='safe_and_sufficient',label_source=source,
                    label_evidence_ref='oracle:test',packet=p,input_sha256=a.digest(p),
                    host=dict(catalog_sha256='1'*64,tool_schema_hash='2'*64,model_config_sha256='3'*64,schema_valid=True,
                              completeness_flags={k:False for k in ('request_truncated','description_truncated','history_truncated',
                              'tool_results_window_truncated','content_truncated','tool_result_error','arguments_truncated','arguments_nonfinite_or_unsupported')}))

    def run_records(self,records):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);src=root/'input.jsonl'
        src.write_text(''.join(json.dumps(r)+'\n' for r in records));return self.api()(src,root/'dataset')

    def test_scores_are_recomputed_and_private_text_not_duplicated(self):
        r=self.record();r['score']=1
        out=self.run_records([r]);self.assertEqual(out['valid_actions'],1)
        rows=json.loads((Path(out['output_dir'])/'rows.json').read_text());self.assertEqual(rows[0]['score'],0)
        self.assertNotIn('packet',rows[0]);self.assertNotIn('Read budget',json.dumps(rows))

    def test_weak_labels_split_leakage_and_hash_change_are_rejected(self):
        for mutation in ('source','split','hash','correlation'):
            records=[self.record()]
            if mutation=='source':records[0]['label_source']='auditor_allow'
            if mutation=='hash':records[0]['packet']['trusted_user_request']='changed'
            if mutation=='split':records.append(self.record(split='calibration'))
            if mutation=='correlation':
                records.append(self.record('other','calibration'));records[1]['correlation_key']=records[0]['correlation_key']
            with self.assertRaises(ValueError):self.run_records(records)

    def test_invalid_samples_are_reported_and_never_safe(self):
        r=self.record();r.update(label='invalid_sample',exclusion_reason='missing payload')
        out=self.run_records([r]);self.assertEqual(out['invalid_actions'],1);self.assertEqual(out['valid_actions'],0)

    def test_hard_scope_is_recomputed_from_host_metadata(self):
        r=self.record();r['packet']['policy_features']['candidate_metadata_states']['read_data']['sensitivity']='secret';r['input_sha256']=a.digest(r['packet'])
        out=self.run_records([r]);rows=json.loads((Path(out['output_dir'])/'rows.json').read_text());self.assertFalse(rows[0]['eligible'])

    def test_calibration_tool_requires_attestation_and_preserves_outputs(self):
        from experiments.calibration.calibrate_l3_router import calibrate_dataset
        records=[self.record('dev')]
        for i in range(64):
            r=self.record(str(i),'calibration');r['packet']['trusted_user_request']=f'Read budget {i}'
            r['input_sha256']=a.digest(r['packet']);records.append(r)
        out=self.run_records(records);root=Path(out['output_dir']);artifact=root.parent/'artifact.json'
        with self.assertRaises(ValueError):calibrate_dataset(root,[0.5],0.05,0.05,artifact)
        result=calibrate_dataset(root,[0.5],0.05,0.05,artifact,True)
        self.assertEqual(result['calibration']['threshold'],0.5)
        self.assertEqual(result['calibration']['valid_groups'],64)
        with self.assertRaises(ValueError):calibrate_dataset(root,[0.5],0.05,0.05,artifact,True)

    def test_missing_completeness_flags_are_not_complete(self):
        r=self.record();r['host']['completeness_flags']={}
        with self.assertRaises(ValueError):self.run_records([r])

    def test_calibrator_rechecks_row_sources_and_actual_groups(self):
        from experiments.calibration.calibrate_l3_router import calibrate_dataset
        records=[self.record('dev')]
        for i in range(64):
            r=self.record(str(i),'calibration');r['packet']['trusted_user_request']=f'Read budget {i}'
            r['input_sha256']=a.digest(r['packet']);records.append(r)
        out=self.run_records(records);root=Path(out['output_dir']);rows=json.loads((root/'rows.json').read_text());manifest=json.loads((root/'manifest.json').read_text())
        rows[1]['label_source']='auditor_allow';rows[1]['episode_group_id']='dev'
        manifest['rows_sha256']=a.digest(rows)
        (root/'rows.json').write_text(json.dumps(rows));(root/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):calibrate_dataset(root,[0.5],0.05,0.05,root.parent/'artifact.json',True)
