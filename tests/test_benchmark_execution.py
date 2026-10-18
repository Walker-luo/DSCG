"""Read-only preparation and sequential run locking."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import json

class BenchmarkExecutionTests(unittest.TestCase):
    def module(self):
        from experiments.common import benchmark_execution
        return benchmark_execution

    def temporary(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        temp = TemporaryDirectory(dir=root); self.addCleanup(temp.cleanup)
        return Path(temp.name)

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
