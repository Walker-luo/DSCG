"""Read-only current documentation revision check; no historical hash rewriting."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
TASK=ROOT/'workshop/artifacts/20261013_l2_docs_sync'
ARCHIVE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def links(text):
 return {m.group(1).strip('<>') for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)',text)
         if not re.match(r'[a-zA-Z]+:',m.group(1)) and not m.group(1).startswith('#')}

def validate():
 b=json.loads((TASK/'before.json').read_text());m=json.loads((ARCHIVE/'revision_manifest.json').read_text())
 errors=[];broken_old=[];link_count=0
 for e in m['files']:
  p=ROOT/e['path']
  if not p.is_file() or sha(p)!=e['after_sha256']:errors.append('current hash changed: '+e['path'])
  old_text=''
  if e.get('original'):
   old=ROOT/e['original']
   if not old.is_file() or sha(old)!=e['before_sha256']:errors.append('original bytes changed: '+e['path'])
   else:old_text=old.read_text()
  if p.suffix=='.md':
   for link in links(p.read_text()):
    link_count+=1
    if not (p.parent/link.split('#')[0]).exists():
     record={'document':e['path'],'link':link}
     if link in links(old_text):broken_old.append(record)
     else:errors.append('new missing link: '+str(record))
 for name,sha_before in b['sources'].items():
  if not (ROOT/name).is_file() or sha(ROOT/name)!=sha_before:errors.append('runtime/UI/test/config changed: '+name)
 for field in ('previous_archives','preserved_documents'):
  for name,sha_before in b[field].items():
   if not (ROOT/name).is_file() or sha(ROOT/name)!=sha_before:errors.append('protected bytes changed: '+name)
 for name,meta in b['protected_outputs'].items():
  p=ROOT/name
  if not p.is_file():errors.append('user output removed: '+name);continue
  stat=p.stat()
  if {'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns}!=meta:errors.append('user output metadata changed: '+name)
 if sha(ROOT.parent/'research/technical_route.md')!=b['route_sha256']:errors.append('formal route changed')
 status=(ROOT.parent/'research/paper/implementation_status.md').read_bytes()
 if hashlib.sha256(status[:b['research_status_bytes']]).hexdigest()!=b['research_status_sha256']:errors.append('research status original prefix changed')
 for name in ('README.md','workshop/L2_opt.md','workshop/README.md','workshop/completed/README.md','docs/README.md','docs/framework_updates.md','docs/dashboard.md'):
  if 'three-layer-l2-v2.2' not in (ROOT/name).read_text():errors.append('current version absent: '+name)
 if '待' not in (ROOT/'docs/framework_updates.md').read_text() or '固定标签' not in (ROOT/'docs/dashboard.md').read_text():errors.append('stale platform labels not explicitly pending')
 if 'three-layer-l2-v2.2' in (ROOT/'dashboard/templates/index.html').read_text():errors.append('unexpected platform implementation')
 current=json.loads((TASK/'latest_results.json').read_text())
 if current['status']!='pass':errors.append('latest-results audit not passed')
 for path,expected in current['input_sha256'].items():
  if sha(ROOT/path)!=expected:errors.append('reviewed input changed: '+path)
 if current['latest_totals']['total']!=144 or current['latest_totals']['utility_true']!=130 or current['latest_totals']['native_asr_true']!=0:errors.append('documented current denominators differ')
 if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=b['head']:errors.append('HEAD changed during review')
 return dict(status='pass' if not errors else 'fail',errors=errors,original_docs=len(b['originals']),current_local_links_checked=link_count,
 preexisting_broken_links=broken_old,unchanged_sources=len(b['sources']),preserved_docs=len(b['preserved_documents']),
 unchanged_prior_archive_files=len(b['previous_archives']),protected_user_output_metadata=len(b['protected_outputs']),
 current_result_input_hashes=len(current['input_sha256']),latest_record_denominator=144,
 formal_route_unchanged=True if not any('formal route' in e for e in errors) else False,
 limitations=['Current docs/source review only; not full historical migration or real E0 validation.',
 'Old input hash differences remain recorded separately; no expected hashes changed.',
 'Output preservation compares baseline size/mtime; not a new full-content hash audit.',
 'Platform display version/rule synchronization is pending, not shipped by this docs-only task.'])

if __name__=='__main__':
 result=validate();print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['status']=='pass' else 1)
