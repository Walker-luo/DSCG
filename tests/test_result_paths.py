"""Backend folder layout and deterministic, non-migrating legacy resolution."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.common.result_paths import resolve_run_path, run_component, run_relative, result_layout


class ResultPathTests(unittest.TestCase):
    def temporary(self):
        root=Path(__file__).resolve().parents[1]/'workshop/artifacts/20261018_backend_result_layout/test_runs'
        root.mkdir(parents=True,exist_ok=True)
        temp=TemporaryDirectory(dir=root); self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def test_backend_is_a_folder_and_runs_group_under_the_model(self):
        for backend in ('agentdojo','agentdyn'):
            self.assertEqual(resolve_run_path(Path('results/partial_benchmark'),backend,'qwen3.7-flash','baseline'),
                             Path('results/partial_benchmark')/backend/'qwen3.7-flash'/'baseline')
        self.assertEqual(run_relative('qwen3.7-flash','baseline'), Path('qwen3.7-flash')/'baseline')
        self.assertEqual(run_relative('qwen3.7-flash',None,default_name='model-DSCG'), Path('model-DSCG'))
        self.assertEqual(run_component('model',None,default_name='model-DSCG'), 'model-DSCG')
        self.assertEqual(run_component('Qwen/model','trial/name'), 'Qwen-model_trial-name')
        self.assertEqual(run_relative('Qwen/model','trial/name'), Path('Qwen-model')/'trial-name')

    def test_legacy_is_only_used_on_resume_and_new_path_always_wins(self):
        root=self.temporary(); old=root/'qwen_agentdojo_baseline'; old.mkdir()
        middle=root/'agentdojo/qwen_baseline'
        new=root/'agentdojo/qwen/baseline'
        self.assertEqual(resolve_run_path(root,'agentdojo','qwen','baseline'),new)
        self.assertEqual(resolve_run_path(root,'agentdojo','qwen','baseline',allow_legacy=True),old)
        middle.mkdir(parents=True)
        self.assertEqual(resolve_run_path(root,'agentdojo','qwen','baseline',allow_legacy=True),middle)
        new.mkdir(parents=True)
        self.assertEqual(resolve_run_path(root,'agentdojo','qwen','baseline',allow_legacy=True),new)
        self.assertEqual(list(old.iterdir()),[])
        self.assertEqual(list(middle.iterdir()),[])

    def test_custom_root_is_always_extended_without_backend_deduplication(self):
        self.assertEqual(resolve_run_path(Path('custom/agentdojo'),'agentdojo','model','trial'),
                         Path('custom/agentdojo/agentdojo/model/trial'))

    def test_layout_names_each_generation(self):
        root=Path('results/benchmarks')
        self.assertEqual(result_layout(root,'agentdojo',root/'agentdojo/model/name'),'backend/model/name/attack/suite')
        self.assertEqual(result_layout(root,'agentdojo',root/'agentdojo/model_name'),'backend/model_run/attack/suite')
        self.assertEqual(result_layout(root,'agentdojo',root/'model_agentdojo_name'),'model_run/attack/suite')
