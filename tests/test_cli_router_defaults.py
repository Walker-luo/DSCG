"""CLI shadow defaults respect baseline/NoChecker; no model construction."""
from contextlib import redirect_stderr
from io import StringIO
import unittest
from unittest.mock import patch

from experiments import run_benchmark as full
from experiments import run_partial_benchmark as partial


class CliRouterDefaultTests(unittest.TestCase):
    def test_defended_cli_defaults_to_shadow_for_both_task_scopes(self):
        for entry in (partial.cli, full.cli):
            with self.subTest(entry=entry), patch.object(partial, 'main', return_value=0) as run:
                self.assertEqual(entry([]), 0)
                self.assertEqual(run.call_args.kwargs['audit_router_mode'], 'shadow')

    def test_baseline_and_no_checker_implicitly_disable_routing(self):
        for entry in (partial.cli, full.cli):
            for flags in (['--baseline'], ['--baseline', '--clean'], ['--no-checker']):
                with self.subTest(entry=entry, flags=flags), patch.object(partial, 'main', return_value=0) as run:
                    self.assertEqual(entry(flags), 0)
                    self.assertEqual(run.call_args.kwargs['audit_router_mode'], 'off')

    def test_explicit_routing_modes_are_preserved(self):
        for entry in (partial.cli, full.cli):
            for mode in ('off', 'shadow', 'selective'):
                with self.subTest(entry=entry, mode=mode), patch.object(partial, 'main', return_value=0) as run:
                    self.assertEqual(entry(['--audit-router-mode', mode]), 0)
                    self.assertEqual(run.call_args.kwargs['audit_router_mode'], mode)

    def test_explicit_incompatible_modes_remain_errors(self):
        for entry in (partial.cli, full.cli):
            for flags in (['--baseline'], ['--no-checker']):
                for mode in ('shadow', 'selective'):
                    with self.subTest(entry=entry, flags=flags, mode=mode), redirect_stderr(StringIO()), patch.object(
                        partial, 'main', return_value=0
                    ) as run, self.assertRaises(SystemExit):
                        entry([*flags, '--audit-router-mode', mode])
                    run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
