"""Runtime profiles distinguish two same-version packages without env-name guesses."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory as _TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dscg import benchmark_catalog as catalog


def TemporaryDirectory():
    root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/catalog_tests'
    root.mkdir(parents=True, exist_ok=True)
    return _TemporaryDirectory(dir=root)


class AgentDynCatalogTests(unittest.TestCase):
    def fixture(self, directory, backend='agentdyn'):
        root=Path(directory)/'agentdojo';root.mkdir()
        path=root/'benchmark.py';path.write_text('pinned implementation')
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        lock={'schema_version':'dscg.agentdyn-lock.v1' if backend=='agentdyn' else 'dscg.agentdojo-lock.v1',
              'repository': 'https://github.com/SaFo-Lab/AgentDyn' if backend=='agentdyn' else 'https://github.com/ethz-spylab/agentdojo',
              'revision':'a'*40 if backend=='agentdyn' else 'pypi:agentdojo==0.1.35',
              'suite_version':'v1.2','package_version':'0.1.35','source_sha256':{'benchmark.py':sha},
              'release_sha256':'b'*64}
        origin={'url':lock['repository']+'.git','vcs_info':{'vcs':'git','commit_id':'a'*40}} if backend=='agentdyn' else {}
        dist=SimpleNamespace(version='0.1.35',read_text=lambda _:json.dumps(origin))
        return root,path,lock,origin,dist

    def test_active_suites_are_derived_from_installed_package(self):
        for backend, suites in [('agentdojo',('workspace','travel','banking','slack')),
                                ('agentdyn',('shopping','github','dailylife'))]:
            with self.subTest(backend=backend),TemporaryDirectory() as directory:
                root,path,lock,origin,dist=self.fixture(directory,backend)
                with patch.object(catalog,'_package_root',return_value=root),patch.object(catalog,'distribution',return_value=dist),patch.object(catalog,'_load_lock',return_value=lock,create=True):
                    profile=catalog.get_backend()
                    self.assertEqual(profile.id,backend)
                    self.assertEqual(catalog.get_suites(),suites)
                    self.assertIn(backend,profile.tool_metadata_path.name)
                    wrong='banking' if backend=='agentdyn' else 'shopping'
                    with self.assertRaises(catalog.BenchmarkConfigurationError):catalog.get_suite('v1.2',wrong)

    def test_content_and_git_origin_are_both_verified(self):
        with TemporaryDirectory() as directory:
            root,path,lock,origin,dist=self.fixture(directory)
            with patch.object(catalog,'_package_root',return_value=root),patch.object(catalog,'distribution',return_value=dist),patch.object(catalog,'_load_lock',return_value=lock,create=True):
                identity=catalog.validate_backend()
                self.assertEqual(identity['revision'],'a'*40)
                for role in ('tasks','environments','attacks','tools'):
                    self.assertRegex(identity[role+'_sha256'],r'^[a-f0-9]{64}$')
                path.write_text('changed implementation')
                with self.assertRaisesRegex(catalog.BenchmarkConfigurationError,'hash|哈希'):catalog.validate_backend()

    def test_official_release_supports_only_exact_reviewed_client_variant(self):
        with TemporaryDirectory() as directory:
            root,path,lock,origin,dist=self.fixture(directory,'agentdojo')
            original=catalog._digest(lock['source_sha256'])
            path.write_text('reviewed local client')
            lock['runtime_variants']={'local-client-reviewed':{'benchmark.py':hashlib.sha256(path.read_bytes()).hexdigest()}}
            with patch.object(catalog,'_package_root',return_value=root),patch.object(catalog,'distribution',return_value=dist),patch.object(catalog,'_load_lock',return_value=lock,create=True):
                identity=catalog.validate_backend()
                self.assertEqual(identity['runtime_variant'],'local-client-reviewed')
                self.assertNotEqual(identity['implementation_sha256'],original)
                path.write_text('unknown client edit')
                with self.assertRaises(catalog.BenchmarkConfigurationError):catalog.validate_backend()

    def test_unknown_git_origin_does_not_fall_back_to_official_release(self):
        with TemporaryDirectory() as directory:
            root,path,lock,origin,dist=self.fixture(directory)
            origin['url']='https://example.invalid/unreviewed.git'
            with patch.object(catalog,'_package_root',return_value=root),patch.object(catalog,'distribution',return_value=dist),patch.object(catalog,'_load_lock',return_value=lock,create=True):
                with self.assertRaisesRegex(catalog.BenchmarkConfigurationError,'source|origin|来源'):catalog.validate_backend()

    def test_wrong_git_revision_cannot_match_another_backend(self):
        with TemporaryDirectory() as directory:
            root,path,lock,origin,dist=self.fixture(directory)
            origin['vcs_info']['commit_id']='c'*40
            with patch.object(catalog,'_package_root',return_value=root),patch.object(catalog,'distribution',return_value=dist),patch.object(catalog,'_load_lock',return_value=lock,create=True):
                with self.assertRaisesRegex(catalog.BenchmarkConfigurationError,'revision|提交'):catalog.validate_backend()

    def test_missing_lock_is_rejected(self):
        with patch.object(catalog,'_load_lock',side_effect=catalog.BenchmarkConfigurationError('lock missing'),create=True):
            with self.assertRaisesRegex(catalog.BenchmarkConfigurationError,'lock'):catalog.validate_backend()

    def test_added_source_file_cannot_silently_change_registered_catalog(self):
        with TemporaryDirectory() as directory:
            root,path,lock,origin,dist=self.fixture(directory)
            (root/'extra_task.py').write_text('unreviewed registration')
            with patch.object(catalog,'_package_root',return_value=root),patch.object(catalog,'distribution',return_value=dist),patch.object(catalog,'_load_lock',return_value=lock):
                with self.assertRaisesRegex(catalog.BenchmarkConfigurationError,'file set|source'):
                    catalog.validate_backend()
