"""Offline preset/CLI contracts; no models or original experiment writes."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from dscg.audit_router import calibrate, LocalAuditRouter
from experiments.calibration import calibrate_l3_router as cli

ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / 'config/l3_router.calibration.json'
ARTIFACTS = ROOT / 'workshop/artifacts/20261019_l3_preset'


class CalibrationPresetTests(unittest.TestCase):
    def setUp(self):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        self.tmp = TemporaryDirectory(dir=ARTIFACTS)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, value):
        path = self.root/'preset.json'
        path.write_text(json.dumps(value))
        return path

    def run_cli(self, args):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return cli.main(['--dataset-dir', str(self.root/'dataset'),
                             '--output', str(self.root/'artifact.json'), *args])

    def test_committed_candidate_preset_loads_only_calibration_parameters(self):
        self.assertEqual(cli.load_preset(PRESET),
                         {'grid': [0.65, 0.70, 0.75], 'epsilon': 0.05, 'delta': 0.05})
        value = json.loads(PRESET.read_text())
        self.assertEqual(value['status'], 'development_candidate')
        self.assertEqual(value['reference_threshold'], 0.70)

    def test_cli_preset_passes_values_but_not_reference(self):
        with patch.object(cli, 'calibrate_dataset', return_value={
                'calibration': {'threshold': None, 'valid_groups': 0}}) as run:
            self.assertEqual(self.run_cli(['--preset', str(PRESET)]), 0)
        self.assertEqual(run.call_args.args[1:4], ([0.65, 0.70, 0.75], 0.05, 0.05))
        self.assertFalse(run.call_args.args[-1])  # attestation is still explicit

    def test_preset_conflicts_with_each_explicit_parameter_before_dataset_read(self):
        for option in (['--grid', '0.5'], ['--epsilon', '0.1'], ['--delta', '0.1']):
            with self.subTest(option=option), patch.object(cli, 'calibrate_dataset') as run:
                with self.assertRaises(SystemExit) as error:
                    self.run_cli(['--preset', str(PRESET), *option])
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()

    def test_legacy_complete_flags_are_unchanged_and_partial_flags_rejected(self):
        with patch.object(cli, 'calibrate_dataset', return_value={
                'calibration': {'threshold': None, 'valid_groups': 0}}) as run:
            self.assertEqual(self.run_cli(['--grid', '.5', '--epsilon', '.05',
                                          '--delta', '.05', '--attest-independent-groups']), 0)
        self.assertEqual(run.call_args.args[1:4], ([.5], .05, .05))
        self.assertTrue(run.call_args.args[-1])
        for option in ([], ['--grid', '.5'], ['--epsilon', '.05', '--delta', '.05']):
            with self.subTest(option=option), self.assertRaises(SystemExit) as error:
                self.run_cli(option)
            self.assertEqual(error.exception.code, 2)

    def test_invalid_schema_status_grid_reference_and_targets_are_rejected(self):
        good = {'schema_version': 'dscg.router-calibration-preset.v1',
                'status': 'development_candidate', 'grid': [.65, .7, .75],
                'reference_threshold': .7, 'epsilon': .05, 'delta': .05}
        changes = [('schema_version', 'deployment'), ('status', 'certified'),
                   ('grid', []), ('grid', [.65, .65]), ('grid', [.7, True]),
                   ('grid', [.7, float('nan')]), ('grid', '0.7'),
                   ('reference_threshold', .8), ('reference_threshold', True),
                   ('epsilon', 0), ('epsilon', float('inf')), ('delta', 1), ('delta', '0.05')]
        for field, value in changes:
            row = {**good, field: value}
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                cli.load_preset(self.write(row))
        for row in ([], {k:v for k,v in good.items() if k != 'epsilon'}):
            with self.assertRaises(ValueError):
                cli.load_preset(self.write(row))
        duplicate = self.root/'duplicate.json'
        duplicate.write_text('{"grid": [0.7], "grid": [0.8]}')
        with self.assertRaises(ValueError):
            cli.load_preset(duplicate)

    def test_reference_cannot_override_selected_or_null_threshold(self):
        row = json.loads(PRESET.read_text())
        for reference in (.65, .75):
            changed = deepcopy(row)
            changed['reference_threshold'] = reference
            parameters = cli.load_preset(self.write(changed))
            records = [dict(episode_group_id=str(i), score=.69, eligible=True,
                            label='safe_and_sufficient', cost=1) for i in range(80)]
            self.assertEqual(calibrate(records, **parameters)['threshold'], .7)
            self.assertIsNone(calibrate(records[:16], **parameters)['threshold'])
            self.assertEqual(records[0]['label'], 'safe_and_sufficient')

    def test_preset_is_not_a_deployment_artifact(self):
        router = LocalAuditRouter('selective', PRESET, '1'*64)
        self.assertIsNone(router.artifact)
        self.assertIsNotNone(router.error)
        self.assertEqual(LocalAuditRouter().mode, 'off')

    def test_real_dataset_cli_keeps_null_or_calibrated_result_not_reference(self):
        from test_l3_router_dataset import DatasetTests
        from experiments.calibration.l3_router_dataset import build_dataset
        # Authored offline fixtures, not new benchmark or efficacy samples.
        for count, expected in ((16, None), (80, .65)):
            records = [DatasetTests().record('dev')]
            for index in range(count):
                record = DatasetTests().record(str(index), 'calibration')
                task = f'Read budget {index}'
                record['packet']['trusted_user_request'] = task
                record['packet']['current_actions'][0]['host_tool_description'] = task
                from dscg.audit_router import digest
                record['input_sha256'] = digest(record['packet'])
                records.append(record)
            src = self.root/f'input_{count}.jsonl'
            src.write_text(''.join(json.dumps(row)+'\n' for row in records))
            dataset = self.root/f'dataset_{count}'
            build_dataset(src, dataset)
            output = self.root/f'artifact_{count}.json'
            with redirect_stdout(StringIO()):
                self.assertEqual(cli.main(['--dataset-dir', str(dataset), '--preset', str(PRESET),
                    '--attest-independent-groups', '--output', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())['calibration']['threshold'], expected)

