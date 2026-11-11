"""Process scheduler and immutable preparation contracts (offline)."""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import time
import multiprocessing
import signal
import threading
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from tempfile import TemporaryDirectory


def offline_group(job):
    started = time.monotonic()
    print('private worker output', flush=True)
    time.sleep(.15)
    if job.get('crash'):
        os._exit(7)
    if job.get('fail'):
        raise RuntimeError('sensitive-provider-error')
    return {'pid': os.getpid(), 'started': started, 'ended': time.monotonic(), 'tokens': 7}


def long_group(job):
    Path(job['marker']).write_text(str(os.getpid()))
    time.sleep(30)


class BenchmarkExecutionTests(unittest.TestCase):
    def test_interrupt_during_start_or_join_keeps_child_in_cleanup_registry(self):
        m = self.module()
        for phase in ('start', 'join'):
            with self.subTest(phase=phase):
                root = self.temporary()
                receive = Mock(); receive.recv.return_value = {'status': 'completed', 'result': {}}
                send = Mock()
                class Process:
                    pid = None
                    alive = False
                    terminated = False
                    joins = 0
                    def start(self):
                        self.pid = 123; self.alive = True
                        if phase == 'start': raise KeyboardInterrupt
                    def is_alive(self): return self.alive
                    def terminate(self): self.terminated = True; self.alive = False
                    def kill(self): self.alive = False
                    def join(self, timeout=None):
                        self.joins += 1
                        if phase == 'join' and self.joins == 1: raise KeyboardInterrupt
                process = Process()
                ctx = SimpleNamespace(Pipe=lambda **_: (receive, send), Process=lambda **_: process)
                with patch.object(m.multiprocessing, 'get_context', return_value=ctx), \
                     patch.object(m, 'wait', return_value=[receive]), redirect_stdout(StringIO()), \
                     self.assertRaises(KeyboardInterrupt):
                    m.execute_groups([{'attack': 'a', 'suite': 's'}], 2, offline_group, root)
                self.assertTrue(process.terminated)
                self.assertGreaterEqual(process.joins, 1)

    def module(self):
        from experiments.common import benchmark_execution
        return benchmark_execution

    def temporary(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_qwen_parallel/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        temp = TemporaryDirectory(dir=root); self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def test_workers_validation(self):
        m = self.module()
        for value in (0, -1, True, 1.5, '2'):
            with self.subTest(value=value), self.assertRaises(ValueError): m.validate_workers(value)
        self.assertEqual(m.validate_workers(3), 3)

    def test_interrupt_terminates_and_reaps_spawned_children(self):
        m = self.module(); root = self.temporary()
        def interrupt():
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not list(root.glob('*.started')):
                time.sleep(.02)
            os.kill(os.getpid(), signal.SIGINT)
        thread = threading.Thread(target=interrupt)
        thread.start()
        with redirect_stdout(StringIO()), self.assertRaises(KeyboardInterrupt):
            m.execute_groups([{'attack': 'a', 'suite': str(i), 'marker': str(root / f'{i}.started')}
                              for i in range(3)], 2, long_group, root)
        thread.join()
        self.assertTrue(list(root.glob('*.started')))
        self.assertFalse(multiprocessing.active_children())

    def test_prepare_all_bindings_before_writing_anything(self):
        m = self.module(); root = self.temporary()
        path = root / 'b/run_manifest.json'; path.parent.mkdir()
        path.write_text('{"model": "original"}')
        plan = m.PreparedBindings()
        plan.check(root / 'a/run_manifest.json', {'model': 'new'})
        with self.assertRaises(ValueError): plan.check(path, {'model': 'changed'})
        self.assertFalse((root / 'a').exists())
        self.assertEqual(json.loads(path.read_text()), {'model': 'original'})

    def test_directory_lock_and_committed_guard(self):
        m = self.module(); root = self.temporary()
        path = root / 'run_manifest.json'; plan = m.PreparedBindings()
        plan.check(path, {'value': 1})
        with m.run_lock(root):
            with self.assertRaises(ValueError):
                with m.run_lock(root): pass
            plan.commit()
        self.assertEqual(plan.guard(path, {'value': 1}), {'value': 1})
        path.write_text('{"value": 2}')
        with self.assertRaises(ValueError): plan.guard(path, {'value': 1})

    def test_spawn_overlaps_isolates_logs_and_accounts_each_group_once(self):
        m = self.module(); root = self.temporary()
        jobs = [{'attack': 'a', 'suite': s} for s in ('one', 'two', 'three')]
        output = StringIO()
        with redirect_stdout(output): results = m.execute_groups(jobs, 2, offline_group, root)
        values = [r['result'] for r in results]
        self.assertEqual(len({v['pid'] for v in values}), 3)
        self.assertTrue(all(v['pid'] != os.getpid() for v in values))
        self.assertLess(max(v['started'] for v in values[:2]), min(v['ended'] for v in values[:2]))
        self.assertEqual(sum(v['tokens'] for v in values), 21)
        self.assertNotIn('private worker output', output.getvalue())
        self.assertEqual(len(list(root.glob('*.log'))), 3)

    def test_exception_and_abrupt_exit_do_not_erase_other_groups_or_echo_error(self):
        m = self.module(); root = self.temporary()
        jobs = [{'attack': 'a', 'suite': 'error', 'fail': True},
                {'attack': 'a', 'suite': 'crash', 'crash': True},
                {'attack': 'b', 'suite': 'ok'}]
        output = StringIO()
        with redirect_stdout(output): results = m.execute_groups(jobs, 2, offline_group, root)
        self.assertEqual([r['status'] for r in results], ['error', 'error', 'completed'])
        self.assertNotIn('sensitive-provider-error', output.getvalue())
        self.assertEqual(results[-1]['result']['tokens'], 7)
