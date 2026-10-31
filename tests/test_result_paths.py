"""Backend folder layout and deterministic, non-migrating legacy resolution."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.common.result_paths import resolve_run_path, run_component


class ResultPathTests(unittest.TestCase):
    def temporary(self):
        root=Path(__file__).resolve().parents[1]/'workshop/artifacts/20261018_backend_result_layout/test_runs'
        root.mkdir(parents=True,exist_ok=True)
        temp=TemporaryDirectory(dir=root); self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def test_backend_is_a_folder_and_default_name_keeps_pipeline_identity(self):
        for backend in ('agentdojo','agentdyn'):
            self.assertEqual(resolve_run_path(Path('results/partial_benchmark'),backend,'qwen3.7-flash','baseline'),
                             Path('results/partial_benchmark')/backend/'qwen3.7-flash_baseline')
        self.assertEqual(run_component('model',None,default_name='model-DSCG'), 'model-DSCG')
        self.assertEqual(run_component('Qwen/model','trial/name'), 'Qwen-model_trial-name')

    def test_legacy_is_only_used_on_resume_and_new_path_always_wins(self):
        root=self.temporary(); old=root/'qwen_agentdojo_baseline'; old.mkdir()
        new=root/'agentdojo/qwen_baseline'
        self.assertEqual(resolve_run_path(root,'agentdojo','qwen','baseline'),new)
        self.assertEqual(resolve_run_path(root,'agentdojo','qwen','baseline',allow_legacy=True),old)
        new.mkdir(parents=True)
        self.assertEqual(resolve_run_path(root,'agentdojo','qwen','baseline',allow_legacy=True),new)
        self.assertEqual(list(old.iterdir()),[])

    def test_custom_root_is_always_extended_without_backend_deduplication(self):
        self.assertEqual(resolve_run_path(Path('custom/agentdojo'),'agentdojo','model','trial'),
                         Path('custom/agentdojo/agentdojo/model_trial'))
