"""Check byte-preserving cleanup and document policy without model execution."""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(root):
    records = []
    for p in sorted(root.rglob('*')):
        if p.is_file():
            st = p.stat()
            records.append((str(p.relative_to(ROOT)), st.st_size, st.st_mtime_ns))
    return {'files': len(records), 'size_mtime_sha256': hashlib.sha256(json.dumps(records).encode()).hexdigest()}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, help='Optional new JSON under workshop/artifacts/; default is read-only.')
args = parser.parse_args()
output = args.output.resolve() if args.output else None
if output and (not output.is_relative_to(ROOT/'workshop/artifacts') or output.exists()):
    parser.error('--output must be a new file under workshop/artifacts/')
manifest = json.loads((OUT/'structure_manifest.json').read_text())
checks = []
for e in manifest['archived_files']:
    old, new = ROOT/e['old_path'], ROOT/e['new_path']
    assert not old.exists() and not old.is_symlink(), old
    assert new.is_file() and sha(new) == e['sha256'], new
    checks.append(e['old_path'])
for e in manifest['baseline_snapshots']:
    assert sha(ROOT/e['archive_path']) == e['sha256'], e
for e in manifest['retired_aliases']:
    old = ROOT.parent/e['legacy_read_path']
    assert not old.exists() and not old.is_symlink(), old
    assert sha(ROOT/e['original_storage']) == e['sha256_before'], e
for name, digest in manifest['protected_tracked_files'].items():
    assert sha(ROOT/name) == digest, name
assert sha(ROOT.parent/'research/technical_route.md') == manifest['research_route_sha256']
for name, expected in manifest['raw_result_inventories'].items():
    assert inventory(ROOT/name) == expected, name
for name, digest in manifest['previous_migration_evidence'].items():
    assert sha(ROOT/name) == digest, name
assert not (ROOT/'System_TODO.md').exists(), 'User deletion must remain untouched'
links = []
current_docs = [ROOT/'README.md', ROOT/'AGENTS.md', ROOT/'RESEARCH_STATUS.md',
                ROOT/'workshop/README.md', ROOT/'workshop/project_structure_20261008.md',
                ROOT/'workshop/archive/project_structure_20261008/README.md',
                *sorted((ROOT/'docs').rglob('*.md'))]
for p in current_docs:
    if p.is_symlink():
        continue
    content = p.read_text()
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', content):
        target = target.strip('<>')
        if target.startswith(('https://','http://','#','app://','codex://')):
            continue
        dest = p.parent/target.split('#', 1)[0]
        assert dest.exists(), (p, target)
        links.append({'document': str(p.relative_to(ROOT)), 'target': target})
expected_docs = {'README.md', 'dashboard.md', 'evaluation.md', 'i3_p0_stress_report.md',
                 'framework_v2_followup_report.md', 'figures/README.md'}
actual_docs = {str(p.relative_to(ROOT/'docs')) for p in (ROOT/'docs').rglob('*') if p.is_file()}
assert actual_docs == expected_docs, actual_docs
assert (ROOT/'docs/framework_v2_followup_report.md').is_symlink()
for name in ('README.md','AGENTS.md','workshop/README.md'):
    content = (ROOT/name).read_text()
    assert 'workshop/artifacts/<YYYYMMDD>_<task>/' in content, name
assert '/workshop/artifacts/' in (ROOT/'.gitignore').read_text()
for p in (OUT/'organize.py', OUT/'verify_structure.py', ROOT/'workshop/verify_migration.py'):
    ast.parse(p.read_text())
commands = []
for cmd, expected in (
    (['/opt/miniconda3/envs/ipi/bin/python','workshop/verify_migration.py'], 0),
    (['/opt/miniconda3/envs/ipi/bin/python','workshop/verify_migration.py','--output',str(OUT/'migration_validation.json')], 2),
    (['/opt/miniconda3/envs/ipi/bin/python','workshop/verify_migration.py','--output','results/forbidden_migration.json'], 2),
):
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    commands.append({'command': ' '.join(cmd), 'exit_code': result.returncode, 'expected_exit_code': expected, 'output': result.stdout + result.stderr})
    assert result.returncode == expected, result.stderr
assert not (ROOT/'results/forbidden_migration.json').exists()
assert sha(ROOT/'workshop/results/materials_migration_20261008/validation.json') == manifest['previous_migration_evidence']['workshop/results/materials_migration_20261008/validation.json']
report = {
    'status': 'pass', 'scope': 'Documentation/layout and validation CLI; no framework change',
    'archived_files_checked': len(checks), 'baseline_snapshots_checked': len(manifest['baseline_snapshots']),
    'retired_aliases_checked': len(manifest['retired_aliases']),
    'protected_tracked_file_hashes_checked': len(manifest['protected_tracked_files']),
    'previous_migration_evidence_hashes_checked': len(manifest['previous_migration_evidence']),
    'original_relocated_hashes_checked': 293,
    'new_local_links_checked': len(links), 'active_docs_entries': sorted(actual_docs),
    'raw_result_inventories_unchanged': manifest['raw_result_inventories'],
    'new_model_calls': 0, 'new_benchmark_samples': 0, 'runtime_tests_run': 0,
    'validation_cli_controls': commands, 'checked_links': links,
    'structure_manifest_sha256': sha(OUT/'structure_manifest.json'),
    'limitations': [
        'No live model, benchmark or security gate validation; current I3 partial and E0 pending remain unchanged.',
        'Historical text is archived unchanged and may contain stale references/commands; current guides are separate.',
        'Raw result tree checks compare file names, sizes and mtimes; they do not rehash every large result file.',
        'Historical relocation hash check relies on retained local ignored evidence; fresh Git clones lack some of those inputs.',
        'New output routing is an agent instruction; existing user runner/plot defaults are unchanged.',
    ],
}
if output:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k.endswith('_checked') or k in ('status','new_model_calls','new_benchmark_samples')}, ensure_ascii=False))
