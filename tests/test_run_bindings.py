import tempfile, unittest
from pathlib import Path
from experiments.common.run_bindings import RunBindings, load_run_bindings
class RunBindingsTests(unittest.TestCase):
 def test_single_manifest_roundtrip(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); p=RunBindings(root)
   expected={'main_model':{'model_id':'x'},'attack':'a','task_selection':{'users':['u'],'injections':['i']}}
   p.check(root/'a/s/run_manifest.json',expected);p.commit()
   self.assertEqual(load_run_bindings(root)['a/s/run_manifest.json'],expected)
   self.assertFalse((root/'a/s/run_manifest.json').exists())
   self.assertEqual(p.guard(root/'a/s/run_manifest.json',expected),expected)
