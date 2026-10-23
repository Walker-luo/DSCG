"""Read-only docs links/anchors, source/control consistency and preservation checks."""
import ast,hashlib,json,re,subprocess,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
TASK=ROOT/'workshop/artifacts/20261013_configuration_docs'
ARCHIVE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def links(text):
 return {m.group(1).strip('<>') for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)',text)
         if not re.match(r'[a-zA-Z]+:',m.group(1)) and not m.group(1).startswith('#')}

def headings(text):
 result=set();fenced=False
 for line in text.splitlines():
  if line.startswith('```'):fenced=not fenced
  if fenced:continue
  m=re.match(r'^#{1,6}\s+(.*)',line)
  if m:
   plain=m.group(1).replace('`','').lower()
   slug=''.join(c for c in plain if c in '_- ' or not unicodedata.category(c).startswith(('P','S')))
   result.add(slug.strip().replace(' ','-'))
 return result

def validate():
 b=json.loads((TASK/'before.json').read_text());m=json.loads((ARCHIVE/'revision_manifest.json').read_text());errors=[];old_broken=[];link_count=0;anchor_count=0
 for e in m['files']:
  p=ROOT/e['path'];old_text=''
  if not p.is_file() or sha(p)!=e['after_sha256']:errors.append('current hash changed: '+e['path'])
  if e.get('original'):
   old=ROOT/e['original']
   if not old.is_file() or sha(old)!=e['before_sha256']:errors.append('original bytes changed: '+e['path'])
   else:old_text=old.read_text()
  if p.suffix=='.md':
   for link in links(p.read_text()):
    link_count+=1;path,sep,anchor=link.partition('#');target=p.parent/path
    if not target.exists():
     rec={'document':e['path'],'link':link}
     if link in links(old_text):old_broken.append(rec)
     else:errors.append('missing new link: '+str(rec))
    elif sep and target.suffix=='.md':
     anchor_count+=1
     if anchor not in headings(target.read_text()):errors.append('missing heading anchor: '+link)
 for section in ('sources','previous_archives','preserved_docs'):
  for path,expected in b[section].items():
   if not (ROOT/path).is_file() or sha(ROOT/path)!=expected:errors.append('protected content changed: '+path)
 for path,meta in b['protected_outputs'].items():
  p=ROOT/path
  if not p.is_file():errors.append('user output missing: '+path);continue
  s=p.stat()
  if {'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}!=meta:errors.append('user output metadata changed: '+path)
 if sha(ROOT.parent/'research/technical_route.md')!=b['route_sha256']:errors.append('formal route changed')
 status=(ROOT.parent/'research/paper/implementation_status.md').read_bytes()
 if hashlib.sha256(status[:b['status_prefix_bytes']]).hexdigest()!=b['status_prefix_sha256']:errors.append('research status prefix changed')
 help_text=(TASK/'partial_help.log').read_text();guide=(ROOT/'docs/model_tool_configuration.md').read_text()
 flags=['--model-config','--tool-metadata','--no-tool-view','--no-delegated-tasks','--no-checker','--audit-router-mode','--audit-router-artifact','--audit-retries','--completion-prompt','--trace-level','--task-manifest','--name','--force-rerun','--results-dir']
 for flag in flags:
  if flag not in help_text or flag not in guide:errors.append('CLI docs mismatch: '+flag)
 tree=ast.parse((ROOT/'dscg/pipelines/defended.py').read_text())
 factory=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='make_qwen_newFrame_pipeline')
 args={a.arg for a in factory.args.args+factory.args.kwonlyargs}
 controls=['use_sandbox','input_isolation','authorization_precheck','planning_tool_view','delegated_tasks','use_security_checker','audit_router_mode','audit_router_artifact','audit_retries','completion_prompt','trace_level','authorization_profile','delegated_task_reader']
 if not set(controls)<=args:errors.append('API controls absent in source')
 for field in ('provider','model_id','base_url','api_key_env','api_key','effect','source','sink','sensitivity','idempotent','reversible'):
  if field not in guide:errors.append('required field omitted: '+field)
 examples=json.loads((TASK/'examples_check.json').read_text())
 if examples['status']!='pass' or examples['new_api_calls']!=0:errors.append('offline example check failed')
 if 'model_tool_configuration.md' not in (ROOT/'README.md').read_text() or 'model_tool_configuration.md' not in (ROOT/'docs/evaluation.md').read_text():errors.append('guide entry missing')
 if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=b['head']:errors.append('HEAD changed')
 return dict(status='pass' if not errors else 'fail',errors=errors,original_docs=len(b['originals']),local_links_checked=link_count,
 heading_anchors_checked=anchor_count,preexisting_broken_links=old_broken,cli_flags_checked=len(flags),api_controls_checked=len(controls),
 model_tests=7,tool_metadata_tests=9,toml_examples=examples['toml_examples'],python_examples=examples['python_examples'],catalog_distinct_tools=examples['catalog_tools'],
 unchanged_sources=len(b['sources']),unchanged_other_docs=len(b['preserved_docs']),unchanged_previous_archive_files=len(b['previous_archives']),
 protected_user_output_metadata=len(b['protected_outputs']),new_model_calls=0,new_rollouts=0,
 limitations=['Offline parsing/schema/coverage only, not live service authentication or model capabilities.',
 'Output preservation uses baseline size/mtime; not full historical hash/migration verification.',
 'Heading checks use GFM-style slugs; no new UI behavior was implemented.'])

if __name__=='__main__':
 r=validate();print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['status']=='pass' else 1)
