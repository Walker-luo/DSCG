"""Real spawn + real AgentDojo/AgentDyn cache/loop; no paid model requests."""

from artifact_support import ensure_artifacts
ensure_artifacts('test_attack_parallel_native')
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import attack_parallel_fixture
import serial_fixture
from baseintent.benchmark_catalog import get_backend, get_suites, get_suite
from experiments import run_partial_benchmark as runner, run_benchmark as full
from experiments.common.attack_execution import iter_attack_results, iter_serial_results


def spawned(jobs, *, on_event):
    return iter_attack_results(jobs,on_event=on_event,execute=attack_parallel_fixture.execute)


def inline(jobs, *, on_event):
    return iter_serial_results(jobs,on_event=on_event,execute=attack_parallel_fixture.execute)


class NativeAttackParallelTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'artifacts/tests/test_attack_parallel_native'
        root.mkdir(parents=True,exist_ok=True)
        temp=TemporaryDirectory(dir=root);self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)

    def base(self,name):
        return self.root/get_backend().id/('offline-model_'+name)

    def summaries(self,name):
        return {str(p.relative_to(self.base(name))):json.loads(p.read_text())
                for p in self.base(name).glob('*/*/summary.json')}

    def test_native_serial_parallel_scores_tokens_order_and_cache_match(self):
        suites=list(get_suites())[:2]
        for origin in (True,False):
            for progress in (False,True):
                with self.subTest(origin=origin,progress=progress),serial_fixture.patched(),redirect_stdout(StringIO()) as output:
                    options=dict(origin=origin,progress=progress,suites=suites,
                                 attack=['ignore_previous','important_instructions'],results_dir=self.root)
                    label=f'{origin}_{progress}'
                    with patch.object(runner,'iter_attack_results',side_effect=inline):
                        self.assertEqual(runner.main(**options,run_name=label+'_serial'),0,output.getvalue())
                    with patch.object(runner,'iter_attack_results',side_effect=spawned):
                        self.assertEqual(runner.main(**options,run_name=label+'_parallel'),0,output.getvalue())
                        base=self.base(label+'_parallel')
                        traces={p:p.read_bytes() for p in base.glob('*/*/*/*/*.json')}
                        bindings={p:p.read_bytes() for p in base.glob('*/*/run_manifest.json')}
                        before={p:len(p.read_text().splitlines()) for p in base.glob('*/*/fixture_events.jsonl')}
                        self.assertEqual(runner.main(**options,run_name=label+'_parallel',reuse=True),0)
                    for p,data in traces.items():self.assertEqual(p.read_bytes(),data)
                    for p,data in bindings.items():self.assertEqual(p.read_bytes(),data)
                    for p,size in before.items():self.assertEqual(len(p.read_text().splitlines()),size+2) # start/end only
                    a,b=self.summaries(label+'_serial'),self.summaries(label+'_parallel')
                    self.assertEqual(a.keys(),b.keys())
                    for key in a:
                        for field in ('task_selection','metrics','task_counts','overhead','sec_overhead'):
                            self.assertEqual(a[key].get(field),b[key].get(field))
                    events=[json.loads(line) for p in base.glob('*/*/fixture_events.jsonl') for line in p.read_text().splitlines()]
                    self.assertEqual(len({e['pid'] for e in events if e['kind']=='task'}),2)
                    for attack in options['attack']:
                        records=[[json.loads(l) for l in (base/attack/s/'fixture_events.jsonl').read_text().splitlines()] for s in suites]
                        self.assertEqual(records[0][0]['pid'],records[1][0]['pid'])
                        self.assertLessEqual(next(e['time'] for e in records[0] if e['kind']=='end'),records[1][0]['time'])
                        for suite_name,records_for_suite in zip(suites,records):
                            tasks=[e for e in records_for_suite if e['kind']=='task']
                            self.assertEqual([e['user'] for e in tasks[:3]],list(get_suite('v1.2',suite_name).injection_tasks)[:3])
                            self.assertEqual(len(tasks),12)
                    if progress:self.assertIn('GOAL 3/3',output.getvalue())
                    self.assertNotIn('\x1b',output.getvalue())
                    manifest=json.loads((base/'attack_manifest.json').read_text())
                    self.assertEqual(manifest['execution']['mode'],'parallel_attacks')
                    self.assertEqual(manifest['execution']['attack_processes'],2)

    def test_full_scope_and_clean_remain_native(self):
        suites=[list(get_suites())[0]]
        with serial_fixture.patched(),redirect_stdout(StringIO()) as output,patch.object(runner,'iter_attack_results',side_effect=spawned):
            self.assertEqual(full.main(origin=True,suites=suites,attack=['ignore_previous','important_instructions'],results_dir=self.root,run_name='full'),0,output.getvalue())
            native=get_suite('v1.2',suites[0])
            for data in self.summaries('full').values():
                self.assertEqual(data['task_selection']['user_task_ids'],list(native.user_tasks))
                self.assertEqual(data['task_selection']['injection_task_ids'],list(native.injection_tasks))
            self.assertEqual(runner.main(origin=True,suites=suites,run_attack=False,results_dir=self.root,run_name='clean'),0)
            clean=json.loads((self.base('clean')/'attack_manifest.json').read_text())
            self.assertEqual(clean['execution']['mode'],'serial')
            self.assertEqual(clean['attacks'],[])

    def test_frozen_cohort_is_read_once_and_not_reopened_in_workers(self):
        from experiments import run_injection_precheck as screen
        from experiments.common import injection_cohort as cohort
        suites=list(get_suites())[:2]
        with serial_fixture.patched(),redirect_stdout(StringIO()),\
             patch.object(screen,'resolve_model_config',side_effect=serial_fixture.resolve),\
             patch.object(screen,'make_openai_compatible_pipeline',side_effect=serial_fixture.baseline),\
             patch.object(cohort,'resolve_model_config',side_effect=serial_fixture.resolve):
            self.assertEqual(screen.screen(config_path=None,run_name='screen',results_dir=self.root/'screen',suites=suites),0)
            original=self.root/'screen'/get_backend().id/'offline-model_screen/cohort.json'
            frozen=json.loads(original.read_text())
            ids=frozen['suites'][suites[0]]['injection_task_ids']
            frozen['suites'][suites[0]]['injection_task_ids']=[ids[0],ids[3]]
            frozen['suites'][suites[1]]['injection_task_ids']=[]
            frozen['cohort_sha256']=cohort._digest({k:v for k,v in frozen.items() if k!='cohort_sha256'})
            path=original.with_name('subset.json');path.write_text(json.dumps(frozen))
            original_bytes=path.read_bytes()
            for entry,label,count in ((runner.main,'partial_cohort',1),(full.main,'full_cohort',2)):
                opened=[];native_read=Path.read_text
                def observed(p,*a,**k):
                    if p==path:opened.append(p)
                    return native_read(p,*a,**k)
                with patch.object(Path,'read_text',observed),patch.object(runner,'iter_attack_results',side_effect=spawned):
                    self.assertEqual(entry(origin=True,suites=suites,cohort_path=path,attack=['ignore_previous','important_instructions'],results_dir=self.root,run_name=label,progress=True),0)
                self.assertEqual(opened,[path])
                for data in self.summaries(label).values():
                    self.assertEqual(data['task_counts']['selected_injection_tasks'],count)
                    expected_users=3 if label.startswith('partial') else len(get_suite('v1.2',suites[0]).user_tasks)
                    self.assertEqual(data['task_counts']['selected_user_tasks'],expected_users)
                self.assertFalse(any((self.base(label)/attack/suites[1]/'summary.json').exists() for attack in runner.TYPICAL_ATTACKS))
                with patch.object(runner,'iter_attack_results',side_effect=spawned):
                    self.assertEqual(entry(origin=True,cohort_path=path,results_dir=self.root,run_name=label,reuse=True,progress=True),0)
                self.assertEqual(path.read_bytes(),original_bytes)

    def test_unsupported_groups_do_not_start_pipeline_or_preflight(self):
        if get_backend().id!='agentdyn':self.skipTest('AgentDyn-specific native unsupported group')
        with serial_fixture.patched(),redirect_stdout(StringIO()),patch.object(runner,'iter_attack_results',side_effect=spawned):
            self.assertEqual(runner.main(origin=True,suites=['dailylife'],results_dir=self.root,run_name='unsupported'),0)
        base=self.base('unsupported')
        manifest=json.loads((base/'attack_manifest.json').read_text())
        unsupported=[r for r in manifest['execution']['groups'] if r['status']=='unsupported']
        self.assertEqual(len(unsupported),1)
        self.assertEqual(unsupported[0]['attack'],'tool_knowledge')
        self.assertFalse((base/'tool_knowledge/dailylife/fixture_events.jsonl').exists())
        self.assertFalse(list((base/'tool_knowledge').rglob('none.json')))

    def test_binding_conflict_prevents_spawning_any_attack(self):
        with serial_fixture.patched(),redirect_stdout(StringIO()),patch.object(runner,'iter_attack_results',side_effect=spawned):
            options=dict(origin=True,suites=[list(get_suites())[0]],attack=['ignore_previous','important_instructions'],results_dir=self.root,run_name='conflict')
            self.assertEqual(runner.main(**options),0)
            base=self.base('conflict');path=next(base.glob('*/*/run_manifest.json'))
            value=json.loads(path.read_text());value['profile']='conflict';path.write_text(json.dumps(value))
            before={p:p.read_bytes() for p in base.rglob('*') if p.is_file()}
            with patch.object(runner,'iter_attack_results') as dispatch:
                self.assertEqual(runner.main(**options,reuse=True),1)
                dispatch.assert_not_called()
            self.assertEqual(before,{p:p.read_bytes() for p in base.rglob('*') if p.is_file()})

    def test_interrupt_reaps_children_preserves_results_and_can_resume(self):
        from contextlib import closing
        import multiprocessing
        import time
        def interrupted(jobs,*,on_event):
            with closing(iter_attack_results(jobs, on_event=on_event,
                         execute=attack_parallel_fixture.execute_interruptible)) as results:
                yield next(results)
                # Stop at a deterministic task boundary, rather than randomly
                # tearing a native JSON write (corrupt caches must still reject).
                deadline = time.monotonic() + 15
                while True:
                    files = list(self.base('interrupt').glob('*/' + get_suites()[0] + '/fixture_events.jsonl'))
                    if len(files) == 2 and all('"kind": "end"' in p.read_text() for p in files):
                        break
                    if time.monotonic() >= deadline:
                        self.fail('fixture attacks did not reach the between-suite boundary')
                    time.sleep(0.02)
                raise KeyboardInterrupt
        previous={p.pid for p in multiprocessing.active_children()}
        options=dict(origin=True,suites=list(get_suites())[:2],attack=['ignore_previous','important_instructions'],results_dir=self.root,run_name='interrupt',progress=True)
        with serial_fixture.patched(),redirect_stdout(StringIO()):
            with patch.object(runner,'iter_attack_results',side_effect=interrupted):
                self.assertEqual(runner.main(**options),130)
            self.assertEqual({p.pid for p in multiprocessing.active_children()},previous)
            base=self.base('interrupt')
            execution=json.loads(next((base/'execution').glob('*/execution.json')).read_text())
            self.assertEqual(execution['status'],'interrupted')
            self.assertTrue(any(g['status']=='completed' for g in execution['groups']))
            traces={p:p.read_bytes() for p in base.glob('*/*/*/*/*.json')}
            self.assertTrue(traces)
            with patch.object(runner,'iter_attack_results',side_effect=spawned):
                self.assertEqual(runner.main(**options,reuse=True),0)
            for p,data in traces.items():
                self.assertEqual(p.read_bytes(), data)

    def test_run_lock_blocks_dispatch(self):
        from experiments.common.benchmark_execution import run_lock
        from experiments.common.partial_controls import RunConfigurationError
        with serial_fixture.patched(),redirect_stdout(StringIO()),run_lock(self.base('locked')),patch.object(runner,'iter_attack_results') as dispatch:
            with self.assertRaises(RunConfigurationError):
                runner.main(origin=True,suites=[get_suites()[0]],attack='typical',results_dir=self.root,run_name='locked')
            dispatch.assert_not_called()

    def test_dos_parallel_keeps_native_denominator_and_has_no_goal_preflight(self):
        from agentdojo.attacks.attack_registry import ATTACKS
        dos=next(name for name,attack in ATTACKS.items() if attack.is_dos_attack)
        with serial_fixture.patched(),redirect_stdout(StringIO()),patch.object(runner,'iter_attack_results',side_effect=spawned):
            self.assertEqual(runner.main(origin=True,suites=[get_suites()[0]],attack=[dos,'ignore_previous'],results_dir=self.root,run_name='dos',progress=True),0)
        data=json.loads((self.base('dos')/dos/get_suites()[0]/'summary.json').read_text())
        self.assertEqual(data['task_counts']['planned_tasks'],3)
        self.assertEqual(data['task_counts']['total_tasks'],3)
        calls=[json.loads(l) for l in (self.base('dos')/dos/get_suites()[0]/'fixture_events.jsonl').read_text().splitlines()]
        self.assertEqual(len([e for e in calls if e['kind']=='task']),3)
        self.assertFalse(list((self.base('dos')/dos).rglob('none.json')))
