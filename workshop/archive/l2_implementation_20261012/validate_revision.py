"""Read-only scoped revision validation; never rewrite prior evidence or hashes."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / 'workshop/artifacts/20261012_l2_implementation'
ARCHIVE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def local_links(text):
    return {m.group(1).strip('<>') for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', text)
            if not re.match(r'[a-zA-Z]+:', m.group(1)) and not m.group(1).startswith('#')}

def validate():
    before = json.loads((TASK/'before.json').read_text())
    manifest = json.loads((ARCHIVE/'revision_manifest.json').read_text())
    errors=[];existing_broken=[];new_links=0
    for entry in manifest['files']:
        current=ROOT/entry['path']
        if not current.is_file() or digest(current)!=entry['after_sha256']:
            errors.append('current hash mismatch: '+entry['path'])
        if entry.get('original'):
            stored=ROOT/entry['original']
            if not stored.is_file() or digest(stored)!=entry['before_sha256']:
                errors.append('original hash mismatch: '+entry['path'])
        if current.suffix=='.md' and current.exists():
            old=(ROOT/entry['original']).read_text() if entry.get('original') else ''
            old_links=local_links(old)
            for link in local_links(current.read_text()):
                target=(current.parent/link.split('#')[0]).resolve()
                if link not in old_links: new_links+=1
                if not target.exists():
                    value={'document':entry['path'],'link':link}
                    if link in old_links: existing_broken.append(value)
                    else: errors.append('new broken link: '+str(value))
    allowed={entry['path'] for entry in manifest['files']}
    unchanged=0
    for path,sha in before['sources'].items():
        if path in allowed: continue
        if digest(ROOT/path)!=sha: errors.append('out-of-scope source change: '+path)
        else: unchanged+=1
    for path,sha in before['preserved_documents'].items():
        if digest(ROOT/path)!=sha: errors.append('protected document changed: '+path)
    for path,meta in before['protected_files'].items():
        target=ROOT/path
        if not target.is_file(): errors.append('protected file missing: '+path);continue
        stat=target.stat()
        if {'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns}!=meta:
            errors.append('protected output metadata changed: '+path)
    if digest(ROOT/before['previous_manifest'])!=before['previous_manifest_sha256']:
        errors.append('prior revision manifest changed')
    if digest(ROOT.parent/'research/technical_route.md')!=before['incoming_route_sha256']:
        errors.append('formal route changed')
    status=(ROOT.parent/'research/paper/implementation_status.md').read_bytes()
    if hashlib.sha256(status[:before['research_status_before_bytes']]).hexdigest()!=before['research_status_before_sha256']:
        errors.append('research status original prefix changed')
    for path in ('README.md','workshop/README.md','workshop/completed/README.md','docs/framework_updates.md',
                 'docs/dashboard.md','dashboard/templates/index.html'):
        if 'three-layer-l2-v2' not in (ROOT/path).read_text(): errors.append('version display stale: '+path)
    if (ROOT/'workshop/L2_implementation_plan_20261012.md').exists(): errors.append('completed plan still at top level')
    return dict(status='pass' if not errors else 'fail',errors=errors,
                scoped_manifest_files=len(manifest['files']),unchanged_source_files=unchanged,
                original_snapshots=sum(bool(e.get('original')) for e in manifest['files']),
                preserved_documents=len(before['preserved_documents']),protected_output_files=len(before['protected_files']),
                output_protection_unit='size+mtime_ns, not new content hashes',new_local_links_checked=new_links,
                preexisting_broken_links=existing_broken,formal_route_unchanged=True if not any('formal route' in e for e in errors) else False,
                limitations=['Scoped current revision only; not full historical migration verification.',
                             'Output protection is baseline metadata comparison; no newly claimed content hashes.',
                             'Existing broken historical links are reported separately, not silently repaired.'])

if __name__=='__main__':
    result=validate();print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['status']=='pass' else 1)
