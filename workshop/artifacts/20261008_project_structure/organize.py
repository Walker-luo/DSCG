"""One-time, byte-preserving documentation archive; refuses destination reuse."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'workshop/archive/project_structure_20261008'
MANIFEST = OUT / 'structure_manifest.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(root):
    records = []
    for p in sorted(root.rglob('*')):
        if p.is_file():
            st = p.stat()
            records.append((str(p.relative_to(ROOT)), st.st_size, st.st_mtime_ns))
    return {'files': len(records), 'size_mtime_sha256': hashlib.sha256(json.dumps(records).encode()).hexdigest()}

assert not MANIFEST.exists(), 'One-time manifest already exists'
assert not ARCHIVE.exists(), 'Archive destination already exists'
base = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
protected = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z', '--', 'dscg', 'tests', 'experiments', 'dashboard', 'config', 'assets', 'environment.yml'], text=True).split('\0')
manifest = {
    'schema_version': 1, 'dscg_base_revision': base,
    'scope': 'Documentation/layout only; archived originals are historical, not current instructions',
    'artifact_policy': 'workshop/artifacts/<YYYYMMDD>_<task>/',
    'protected_tracked_files': {s: sha(ROOT / s) for s in protected if s},
    'research_route_sha256': sha(ROOT.parent / 'research/technical_route.md'),
    'raw_result_inventories': {name: inventory(ROOT / name) for name in ('results', 'download')},
    'baseline_snapshots': [], 'archived_files': [], 'retired_aliases': [], 'removed_generated_caches': [],
}
for name in ('README.md', 'AGENTS.md', 'RESEARCH_STATUS.md', '.gitignore', 'workshop/README.md', 'workshop/verify_migration.py'):
    src, dest = ROOT / name, ARCHIVE / 'before' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    manifest['baseline_snapshots'].append({'old_path': name, 'archive_path': str(dest.relative_to(ROOT)), 'sha256': sha(dest)})
paths = [p for p in (ROOT / 'docs').rglob('*') if p.is_file() and not p.is_symlink() and p.name != '.DS_Store' and p.name != 'i3_p0_stress_report.md']
for src in sorted(paths):
    dest = ARCHIVE / src.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = sha(src)
    src.rename(dest)
    manifest['archived_files'].append({'old_path': str(src.relative_to(ROOT)), 'new_path': str(dest.relative_to(ROOT)), 'sha256': digest, 'reason': 'Historical report/introduction/figure/prompt; removed from current docs entry'})
for name, new in (
    ('ALMML_sub.md', 'workshop/ALMML_sub.md'),
    ('AIMLL WS.pdf', 'workshop/references/AIMLL WS.pdf'),
    ('Paper_TODO.md', 'workshop/archive/project_structure_20261008/Paper_TODO.md'),
):
    src, dest = ROOT / name, ROOT / new
    assert not dest.exists(), dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = sha(src)
    src.rename(dest)
    manifest['archived_files'].append({'old_path': name, 'new_path': new, 'sha256': digest, 'reason': 'Workshop ownership or redundant research pointer'})
old_manifest = json.loads((ROOT / 'workshop/results/materials_migration_20261008/migration_manifest.json').read_text())
for e in old_manifest['entries']:
    old = ROOT.parent / e['legacy_read_path']
    if e['kind'] == 'document' and e['old_path'].startswith('DSCG/docs/') and old.name != 'framework_v2_followup_report.md':
        assert old.is_symlink() and sha(old) == e['sha256_before']
        manifest['retired_aliases'].append({'legacy_read_path': e['legacy_read_path'], 'original_storage': e['original_storage'], 'sha256_before': e['sha256_before'], 'link_target': str(old.readlink()), 'reason': 'Retired old docs entry; original evidence bytes remain under workshop'})
        old.unlink()
for src in (ROOT / 'docs').rglob('.DS_Store'):
    manifest['removed_generated_caches'].append(str(src.relative_to(ROOT)))
    src.unlink()
for directory in sorted((ROOT / 'docs').rglob('*'), key=lambda p: len(p.parts), reverse=True):
    if directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()
manifest['previous_migration_evidence'] = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'workshop/results/materials_migration_20261008').iterdir() if p.is_file()}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'archived_files': len(manifest['archived_files']), 'baseline_snapshots': len(manifest['baseline_snapshots']), 'retired_aliases': len(manifest['retired_aliases'])}))
