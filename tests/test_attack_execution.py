"""Real spawn scheduling contracts without importing a model client."""
import multiprocessing
import os
from pathlib import Path
import time
import unittest

from experiments.common.attack_execution import iter_attack_results


def probe(job):
    if job.get('crash'): os._exit(7)
    if job.get('fail'): raise TypeError('private-response-should-not-be-recorded')
    if job.get('gate') is not None: job['gate'].wait(timeout=15)
    start = time.monotonic()
    time.sleep(.2)
    return {'suite_reports': [{'attack': job['attack'], 'suite': job['suite'],
                              'pid': os.getpid(), 'start': start, 'end': time.monotonic()}]}


class AttackExecutionTests(unittest.TestCase):
    def jobs(self):
        return [{'attack': a, 'suite': s, 'compatibility': None}
                for a in ('a', 'b', 'c') for s in ('first', 'second')]

    def test_attacks_overlap_but_suites_remain_ordered_in_one_process(self):
        events=[]
        jobs=self.jobs();gate=multiprocessing.get_context('spawn').Barrier(3)
        for i in (0,2,4):jobs[i]['gate']=gate
        pairs=list(iter_attack_results(jobs, on_event=events.append, execute=probe))
        results={i:r for i,r in pairs}
        rows=[results[i]['result']['suite_reports'][0] for i in range(6)]
        self.assertEqual(len({r['pid'] for r in rows}),3)
        self.assertNotIn(os.getpid(),{r['pid'] for r in rows})
        self.assertLess(max(r['start'] for r in rows[::2]), min(r['end'] for r in rows[::2]))
        for i in range(0,6,2):
            self.assertEqual(rows[i]['pid'],rows[i+1]['pid'])
            self.assertLessEqual(rows[i]['end'],rows[i+1]['start'])
        self.assertEqual(len([e for e in events if e['kind']=='group_start']),6)

    def test_one_attack_and_unsupported_groups_need_no_children(self):
        jobs=self.jobs()[:2]
        results=dict(iter_attack_results(jobs,on_event=lambda _:None,execute=probe))
        self.assertEqual(results[0]['result']['suite_reports'][0]['pid'],os.getpid())
        for job in jobs: job['compatibility']={'status':'unsupported','reason_code':'missing_placeholder_args'}
        def forbidden(_): self.fail('unsupported group executed')
        self.assertTrue(all(r['status']=='unsupported' for _,r in iter_attack_results(jobs,on_event=lambda _:None,execute=forbidden)))

    def test_errors_do_not_stop_other_suites_or_attacks_and_are_safe(self):
        jobs=self.jobs();jobs[0]['fail']=True
        results=dict(iter_attack_results(jobs,on_event=lambda _:None,execute=probe))
        self.assertEqual(results[0]['error_type'],'TypeError')
        self.assertTrue(all(results[i]['status']=='completed' for i in range(1,6)))
        self.assertNotIn('private-response',str(results))

    def test_dead_child_reports_unfinished_groups_and_reaps_all_processes(self):
        jobs=self.jobs();jobs[0]['crash']=True
        previous={p.pid for p in multiprocessing.active_children()}
        results=dict(iter_attack_results(jobs,on_event=lambda _:None,execute=probe))
        self.assertEqual(results[0]['error_type'],'WorkerProcessError')
        self.assertTrue(results[1]['not_started'])
        self.assertTrue(all(results[i]['status']=='completed' for i in range(2,6)))
        self.assertEqual({p.pid for p in multiprocessing.active_children()},previous)

    def test_spawn_start_failure_does_not_block_other_attacks(self):
        from unittest.mock import patch
        from multiprocessing.process import BaseProcess
        native_start=BaseProcess.start
        def start(process):
            if process.name=='dscg-a':raise OSError('private-start-error')
            return native_start(process)
        with patch.object(BaseProcess,'start',new=start):
            results=dict(iter_attack_results(self.jobs(),on_event=lambda _:None,execute=probe))
        self.assertEqual(results[0]['error_type'],'WorkerStartError')
        self.assertTrue(results[1]['not_started'])
        self.assertTrue(all(results[i]['status']=='completed' for i in range(2,6)))
        self.assertNotIn('private-start-error',str(results))

    def test_broken_result_pipe_does_not_abort_other_attacks(self):
        from multiprocessing.connection import Connection
        from unittest.mock import patch
        native_recv=Connection.recv
        failed=[]
        def recv(connection):
            if not failed:
                failed.append(True)
                raise OSError('private-ipc-error')
            return native_recv(connection)
        with patch.object(Connection,'recv',new=recv):
            results=dict(iter_attack_results(self.jobs(),on_event=lambda _:None,execute=probe))
        self.assertEqual(sum(r['status']=='error' for r in results.values()),2)
        self.assertEqual(sum(r['status']=='completed' for r in results.values()),4)
        self.assertNotIn('private-ipc-error',str(results))

    def test_interrupt_immediately_after_spawn_reaps_the_new_child(self):
        from multiprocessing.process import BaseProcess
        from unittest.mock import patch
        native_start=BaseProcess.start
        previous={p.pid for p in multiprocessing.active_children()}
        created=[]
        def interrupt(process):
            native_start(process)
            created.append(process)
            raise KeyboardInterrupt
        try:
            with patch.object(BaseProcess,'start',new=interrupt),self.assertRaises(KeyboardInterrupt):
                list(iter_attack_results(self.jobs(),on_event=lambda _:None,execute=probe))
            self.assertEqual({p.pid for p in multiprocessing.active_children()},previous)
        finally:
            for process in created:
                if not process._closed:
                    if process.is_alive():process.terminate()
                    process.join();process.close()

    def test_interrupt_reaps_workers(self):
        previous={p.pid for p in multiprocessing.active_children()}
        def interrupt(event):
            if event['kind']=='group_start': raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            list(iter_attack_results(self.jobs(),on_event=interrupt,execute=probe))
        self.assertEqual({p.pid for p in multiprocessing.active_children()},previous)

class AttackOutputTests(unittest.TestCase):
    def test_worker_progress_is_forwarded_and_parent_owns_one_rich_renderer(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from rich.progress import Progress
        from experiments.common.attack_execution import AttackOutput
        from experiments.common.benchmark_progress import GroupProgress,progress_events
        events=[]
        with progress_events(events.append):
            for label in ('a/s','b/s'):
                with GroupProgress(label,goal_total=1,score_total=1) as bar:
                    bar.advance('goal');bar.advance('score')
                    events.append({'kind':'log','attack':label[0],'suite':'s','text':'native log'})
        class TTY(StringIO):
            def isatty(self):return True
        stream=TTY()
        with redirect_stdout(stream),patch('rich.progress.Progress',wraps=Progress) as factory:
            with AttackOutput([],True) as output:
                for event in events:output.event(event)
                self.assertEqual(len(output.rich.tasks),2)
            self.assertEqual(factory.call_count,1)
        self.assertIn('[a/s] native log',stream.getvalue())

    def test_failed_shared_bar_freezes_elapsed_time(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from experiments.common.attack_execution import AttackOutput
        class TTY(StringIO):
            def isatty(self):return True
        with redirect_stdout(TTY()),AttackOutput([],True) as output:
            output.event({'kind':'progress_start','label':'a/s','goal_total':1,'score_total':2})
            output.event({'kind':'progress_step','label':'a/s','phase':'goal'})
            output.event({'kind':'progress_end','label':'a/s','status':'error'})
            self.assertIsNotNone(output.rich.tasks[0].stop_time)

    def test_relay_keeps_goal_score_counts_and_error_status(self):
        from experiments.common.benchmark_progress import GroupProgress,progress_events
        events=[]
        with progress_events(events.append):
            with self.assertRaises(TypeError):
                with GroupProgress('a/s',goal_total=1,score_total=2) as bar:
                    bar.advance('goal');bar.advance('score');raise TypeError('private detail')
        self.assertEqual([e['kind'] for e in events],['progress_start','progress_step','progress_step','progress_end'])
        self.assertEqual(events[-1]['status'],'error')
        self.assertNotIn('private detail',str(events))
