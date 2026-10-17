"""Relocated offline commands keep working from the project root."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class ExperimentsLayoutTests(unittest.TestCase):
    def test_grouped_harness_cli_preserves_sample_error_denominators(self):
        root = Path(__file__).resolve().parents[1]
        artifacts = root / 'workshop/artifacts/20261017_experiments_layout/test_runs'
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
