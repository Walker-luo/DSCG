"""Relocated offline commands keep working from the project root."""

from artifact_support import ensure_artifacts
ensure_artifacts('test_experiments_layout')
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class ExperimentsLayoutTests(unittest.TestCase):
    def test_grouped_harness_cli_preserves_sample_error_denominators(self):
        root = Path(__file__).resolve().parents[1]
        artifacts = root / 'artifacts/tests/test_experiments_layout'
        artifacts.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=artifacts) as directory:
            output = Path(directory) / 'e0.json'
            result = subprocess.run([
                sys.executable, '-B', '-m', 'experiments.diagnostics.harness_audit',
                '--fixture', 'tests/fixtures/harness_audit_cases.json', '--output', str(output),
            ], cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            counts = json.loads(output.read_text())['sample_counts']
            self.assertEqual(counts['valid'], 1)
            self.assertEqual(counts['tool_error'], 1)
            self.assertEqual(counts['infrastructure_error'], 4)


if __name__ == '__main__':
    unittest.main()
