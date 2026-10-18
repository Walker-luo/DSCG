"""Metadata identification and explicit configuration matching, without source scans."""
from pathlib import Path
from types import SimpleNamespace
import json
import unittest
from unittest.mock import patch

from dscg import benchmark_catalog as catalog
from experiments.common import benchmark_reuse as reuse


class LightweightIdentityTests(unittest.TestCase):
    def test_tool_metadata_contents_are_bound_but_selection_path_is_provenance(self):
        identity = catalog.benchmark_identity()
        binding = {'benchmark':identity, 'tool_metadata':{'read':{'risk_level':'low'}},
                   'tool_metadata_selection':{'path':'/old/tools.toml', 'source':'explicit'}}
        moved = {**binding, 'tool_metadata_selection':{'path':'/new/tools.toml', 'source':'backend_local'}}
        self.assertTrue(reuse._compatible_binding(binding, moved))
        self.assertFalse(reuse._compatible_binding(binding,
            {**moved, 'tool_metadata':{'read':{'risk_level':'critical'}}}))

    def test_effective_nested_source_fields_and_tool_names_are_not_provenance(self):
        identity = catalog.benchmark_identity()
        binding = {'benchmark':identity, 'tool_metadata':{'read':{'source':'calendar'},
                                                       'source':{'risk_level':'critical'}}}
        self.assertFalse(reuse._compatible_binding(binding,
            {**binding, 'tool_metadata':{'read':{'source':'email'}, 'source':{'risk_level':'critical'}}}))
        self.assertFalse(reuse._compatible_binding(binding,
            {**binding, 'tool_metadata':{'read':{'source':'calendar'}}}))

    def test_shadowed_import_path_is_rejected(self):
        dist = SimpleNamespace(version='0.1.35', read_text=lambda _: None,
                               locate_file=lambda _: Path('/installed/agentdojo'))
        with patch.object(catalog, 'distribution', return_value=dist), \
             patch.object(catalog, '_package_root', return_value=Path('/shadowed/agentdojo')):
            with self.assertRaisesRegex(ValueError, 'path'):
                catalog.benchmark_identity()

    def test_informational_source_metadata_is_resolved_once_without_source_reads(self):
        from experiments.common import partial_controls as controls
        controls._source_metadata.cache_clear()
        with patch.object(controls.subprocess, 'check_output', return_value='fixture-commit\n') as git, \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('source read')):
            self.assertNotIn('source_sha256', controls.source_revision())
            self.assertNotIn('source_sha256', controls.source_revision())
            self.assertEqual(git.call_count, 1)
        controls._source_metadata.cache_clear()

    def test_backend_metadata_does_not_scan_or_read_source(self):
        dist = SimpleNamespace(version='0.1.35', read_text=lambda _: None)
        with patch.object(catalog, 'distribution', return_value=dist), \
             patch.object(catalog, '_package_root', return_value=Path('/fixture/agentdojo')), \
             patch.object(Path, 'rglob', side_effect=AssertionError('source scan')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('source hash')):
            identity = catalog.benchmark_identity()
        self.assertEqual(identity['id'], 'agentdojo')
        self.assertEqual(identity['verification_mode'], 'metadata_only')
        self.assertEqual(identity['runtime_variant'], 'unverified')
        self.assertFalse(any(k.endswith('_sha256') for k in identity))

    def test_old_source_hash_and_python_patch_are_not_resume_requirements(self):
        identity = catalog.benchmark_identity()
        binding = {'schema_version': 'dscg.partial-run.v2', 'benchmark': identity,
                   'main_model': {'model_id': 'offline'}, 'profile': 'baseline',
                   'task_selection': {'users': ['u0'], 'injections': ['i0']},
                   'attack': 'tool_knowledge', 'source': {'python': '3.10.19', 'source_sha256': {'x': 'old'}}}
        changed = {**binding, 'source': {'python': '3.10.21', 'source_sha256': {'x': 'new'}}}
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('source read')):
            self.assertTrue(reuse._compatible_binding(binding, changed))
        for key, value in [('main_model', {'model_id': 'different'}), ('profile', 'full'),
                           ('attack', 'ignore_previous'), ('task_selection', {'users': ['other']})]:
            self.assertFalse(reuse._compatible_binding(binding, {**changed, key: value}))


if __name__ == '__main__':
    unittest.main()
