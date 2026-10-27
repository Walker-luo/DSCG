"""Runtime profiles distinguish two same-version packages without env-name guesses."""

from artifact_support import ensure_artifacts
ensure_artifacts('test_agentdyn_catalog')
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory as _TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from baseintent import benchmark_catalog as catalog


def TemporaryDirectory():
    root = Path(__file__).resolve().parents[1] / 'artifacts/tests/test_agentdyn_catalog'
    root.mkdir(parents=True, exist_ok=True)
    return _TemporaryDirectory(dir=root)


class AgentDynCatalogTests(unittest.TestCase):
    def fixture(self, directory, backend='agentdyn'):
        root=Path(directory)/'agentdojo';root.mkdir()
        path=root/'benchmark.py';path.write_text('pinned implementation')
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        lock={'schema_version':'baseintent.agentdyn-lock.v1' if backend=='agentdyn' else 'baseintent.agentdojo-lock.v1',
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

    def test_metadata_only_does_not_certify_content_or_client_variant(self):
        for backend in ('agentdojo', 'agentdyn'):
            with self.subTest(backend=backend), TemporaryDirectory() as directory:
                root,path,lock,origin,dist=self.fixture(directory,backend)
                with patch.object(catalog,'_package_root',return_value=root), patch.object(catalog,'distribution',return_value=dist), patch.object(catalog,'_load_lock',return_value=lock), patch.object(Path,'rglob',side_effect=AssertionError('source scan')):
                    identity=catalog.validate_backend()
                    self.assertEqual(identity['verification_mode'],'metadata_only')
                    self.assertEqual(identity['runtime_variant'],'unverified')
                    path.write_text('changed implementation')
                    self.assertEqual(catalog.validate_backend(),identity)

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

    def test_additional_source_files_are_not_scanned(self):
        with TemporaryDirectory() as directory:
            root,path,lock,origin,dist=self.fixture(directory)
            (root/'extra_task.py').write_text('extra source')
            with patch.object(catalog,'_package_root',return_value=root), patch.object(catalog,'distribution',return_value=dist), patch.object(catalog,'_load_lock',return_value=lock):
                self.assertEqual(catalog.validate_backend()['id'],'agentdyn')
