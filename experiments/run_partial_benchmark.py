import argparse
from contextlib import closing
import os
from pathlib import Path
import csv
from time import monotonic
from uuid import uuid4
from types import SimpleNamespace
from copy import copy

from agentdojo import logging, benchmark, attacks
from agentdojo.attacks.attack_registry import ATTACKS
from dscg.benchmark_catalog import get_suite, benchmark_identity, validate_backend, get_backend, get_suites, SUITE_VERSION
import json

from dscg.model_config import ModelConfigurationError, resolve_model_config
from dscg.paths import RESULTS_DIR, BENCHMARK_RESULTS_DIR
from dscg.audit_router import (DEFAULT_THRESHOLD, POLICY_VERSION as ROUTER_POLICY_VERSION,
                               validate_router_options, summarize_events, LocalAuditRouter)
from dscg.input_isolation import FRAMEWORK_VERSION, framework_version_for_profile
from dscg.l1_projection import MODES as L1_PROJECTION_MODES, PROFILE_SHA256 as L1_PROFILE_SHA256
from dscg.pipelines.baseline import make_openai_compatible_pipeline
from dscg.pipelines.defended import make_defended_pipeline, router_configuration_hash, defended_pipeline_name
from dscg.prompt_profiles import PROFILES as PROMPT_PROFILES, resolve_profile, validate_profile, profile_binding
from dscg.intent_evidence import audit_model_settings
from dscg.tool_metadata import ToolMetadataError, load_tool_metadata, validate_benchmark_tool_metadata, resolve_tool_metadata
from experiments.common.benchmark_outcomes import project_outcomes
from dscg.task_diagnostics import OUTCOME_PROJECTION_VERSION
from experiments.common.partial_reporting import collect_suite_report, write_run_overview
from experiments.common.partial_controls import (validate_controls, make_task_manifest, load_task_manifest,
                                          select_tasks, guard_run, source_revision, preserve_cached_cost,
                                          RunConfigurationError)
from experiments.common.benchmark_reuse import ReusePlan, execution_plan
from experiments.common.result_paths import (
    safe_result_component as _safe_result_component, run_component, resolve_run_path, result_layout,
)
from experiments.common.benchmark_execution import run_lock
from experiments.common.run_bindings import RunBindings, LAYOUT
from experiments.common.injection_filter import load_fliter, filter_digest, excluded_ids
from experiments.common.goal_stage import run_goal_checks
from experiments.common.attack_execution import iter_attack_results, AttackOutput
from experiments.common.benchmark_progress import GroupProgress, run_suite_with_progress
from experiments.common.error_diagnostics import execution_error_diagnostics
from experiments.common.native_cache_compat import ensure_native_cache_model_ready
from experiments.common.attack_compatibility import check_attack_compatibility


TYPICAL_ATTACKS = (
    "ignore_previous", "important_instructions", "tool_knowledge",
)


def _apply_run_name(pipeline, resolved_model_id: str | None, run_name: str | None) -> str:
    """Name a run; its backend is represented by the parent directory."""
    pipeline.name = run_component(resolved_model_id, run_name, default_name=pipeline.name)
    return pipeline.name


def resolve_attack_names(selection: str | list[str] = "typical") -> list[str]:
    """Resolve automatic attacks without starting a model or prompting for input."""
    available = sorted(name for name in ATTACKS if name != "manual")
    names = [selection] if isinstance(selection, str) else list(selection)
    if not names:
        raise ValueError("至少指定一个攻击，或使用 typical / all。")
    presets = set(names) & {"typical", "all"}
    if presets:
        if len(set(names)) != 1:
            raise ValueError("typical / all 不能与其他预设或具体攻击名称同时使用。")
        if "all" in presets:
            return available
        missing = sorted(set(TYPICAL_ATTACKS) - set(available))
        if missing:
            raise ValueError(f"典型攻击未注册: {', '.join(missing)}")
        return list(TYPICAL_ATTACKS)
    unknown = sorted(set(names) - set(available))
    if unknown:
        raise ValueError(f"未知攻击: {', '.join(unknown)}")
    return list(dict.fromkeys(names))


def _validate_router_controls(origin, use_security_checker, mode, use_sandbox=True):
    if mode not in {"off","shadow","selective"}:
        raise ValueError("unknown audit-router mode")
    if mode != "off" and (origin or not use_security_checker or not use_sandbox):
        raise ValueError("audit routing requires the defended pipeline with L2 and checker")


def _validate_prompt_profile(origin, use_sandbox, use_checker, profile):
    profile = resolve_profile(profile, origin=origin)
    if (origin and profile != 'legacy') or (profile not in ('legacy', 'static-task-v352', 'static-task-v354', 'static-task-v361') and (not use_sandbox or not use_checker)):
        raise ValueError('candidate prompt profiles require the defended pipeline with L2 and checker')
    return profile


def _router_trace_summary(suite_dir, task_keys, attack_name, run_attack):
    from dscg.task_diagnostics import load_task_trace
    events=[];recorded=0
    unavailable=0
    for key in task_keys:
        injection=key[1] if len(key)>1 and run_attack else "none"
        from experiments.common.task_paths import trace_path
        path=trace_path(suite_dir, str(key[0]), attack_name, injection)
        try:
            if not path.resolve().is_relative_to(suite_dir.resolve()):continue
            trace=load_task_trace(path)
            if trace.get('dscg_diagnostics_status') in ('missing','corrupt','invalid_reference','incomplete'):
                unavailable+=1;continue
            value=trace.get("dscg_router_events")
            if isinstance(value,list) and all(isinstance(e,dict) for e in value):
                recorded+=1;events.extend(value)
        except (OSError,ValueError,AttributeError):continue
    return {**summarize_events(events),"expected_task_traces":len(task_keys),"recorded_task_traces":recorded,
            "diagnostic_unavailable_traces":unavailable,
            "scope":"recorded scored traces only; missing routing traces are unknown"}


def _describe_pipeline(model_id, sec_model_id, *, origin, defense, **options):
    """Resolve public identity without clients, pipelines, attacks or model requests."""
    prompt_profile = _validate_prompt_profile(origin, options['use_sandbox'], options['use_security_checker'], options.get('prompt_profile'))
    main = resolve_model_config(model_id, prefix='DSCG_MAIN', **{
        k: options.get(k) for k in ('api_key', 'base_url', 'provider', 'api_key_env', 'config_path')})
    name = f'{main.model_id}_{defense}' if origin and defense else main.model_id
    security, optimization = {}, {}
    if not origin:
        checker, sandbox = options['use_security_checker'], options['use_sandbox']
        isolation = bool(sandbox or checker)
        projection = options['l1_projection_mode'] if isolation else 'off'
        view, delegated = options['planning_tool_view'] and sandbox, options['delegated_tasks'] and sandbox
        router, config_hash = None, None
        if checker:
            audit = resolve_model_config(sec_model_id, prefix='DSCG_SEC', fallback=main,
                config_path=options.get('config_path'), **{
                    k: options.get('sec_' + k) for k in ('api_key', 'base_url', 'provider', 'api_key_env')})
            security = audit_model_settings(audit, prompt_profile)
            config_hash = router_configuration_hash(main, audit, input_isolation=isolation,
                authorization_precheck=sandbox, l1_projection_mode=projection,
                planning_tool_view=view, delegated_tasks=delegated,
                audit_retries=options['audit_retries'], completion_prompt=options['completion_prompt'],
                prompt_profile=prompt_profile, audit_router_threshold=options.get('audit_router_threshold', DEFAULT_THRESHOLD)
                if options['audit_router_mode'] != 'off' else None, use_sandbox=sandbox)
            if sandbox or options['audit_router_mode'] != 'off':
                router = LocalAuditRouter(options['audit_router_mode'], model_config_sha256=config_hash,
                                          threshold=options.get('audit_router_threshold', DEFAULT_THRESHOLD))
        optimization = {'audit_router_config_sha256': config_hash,
                        'audit_router_threshold': router.threshold if router else None,
                        'audit_router_policy_version': ROUTER_POLICY_VERSION if router else None,
                        'audit_router_artifact_sha256': router.artifact_sha256 if router else None,
                        **profile_binding(prompt_profile)}
        name = defended_pipeline_name(main.model_id, use_sandbox=sandbox, use_security_checker=checker,
            input_isolation=isolation, authorization_precheck=sandbox, l1_projection_mode=projection,
            planning_tool_view=view, delegated_tasks=delegated, audit_router_mode=options['audit_router_mode'],
            audit_router=router, router_config_hash=config_hash, prompt_profile=prompt_profile)
    return SimpleNamespace(name=name, dscg_model_config=main.public_dict(),
                           dscg_security_model_config=security, dscg_optimization_config=optimization)


def _configured_pipeline(options, tool_metadata):
    common = {k: options.get(k) for k in ('api_key','base_url','provider','api_key_env','config_path')}
    if options.get('origin'):
        pipeline, tracker = make_openai_compatible_pipeline(options.get('model_id'), ad_defense=options.get('defense'), **common)
        return pipeline, tracker, None
    defended = {k: options.get(k) for k in ('sec_api_key','sec_base_url','sec_provider','sec_api_key_env',
        'trace_level','use_security_checker','use_sandbox','audit_retries','completion_prompt','audit_router_mode',
        'audit_router_artifact','audit_router_threshold','planning_tool_view','delegated_tasks','l1_projection_mode','prompt_profile')}
    return make_defended_pipeline(options.get('model_id'), options.get('sec_model_id'),
                                  tool_metadata=tool_metadata, **common, **defended)


def main(
    model_id: str | None = None,
    sec_model_id: str | None = None,
    suites: list[str] | None = None,
    run_attack: bool = True,
    origin=False,
    defense: str = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
    api_key_env: str | None = None,
    sec_api_key: str | None = None,
    sec_base_url: str | None = None,
    sec_provider: str | None = None,
    sec_api_key_env: str | None = None,
    config_path: str | Path | None = None,
    force_rerun: bool = False,
    reuse: bool = False,
    progress: bool = False,
    run_name: str | None = None,
    trace_level: str = "summary",
    tool_metadata_path: str | Path | None = None,
    use_security_checker: bool = True,
    audit_retries: int = 0,
    completion_prompt: bool = False,
    task_manifest_path: str | Path | None = None,
    results_dir: str | Path | None = None,
    attack: str | list[str] | None = None,
    audit_router_mode: str = "off",
    audit_router_artifact: str | Path | None = None,
    audit_router_threshold: float = DEFAULT_THRESHOLD,
    planning_tool_view: bool = True,
    delegated_tasks: bool = True,
    l1_projection_mode: str = 'projected',
    prompt_profile: str | None = None,
    task_scope: str = 'partial',
    use_sandbox: bool = True,
    fliter_path: str | Path | None = None,
    goal: bool = False,
) -> int:
    backend = get_backend()
    if task_scope not in {'partial', 'full'}:
        raise ValueError('unknown task scope')
    if reuse and (force_rerun or not run_name):
        raise ValueError('--reuse requires --name and cannot combine with force_rerun')
    if not run_attack and (fliter_path is not None or goal):
        raise ValueError('--fliter and --goal are unavailable for clean')
    if suites is None and not reuse:
        suites = list(backend.suites)
    fliter = load_fliter(fliter_path) if fliter_path is not None else None
    logdir = Path(results_dir) if results_dir is not None else BENCHMARK_RESULTS_DIR if task_scope in {'full', 'screened'} else RESULTS_DIR / "partial_benchmark"
    resume = None
    if reuse and resume is None:
        config = resolve_model_config(model_id, api_key=api_key, base_url=base_url, provider=provider,
                                      api_key_env=api_key_env, config_path=config_path)
        base = resolve_run_path(logdir, backend.id, config.model_id, run_name, allow_legacy=True)
        try:
            resume = ReusePlan(base, suites=suites, attack=attack, run_attack=run_attack,
                               task_scope=task_scope, resolve_attacks=resolve_attack_names)
        except RunConfigurationError as exc:
            print(f'❌ 续跑校验失败: {exc}', flush=True)
            return 1
        suites, attack = resume.suites, resume.attacks if run_attack else None
    suites = list(backend.suites if suites is None else suites)
    if not suites or any(name not in backend.suites for name in suites) or len(set(suites)) != len(suites):
        raise ValueError(f'suites must be a nonempty, unique selection of {", ".join(backend.suites)}')
    if not isinstance(l1_projection_mode, str) or l1_projection_mode not in L1_PROJECTION_MODES:
        raise ValueError('invalid L1 projection mode')
    prompt_profile = _validate_prompt_profile(origin, use_sandbox, use_security_checker, prompt_profile)
    audit_router_threshold = validate_router_options(audit_router_threshold, audit_router_artifact)
    _validate_router_controls(origin,use_security_checker,audit_router_mode,use_sandbox)
    validate_controls(origin=origin, use_security_checker=use_security_checker,
                      audit_retries=audit_retries, completion_prompt=completion_prompt)
    frozen_tasks = load_task_manifest(task_manifest_path)
    if frozen_tasks and frozen_tasks.get('schema_version') == 'dscg.injection-screen.v2':
        raise ValueError('old cohort manifests are read-only; supply a new fliter.json exclusion list')
    attack_names = resolve_attack_names(attack if attack is not None else 'typical') if run_attack else ["none"]
    if (fliter is not None or goal) and any(ATTACKS[name].is_dos_attack for name in attack_names if name != 'none'):
        raise ValueError('DoS does not accept --fliter or --goal')
    selections, exclusions = {}, []
    for suite_name in suites:
        suite = get_suite(SUITE_VERSION, suite_name)
        users, targets = select_tasks(frozen_tasks, suite_name, list(suite.user_tasks),
                                     list(suite.injection_tasks), run_attack, False, task_scope=task_scope)
        excluded = set(excluded_ids(fliter, suite_name)) if fliter else set()
        for target in targets:
            if target in excluded:
                exclusions.append(dict(suite=suite_name, injection_task_id=target, reason='fliter',
                                       status='excluded', removed_pairs=len(users)*len(attack_names)))
        selections[suite_name] = dict(user_task_ids=users, injection_task_ids=[i for i in targets if i not in excluded])
    selection_report = dict(targets_before=sum(len(v['injection_task_ids']) for v in selections.values())+len(exclusions),
        fliter_excluded=exclusions, goal_checks=[], targets_retained=sum(len(v['injection_task_ids']) for v in selections.values()),
        removed_pairs=sum(e['removed_pairs'] for e in exclusions), goal_enabled=bool(goal),
        goal_pipeline='baseline' if origin else prompt_profile)
    context = {'execution_plan': execution_plan(task_scope, suites, attack_names, None)}
    run_records = []
    print(f"本次攻击 ({len(attack_names) if run_attack else 0}): {', '.join(attack_names) if run_attack else '无（clean）'}", flush=True)
    print(f"本次场景 ({len(suites)}): {', '.join(suites)}", flush=True)

    resources = {'task_manifest': frozen_tasks, 'selections': selections,
                 'selection_options': {'fliter_sha256': filter_digest(fliter) if fliter else None, 'goal': bool(goal)}}
    def group_options(attack_name):
        return dict(
                model_id=model_id, sec_model_id=sec_model_id, suites=suites, run_attack=run_attack, origin=origin, defense=defense,
                api_key=api_key, base_url=base_url, provider=provider, api_key_env=api_key_env,
                sec_api_key=sec_api_key, sec_base_url=sec_base_url, sec_provider=sec_provider,
                sec_api_key_env=sec_api_key_env, config_path=config_path, force_rerun=force_rerun,
                progress=progress,
                run_name=run_name, trace_level=trace_level, tool_metadata_path=tool_metadata_path,
                results_dir=logdir, attack_name=attack_name,
                use_security_checker=use_security_checker,
                audit_retries=audit_retries, completion_prompt=completion_prompt,
                task_manifest_path=task_manifest_path,
                audit_router_mode=audit_router_mode,audit_router_artifact=audit_router_artifact, audit_router_threshold=audit_router_threshold,
                planning_tool_view=planning_tool_view and not origin and use_sandbox,
                delegated_tasks=delegated_tasks and not origin and use_sandbox,
                prompt_profile=prompt_profile,
                l1_projection_mode='off' if origin or not (use_sandbox or use_security_checker) else l1_projection_mode,
                task_scope=task_scope, use_sandbox=use_sandbox,
                run_base=resume.base if isinstance(resume, ReusePlan) else None,

        )
    descriptor = _describe_pipeline(model_id, sec_model_id, origin=origin, defense=defense,
                                   **{k:v for k,v in group_options(attack_names[0]).items()
                                      if k not in {'model_id','sec_model_id','origin','defense'}})
    base = resume.base if resume is not None else resolve_run_path(logdir, backend.id,
        descriptor.dscg_model_config['model_id'], run_name, default_name=descriptor.name)
    prepared = RunBindings(base, reuse=reuse)
    resources['descriptor'] = descriptor
    try:
        for attack_name in attack_names:
            _run_single_attack(**group_options(attack_name), report_context=context,
                               reuse_plan=prepared, prepare_only=True, resource_cache=resources)
    except RunConfigurationError as exc:
        print(f'❌ 配置绑定冲突: {exc}', flush=True)
        return 1
    base = context['base_output_dir']
    print('缓存策略: ' + ('显式续跑' if reuse else '强制重跑' if force_rerun else '默认复用原生缓存'), flush=True)
    print(f"模型: {context['model_id']}；后端: {backend.label}；审计: {context.get('security_model_id') or '无'}", flush=True)
    selection, _ = resources.get('metadata', (None, None))
    if selection:
        print(f"工具分类目录: {selection['path']}；来源: {selection['source']}", flush=True)
        if selection.get('warning'):
            print(f"工具分类目录提示: {selection['warning']}", flush=True)
    with run_lock(base):
        try:
            if not set(base.glob('*/*/run_manifest.json')) <= prepared.checked.keys():
                raise RunConfigurationError('existing task bindings fall outside the complete requested plan')
            prepared.commit()
        except RunConfigurationError as exc:
            print(f'❌ 配置绑定冲突: {exc}', flush=True)
            return 1
        if fliter is not None:
            filter_copy = base / 'fliter.json'
            if not filter_copy.exists():
                filter_copy.write_text(json.dumps(fliter, ensure_ascii=False, indent=2)+'\n')
        approved = prepared
        if goal:
            def goal_pipeline(suite_name):
                pipeline, main_tracker, sec_tracker = _configured_pipeline(group_options(attack_names[0]), resources.get('metadata', (None,None))[1])
                pipeline._goal_trackers = tuple(t for t in (main_tracker, sec_tracker) if t is not None)
                return pipeline
            try:
                checks = run_goal_checks(base, selections, goal_pipeline, reuse=reuse, progress=progress)
            except KeyboardInterrupt:
                print('GOAL已中断并保存；使用原参数加 --reuse 续跑。', flush=True)
                return 130
            for check in checks:
                check['removed_pairs'] = (len(selections[check['suite']]['user_task_ids'])*len(attack_names)
                                          if check['status'] != 'passed' else 0)
            selection_report['goal_checks'] = checks
            passed = {(c['suite'], c['injection_task_id']) for c in checks if c['status']=='passed'}
            resources['goal_retained'] = {suite:[i for i in ids['injection_task_ids'] if (suite,i) in passed]
                                          for suite,ids in selections.items()}
            # GOAL can remove a target whose native attack payload is unsupported.
            # Compatibility belongs to the actual scored subset, not excluded IDs.
            resources['compatibility'] = {}
            for attack_name in attack_names:
                for suite_name in suites:
                    try:
                        issue = check_attack_compatibility(get_suite(SUITE_VERSION, suite_name), attack_name,
                            selections[suite_name]['user_task_ids'], resources['goal_retained'][suite_name])
                        if issue is not None:
                            resources['compatibility'][(attack_name,suite_name)] = {'status':'unsupported', **issue}
                    except Exception as exc:
                        resources['compatibility'][(attack_name,suite_name)] = {
                            'status':'error', 'error_type':type(exc).__name__,
                            'execution_error':execution_error_diagnostics(exc)}
            selection_report['targets_retained'] = len(passed)
            selection_report['removed_pairs'] += sum(len(selections[c['suite']]['user_task_ids'])*len(attack_names)
                                                     for c in checks if c['status']!='passed')

        jobs = [{'attack': name, 'suite': suite,
                 'options': group_options(name), 'bindings': approved,
                 'execution_plan': context['execution_plan'],
                 'resources': resources,
                 'compatibility': resources.get('compatibility', {}).get((name, suite))}
                for name in attack_names for suite in suites]
        invocation = uuid4().hex
        execution_dir = base / 'execution' / invocation
        execution_dir.mkdir(parents=True, exist_ok=True)
        runnable_attacks = len({j['attack'] for j in jobs if j['compatibility'] is None})
        parallel = runnable_attacks > 1
        execution = {'mode': 'parallel_attacks' if parallel else 'serial', 'unit': 'attack',
                     'attack_processes': runnable_attacks if parallel else 0,
                     'planned_groups': len(jobs), 'invocation_id': invocation}
        if 'cohort_validation' in context:
            execution['cohort_validation'] = context['cohort_validation']
        print(f"结果目录: {base}；{len(attack_names)} 个attack，{len(jobs)} 个场景组；"
              + ("attack并行，内部顺序执行。" if parallel else "顺序执行。"), flush=True)
        started = monotonic()
        try:
            group_results = [None] * len(jobs)
            with AttackOutput(jobs, progress) as output:
                with closing(iter_attack_results(jobs, on_event=output.event)) as results:
                    for index, result in results:
                        group_results[index] = result
                        output.result(index, result)
        except KeyboardInterrupt:
            execution.update(status='interrupted', wall_seconds=monotonic() - started, workers=output.workers,
                             groups=[{'attack': j['attack'], 'suite': j['suite'],
                                      **({k: v for k, v in r.items() if k != 'result'} if r is not None else {'status': 'interrupted'})}
                                     for j, r in zip(jobs, group_results)])
            (execution_dir / 'execution.json').write_text(json.dumps(execution, indent=2) + '\n')
            # Derive partial reports from completed groups and already committed
            # task bindings. No model calls, new scores or cache rewrites.
            completed_reports = [report for result in group_results if result is not None and result['status'] == 'completed'
                                 for report in result['result']['suite_reports']]
            try:
                from experiments.common.routing_reports import write_routing_summary
                routing_summary = write_routing_summary(base, refresh=True, check_running=False)
                write_run_overview(base, attack_names, suites,
                    [{'attack': name, 'status': 'error', 'error_type': 'KeyboardInterrupt'} for name in attack_names],
                    completed_reports, model_id=context.get('model_id', model_id), task_scope=task_scope,
                    routing_summary=routing_summary, selection_report=selection_report)
            except (OSError, ValueError, KeyError, TypeError):
                print('部分汇总未完成；原始结果与执行状态已保留，可离线重新汇总。', flush=True)
            print('已中断；保留原参数、运行名并加 --reuse 续跑。', flush=True)
            return 130
        execution.update(status='error' if any(r['status'] == 'error' or r.get('task_errors') for r in group_results) else
                                'unsupported' if all(r['status'] == 'unsupported' for r in group_results) else 'completed',
                         wall_seconds=monotonic() - started, workers=output.workers,
                         groups=[{'attack': j['attack'], 'suite': j['suite'],
                                  **{k: v for k, v in r.items() if k != 'result'}}
                                 for j, r in zip(jobs, group_results)])
        (execution_dir / 'execution.json').write_text(json.dumps(execution, indent=2) + '\n')
        for name in attack_names:
            entries = [(j, r) for j, r in zip(jobs, group_results) if j['attack'] == name]
            for job, result in entries:
                if result['status'] == 'completed':
                    context.setdefault('suite_reports', []).extend(result['result']['suite_reports'])
            # Keep errors before unsupported groups in manifests and failure indexes.
            for status in ('error', 'unsupported'):
                for job, result in entries:
                    if result['status'] == status:
                        run_records.append({'attack': name, 'status': status,
                                            'failed_suite': job['suite'], **result})
            if any(r['status'] == 'completed' for _, r in entries):
                run_records.append({'attack': name, 'status': 'completed', 'output_dir': str(base / name)})

        from experiments.common.routing_reports import write_routing_summary
        routing_summary = write_routing_summary(base, refresh=True, check_running=False)
        overview_path, failures_path = write_run_overview(
            base, attack_names, suites, run_records, context.get("suite_reports", []),
            model_id=context.get("model_id", model_id), task_scope=task_scope, routing_summary=routing_summary, selection_report=selection_report,
        )
        print(f"📝 紧凑摘要: {overview_path}")
        print(f"🔎 失败片段: {failures_path}")
        print(f"📋 运行配置: {base / 'run_manifest.json'}")
        return 1 if (any(c['status']=='error' for c in selection_report['goal_checks']) or
                     not any(r['status'] == 'completed' for r in group_results) or
                     any(record["status"] == "error" for record in run_records) or
                     any(report.get("task_errors") or report.get("goal_preflight_errors") for report in context.get("suite_reports", []))) else 0


def _execute_group(job):
    context = {'execution_plan': job['execution_plan']}
    _run_single_attack(**job['options'], only_suite=job['suite'], group_mode=True,
                       reuse_plan=job['bindings'], report_context=context, resource_cache=job.get('resources'))
    return {'suite_reports': context.get('suite_reports', [])}


def _run_single_attack(
    model_id: str | None = None,
    sec_model_id: str | None = None,
    suites: list[str] | None = None,
    run_attack: bool = True,
    origin = False,
    defense: str = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
    api_key_env: str | None = None,
    sec_api_key: str | None = None,
    sec_base_url: str | None = None,
    sec_provider: str | None = None,
    sec_api_key_env: str | None = None,
    config_path: str | Path | None = None,
    force_rerun: bool = False,
    progress: bool = False,
    run_name: str | None = None,
    trace_level: str = "summary",
    tool_metadata_path: str | Path | None = None,
    use_security_checker: bool = True,
    audit_retries: int = 0,
    completion_prompt: bool = False,
    task_manifest_path: str | Path | None = None,
    results_dir: str | Path | None = None,
    attack_name: str = "important_instructions",
    report_context: dict | None = None,
    audit_router_mode: str = "off",
    audit_router_artifact: str | Path | None = None,
    audit_router_threshold: float = DEFAULT_THRESHOLD,
    planning_tool_view: bool = True,
    delegated_tasks: bool = True,
    l1_projection_mode: str = 'projected',
    prompt_profile: str | None = None,
    task_scope: str = 'partial',
    use_sandbox: bool = True,
    cohort_sha256: str | None = None,
    reuse_plan=None,
    prepare_only=False,
    only_suite=None,
    group_mode=False,
    resource_cache=None,
    run_base=None,
):
    """
        model_id: 执行的llm的id
        sec_model_id: 审计的模型id，可以使用小模型替代
        suites: 测试的场景
        run_attack: 是否进行攻击，测试安全性，默认true
        origin: 是否只使用原始模型
        defense: agentdojo自带的防御机制包括："tool_filter", "transformers_pi_detector", "spotlighting_with_delimiting"等
    """



    backend = get_backend()
    suites = list(backend.suites if suites is None else suites)
    if not suites or len(set(suites)) != len(suites) or not set(suites) <= set(backend.suites):
        raise ValueError('invalid suite selection for current backend')
    prompt_profile = _validate_prompt_profile(origin, use_sandbox, use_security_checker, prompt_profile)
    audit_router_threshold = validate_router_options(audit_router_threshold, audit_router_artifact)
    _validate_router_controls(origin,use_security_checker,audit_router_mode,use_sandbox)
    validate_controls(origin=origin, use_security_checker=use_security_checker,
                      audit_retries=audit_retries, completion_prompt=completion_prompt)
    frozen_tasks = (resource_cache['task_manifest'] if resource_cache is not None and 'task_manifest' in resource_cache
                    else load_task_manifest(task_manifest_path))
    selection_seed = None if task_scope in {'full', 'screened'} else frozen_tasks.get("seed", 7) if frozen_tasks else 7
    if resource_cache is not None and 'metadata' in resource_cache:
        metadata_selection, tool_metadata = resource_cache['metadata']
    else:
        metadata_selection = None
        tool_metadata = None
        if not origin:
            selection = resolve_tool_metadata(tool_metadata_path, backend=backend)
            metadata_selection = selection.public_dict()
            if not prepare_only:
                print(f"工具分类目录: {metadata_selection['path']}；来源: {metadata_selection['source']}；基准: {backend.label}", flush=True)
            if not prepare_only and metadata_selection.get('warning'):
                print(f"工具分类目录提示: {metadata_selection['warning']}", flush=True)
            validate_benchmark_tool_metadata(selection.path)
            tool_metadata = load_tool_metadata(selection.path)
        if resource_cache is not None:
            resource_cache['metadata'] = (metadata_selection, tool_metadata)
    active_defense = defense if origin else "dscg"
    logdir = Path(results_dir) if results_dir is not None else BENCHMARK_RESULTS_DIR if task_scope in {'full', 'screened'} else RESULTS_DIR / "partial_benchmark"
    logdir.mkdir(parents=True, exist_ok=True)
    output_dir: Path | None = None

    if not prepare_only and not group_mode:
        print(f"开始实验 - 模型: {model_id or '本地/环境配置'}, 攻击: {attack_name if run_attack else '无'}, 防御: {active_defense or '无（baseline）'}")

    for suite_name in ([only_suite] if only_suite is not None else suites):
        if report_context is not None:
            report_context["active_suite"] = suite_name

        if prepare_only:
            if resource_cache is None:
                resource_cache = {}
            if 'descriptor' not in resource_cache:
                resource_cache['descriptor'] = _describe_pipeline(
                    model_id, sec_model_id, origin=origin, defense=defense,
                    api_key=api_key, base_url=base_url, provider=provider, api_key_env=api_key_env,
                    sec_api_key=sec_api_key, sec_base_url=sec_base_url, sec_provider=sec_provider,
                    sec_api_key_env=sec_api_key_env, config_path=config_path,
                    use_security_checker=use_security_checker, use_sandbox=use_sandbox,
                    l1_projection_mode=l1_projection_mode, planning_tool_view=planning_tool_view,
                    delegated_tasks=delegated_tasks, audit_router_mode=audit_router_mode,
                    audit_router_artifact=audit_router_artifact, audit_router_threshold=audit_router_threshold, audit_retries=audit_retries,
                    completion_prompt=completion_prompt, prompt_profile=prompt_profile)
            pipeline = copy(resource_cache['descriptor'])
        else:
            pipeline, main_tracker, sec_tracker = _configured_pipeline(locals(), tool_metadata)


        main_model_config = getattr(pipeline, "dscg_model_config", {})
        sec_model_config = getattr(pipeline, "dscg_security_model_config", {})
        resolved_model_id = main_model_config.get("model_id", model_id)
        resolved_sec_model_id = None if origin or not use_security_checker else sec_model_config.get("model_id", sec_model_id)
        original_name = pipeline.name
        _apply_run_name(pipeline, resolved_model_id, run_name)
        base_output_dir = Path(run_base) if run_base is not None else resolve_run_path(
            logdir, backend.id, resolved_model_id, run_name, default_name=original_name)
        result_dir_name = base_output_dir.name
        pipeline.name = result_dir_name
        def bind(path, expected):
            if reuse_plan is not None:
                return reuse_plan.check(path, expected) if prepare_only else reuse_plan.guard(path, expected)
            guard_run(path, expected)
            return expected
        if task_scope in {'partial', 'partial_screened', 'full'}:
            # Bind the entire selection, including disjoint subsets, before any
            # scored execution or report rewrite under this run name.
            bind(base_output_dir / 'suite_manifest.json', {
                'schema_version': 'dscg.full-suites.v2' if task_scope == 'full' else 'dscg.partial-suites.v2',
                'benchmark': benchmark_identity(),
                'suites': suites,
            })
        if cohort_sha256 is None and report_context is not None:
            bind(base_output_dir / 'benchmark_plan.json', report_context['execution_plan'])
        attack_component = _safe_result_component(attack_name if run_attack else "none", "attack")
        output_dir = base_output_dir / attack_component
        if report_context is not None:
            report_context.update(base_output_dir=base_output_dir,
                                  pipeline_name=result_dir_name, model_id=resolved_model_id,
                                  security_model_id=resolved_sec_model_id)


        
        # 加载套件和攻击
        suite = get_suite("v1.2", suite_name)
        user_task_ids = list(suite.user_tasks.keys())
        injection_task_ids = list(suite.injection_tasks.keys())
        
        attack = None if not run_attack or prepare_only else attacks.load_attack(attack_name, suite, pipeline)
        is_dos_attack = bool(run_attack and ATTACKS[attack_name].is_dos_attack)

        # Share the same scope/IDs across baseline and DSCG; only partial is capped.
        selected_users, selected_injections = select_tasks(
            frozen_tasks, suite_name, user_task_ids, injection_task_ids, run_attack, is_dos_attack,
            task_scope=task_scope,
        )
        if resource_cache and 'selections' in resource_cache:
            selected_users = resource_cache['selections'][suite_name]['user_task_ids']
            if run_attack and not is_dos_attack:
                selected_injections = resource_cache['selections'][suite_name]['injection_task_ids']
        run_binding = {
            'task_layout': LAYOUT,
            'selection_options': resource_cache.get('selection_options', {}) if resource_cache else {},
            "schema_version": f"dscg.{task_scope}-run.v2",
            "outcome_projection": OUTCOME_PROJECTION_VERSION,
            "benchmark": benchmark_identity(),
            "task_scope": task_scope,
            "task_selection": {"users": selected_users, "injections": selected_injections,
                               "suite_version": "v1.2", "seed": selection_seed},
            "attack": attack_name if run_attack else None,
            "main_model": main_model_config, "security_model": sec_model_config,
            "profile": "baseline" if origin else "full" if use_security_checker else "no-checker",
            "agentdojo_defense": defense if origin else None,
            "audit_retries": audit_retries, "completion_prompt": completion_prompt,
            "trace_level": None if origin else trace_level,
            "tool_metadata": tool_metadata, "tool_metadata_selection": metadata_selection, "source": source_revision(),
            "defense_version": None if origin else framework_version_for_profile(prompt_profile),
            "input_isolation": bool(not origin and (use_sandbox or use_security_checker)),
            'l1_projection_mode': 'off' if origin else l1_projection_mode,
            'l1_projection_profile_sha256': None if origin else L1_PROFILE_SHA256,
            "authorization_precheck": bool(not origin and use_sandbox),
            'planning_tool_view': bool(planning_tool_view and not origin),
            'delegated_tasks': bool(delegated_tasks and not origin),
            "audit_router_mode": audit_router_mode,
            "audit_router_artifact_sha256": getattr(pipeline,"dscg_optimization_config",{}).get("audit_router_artifact_sha256"),
            "audit_router_config_sha256": getattr(pipeline,"dscg_optimization_config",{}).get("audit_router_config_sha256"),
            **({'task_failure_policy': pipeline.dscg_optimization_config['task_failure_policy']}
               if getattr(pipeline,'dscg_optimization_config',{}).get('task_failure_policy') else {}),
        }
        if audit_router_mode != 'off':
            run_binding.update(audit_router_threshold=audit_router_threshold,
                               audit_router_policy_version=ROUTER_POLICY_VERSION)
        if not origin:
            run_binding.update(profile_binding(prompt_profile))
        if cohort_sha256 is not None:
            run_binding['cohort_sha256'] = cohort_sha256
        recorded_binding = bind(output_dir / suite_name / "run_manifest.json", run_binding)

        if not prepare_only and resource_cache and 'goal_retained' in resource_cache:
            selected_injections = resource_cache['goal_retained'][suite_name]
        planned_task_count = (
            len(selected_users) * len(selected_injections)
            if run_attack
            else len(selected_users)
        )
        if prepare_only:
            if resource_cache is not None:
                compatibility = resource_cache.setdefault('compatibility', {})
                try:
                    issue = check_attack_compatibility(
                        suite, attack_name if run_attack and not is_dos_attack else 'none',
                        selected_users, selected_injections)
                    if issue is not None:
                        compatibility[(attack_name, suite_name)] = {'status': 'unsupported', **issue}
                except Exception as exc:
                    compatibility[(attack_name, suite_name)] = {
                        'status': 'error', 'error_type': type(exc).__name__,
                        'execution_error': execution_error_diagnostics(exc)}
            continue
        if not progress:
            print(f"用户任务={len(selected_users)}；注入目标={len(selected_injections)}；计划组合={planned_task_count}", flush=True)
        if report_context is not None:
            report_context['pipeline_name'] = result_dir_name
        pipeline.name = attack_component
        try:
            ensure_native_cache_model_ready()
            with logging.OutputLogger(str(base_output_dir)):
                if progress:
                    with GroupProgress(f"{attack_name if run_attack else 'none'}/{suite_name}",
                                       goal_total=0,
                                       score_total=planned_task_count) as display:
                        results = run_suite_with_progress(
                            pipeline, suite, attack, base_output_dir, force_rerun,
                            user_tasks=selected_users, injection_tasks=selected_injections,
                            benchmark_version=SUITE_VERSION, on_step=display.advance)
                else:
                    results = run_suite_with_progress(
                        pipeline, suite, attack, base_output_dir, force_rerun,
                        user_tasks=selected_users, injection_tasks=selected_injections,
                        benchmark_version=SUITE_VERSION)
        finally:
            pipeline.name = result_dir_name

        utility_results = results["utility_results"]
        security_results = results.get("security_results", {})
        if not progress:
            print(f"实际完成评测任务数量: {len(utility_results)}")

        suite_output_dir = output_dir / suite_name
        suite_output_dir.mkdir(parents=True, exist_ok=True)
        csv_file_path = suite_output_dir / "detailed_results.csv"
        summary_file_path = suite_output_dir / "summary.json"

        outcomes = project_outcomes(utility_results, security_results, suite_output_dir,
                                    attack_name if run_attack else "none", run_attack=run_attack,
                                    task_errors=results.get("task_errors", []))
        structured_records = [{
            "suite_name": suite_name,
            "model_id": resolved_model_id,
            "attack_type": attack_name if run_attack else "None",
            "user_task_id": task_key[0],
            "injection_task_id": task_key[1] if len(task_key) > 1 else "None",
            **outcomes[task_key],
        } for task_key in utility_results]

        valid_utility_results = [r['utility_success'] for r in outcomes.values() if isinstance(r['utility_success'], bool)]
        utility_score = sum(valid_utility_results) / len(valid_utility_results) if valid_utility_results else None
        valid_security_results = [r['attack_success'] for r in outcomes.values() if isinstance(r['attack_success'], bool)]
        security_score = (
            sum(valid_security_results) / len(valid_security_results)
            if run_attack and valid_security_results else None
        )
        defense_score = 1.0 - security_score if security_score is not None else None


        prompt_tokens = main_tracker.total_prompt_tokens 
        completion_tokens = main_tracker.total_completion_tokens
        total_tokens = main_tracker.get_total_tokens()
        if sec_tracker:
            sec_prompt_tokens = sec_tracker.total_prompt_tokens 
            sec_completion_tokens = sec_tracker.total_completion_tokens
            sec_total_tokens = sec_tracker.get_total_tokens() 

        summary_data = {
            "schema_version": "dscg.benchmark-summary.v2", "benchmark": benchmark_identity(),
            "task_scope": task_scope,
            "suites": suites,
            "suite_scope": "all_registered" if set(suites) == set(backend.suites) else "selected",
            "suite_name": suite_name,
            "pipeline_name": f"{result_dir_name}/{attack_component}",
            "model_id": resolved_model_id,
            "defense": active_defense,
            "tool_metadata_selection": metadata_selection,
            "run_manifest": "../../run_manifest.json",
            "audit_router": _router_trace_summary(suite_output_dir,utility_results,attack_name if run_attack else "none",run_attack)
                            if audit_router_mode != "off" else None,
            "api_accounting": {"main": main_tracker.snapshot() if hasattr(main_tracker, "snapshot") else {},
                               "security": sec_tracker.snapshot() if sec_tracker and hasattr(sec_tracker, "snapshot") else {}},
            "attack_kind": "dos" if is_dos_attack else "targeted" if run_attack else "none",
            "security_definition": "not utility (AgentDojo DoS)" if is_dos_attack else "injection task predicate" if run_attack else None,
            "task_selection": {
                "suite_version": "v1.2",
                "seed": selection_seed,
                "user_task_ids": selected_users,
                "injection_task_ids": selected_injections,
                "attack": attack_name if run_attack else None,
            },
            "metrics": {
                "utility_rate": utility_score,
                "attack_success_rate": security_score,
                "defense_success_rate": defense_score
            },
            "task_counts": {
                "total_tasks": len(utility_results),
                "planned_tasks": planned_task_count,
                "utility_passed": sum(valid_utility_results),
                "utility_valid": len(valid_utility_results),
                "execution_errors": sum(r["execution_error"] for r in outcomes.values()),
                "framework_failures": sum(r.get('framework_termination',{}).get('kind') == 'framework_failure' for r in outcomes.values()),
                "attacked_tasks": len(valid_security_results) if run_attack else 0,
                "security_missing": sum(
                    not isinstance(r["attack_success"], bool) for r in outcomes.values()
                ) if run_attack else 0,
                "selected_user_tasks": len(selected_users),
                "selected_injection_tasks": len(selected_injections),
                "available_user_tasks": len(user_task_ids),
                "available_injection_tasks": len(injection_task_ids),
            },
            "overhead": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
        }
        task_errors = results.get('task_errors', [])
        if task_errors:
            summary_data['task_error_diagnostics'] = task_errors
            summary_data['task_counts']['goal_preflight_errors'] = sum(e['stage'] == 'goal_preflight' for e in task_errors)
        if cohort_sha256 is not None:
            summary_data['cohort_sha256'] = cohort_sha256

        if sec_tracker:
            summary_data["sec_overhead"] = {
                "prompt_tokens": sec_prompt_tokens,
                "completion_tokens": sec_completion_tokens,
                "total_tokens": sec_total_tokens
            }

        preserve_cached_cost(summary_data, summary_file_path, force_rerun)

        if structured_records:
            with open(csv_file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=structured_records[0].keys())
                writer.writeheader()
                writer.writerows(structured_records)

        with open(summary_file_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=4, ensure_ascii=False)

        if report_context is not None:
            report_context.setdefault("suite_reports", []).append(collect_suite_report(
                base_output_dir, suite_output_dir, summary_data, structured_records, suite,
            ))


        if not progress:
            print(f"✅ [{suite_name}] 测试完成！")
            print(f"📊 数据表格(用于画图): {csv_file_path}")
            print(f"📈 得分汇总: {summary_file_path}\n")

    return output_dir





def cli(argv: list[str] | None = None, *, task_scope: str = 'partial', entrypoint=None, require_cohort=False) -> int:
    if task_scope not in {'partial', 'full'}:
        raise ValueError('task scope must be partial or full')
    full = task_scope == 'full'
    parser = argparse.ArgumentParser(
        description="运行 DSCG 的当前基准全量评测（所选场景全部用户/注入任务）。" if full else "运行 DSCG 的当前基准小批量回归评测，可指定场景。"
    )
    parser.add_argument('--suites', nargs='+', metavar='SUITE', default=None,
                        help='选择当前环境支持的场景；默认全部场景，full保留所选场景全部任务。')
    parser.add_argument(
        "--attack",
        nargs="+",
        action="extend",
        choices=("typical", "all", *resolve_attack_names("all")),
        metavar="ATTACK",
        help="默认 typical（3 种目标型攻击，不含injecagent）；reuse未指定时沿用原攻击名单。",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="运行无防御原生基线；与默认 DSCG 使用相同任务范围和注入攻击。",
    )
    parser.add_argument('--progress', action='store_true',
                        help='按攻击/场景显示进度条；分别计数原生GOAL预检与计分任务。')
    cache_policy = parser.add_mutually_exclusive_group()
    cache_policy.add_argument('--reuse', action='store_true',
        help='按原name显式续跑，保留原名单与原生缓存规则；覆盖DSCG_FORCE_RERUN，不自动重试错误。')
    cache_policy.add_argument(
        "--force-rerun",
        action="store_true",
        help="重新执行任务，不复用已有结果；也可设置 DSCG_FORCE_RERUN=1。",
    )
    parser.add_argument(
        "--name",
        dest="run_name",
        metavar="NAME",
        help="本次运行名称；结果保存于 --results-dir 指定目录下的 <backend>/<model_id>_<NAME>/。",
    )
    parser.add_argument(
        "--trace-level",
        choices=("summary", "standard", "full"),
        default=os.getenv("DSCG_TRACE_LEVEL", "summary"),
        help="独立 DSCG 诊断文件详细度；默认 summary，任务 JSON 始终精简。",
    )
    parser.add_argument(
        "--include-extra-info",
        action="store_true",
        help="兼容快捷开关，等同于 --trace-level full，将详细审计/动作记录写入独立诊断文件。",
    )
    parser.add_argument(
        "--tool-metadata",
        dest="tool_metadata_path",
        metavar="PATH",
        default=os.getenv("DSCG_TOOL_METADATA"),
        help="显式工具风险元数据 TOML；默认本地覆盖或当前基准内置分类，缺失/非法工具按 critical 处理。",
    )
    parser.add_argument(
        "--model-config",
        dest="config_path",
        metavar="PATH",
        help="模型配置 TOML；缺省使用 config/models.local.toml。",
    )
    parser.add_argument(
        "--results-dir",
        metavar="DIR",
        help="结果根目录；缺省使用 results/benchmarks/。" if full else "结果根目录；缺省使用 results/partial_benchmark/。",
    )
    parser.add_argument("--no-checker", action="store_true", help="P0 消融：保留授权/monitor/ticket，关闭语义审计。")
    parser.add_argument('--no-tool-view', action='store_true', help='L2 对照：规划器展示完整工具目录，保留执行权限检查。')
    parser.add_argument('--no-delegated-tasks', action='store_true', help='关闭显式任务文件展开，用于原任务编译对照。')
    parser.add_argument('--prompt-profile', choices=PROMPT_PROFILES, default=None,
                        help=f'默认{resolve_profile(None)}；baseline默认legacy；显式legacy保留单次授权对照')
    parser.add_argument('--l1-projection-mode', choices=('off','shadow','projected'), default='off',
                        help='L1有限交易投影，CLI默认off保留来源封装；shadow只观察，projected启用有限投影。')
    # None selects the profile default below: DSCG shadow, baseline/NoChecker off.
    parser.add_argument("--audit-router-mode", choices=("off", "shadow", "selective"), default=None,
                        help="L3纯算法路由；DSCG CLI默认shadow，baseline/NoChecker默认off；可显式选择。")
    parser.add_argument("--audit-router-artifact", help="已停用；请改用 --audit-router-threshold。")
    parser.add_argument("--audit-router-threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="诊断阈值 [0,1]，默认0.70；read-purpose-v2按读取规则免审，不按分数阈值。")
    parser.add_argument("--audit-retries", type=int, choices=(0, 1), default=0, help="语义 abstain 有界重审次数；默认 0。")
    parser.add_argument("--completion-prompt", action="store_true", help="启用通用任务完成提示；默认关闭。")
    parser.add_argument("--clean", action="store_true", help="用相同用户任务运行无攻击效用控制。")
    parser.add_argument("--task-manifest", dest="task_manifest_path", help="读取冻结 v1.2 全量任务清单；拒绝缩小实际执行集合。" if full else "读取冻结 v1.2 任务 ID 清单。")
    parser.add_argument("--write-task-manifest", metavar="PATH", help="离线导出当前任务 ID 清单并退出，不调用模型。")
    parser.add_argument('--fliter', dest='fliter_path', help='Minimal injection exclusion list (fliter.json).')
    parser.add_argument('--goal', action='store_true', help='Precheck remaining GOALs using the current measured pipeline.')
    args = parser.parse_args(argv)
    if args.audit_router_mode is None:
        args.audit_router_mode = 'off' if args.baseline or args.no_checker else 'shadow'
    try:
        validate_router_options(args.audit_router_threshold, args.audit_router_artifact)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        active_suites = get_suites()
    except ValueError as exc:
        print(f'测量配置或证据校验失败: {exc}')
        return 1
    selected_suites = args.suites if args.reuse else args.suites or list(active_suites)
    if selected_suites is not None and not set(selected_suites) <= set(active_suites):
        parser.error(f'--suites must select from {", ".join(active_suites)}')
    if selected_suites is not None and len(set(selected_suites)) != len(selected_suites):
        parser.error('--suites cannot contain duplicate names')
    if args.reuse and (not args.run_name or args.write_task_manifest):
        parser.error('--reuse requires --name and cannot combine with --write-task-manifest')
    if require_cohort:
        parser.error('the old screened/cohort entry point is retired; use --fliter and optionally --goal')
    if args.clean and (args.fliter_path is not None or args.goal):
        parser.error('--clean does not accept --fliter or --goal')
    try:
        validate_controls(origin=args.baseline, use_security_checker=not args.no_checker,
                          audit_retries=args.audit_retries, completion_prompt=args.completion_prompt)
        args.prompt_profile = _validate_prompt_profile(args.baseline, True, not args.no_checker, args.prompt_profile)
        _validate_router_controls(args.baseline,not args.no_checker,args.audit_router_mode)
        if args.write_task_manifest:
            path = Path(args.write_task_manifest)
            if path.exists(): parser.error("task manifest already exists; preserve old evidence")
            manifest = make_task_manifest(task_scope)
            manifest['suites'] = {name: manifest['suites'][name] for name in selected_suites}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            print(f"任务清单: {path}")
            return 0
    except ValueError as exc:
        parser.error(str(exc))
    selected_attacks = args.attack if args.reuse else args.attack or ["typical"]
    try:
        if selected_attacks is not None:
            resolve_attack_names(selected_attacks)
    except ValueError as exc:
        parser.error(str(exc))

    try:
        execution = entrypoint or main
        dispatch_options = {} if entrypoint is not None else {'task_scope': task_scope}
        dispatch_options.update(fliter_path=args.fliter_path, goal=args.goal)
        status = execution(
            model_id=os.getenv("DSCG_MAIN_MODEL_ID"),
            sec_model_id=os.getenv("DSCG_SEC_MODEL_ID"),
            provider=os.getenv("DSCG_MAIN_PROVIDER"),
            sec_provider=os.getenv("DSCG_SEC_PROVIDER"),
            suites=selected_suites,
            run_attack=not args.clean,
            origin=args.baseline,
            defense=None,
            force_rerun=False if args.reuse else args.force_rerun or os.getenv("DSCG_FORCE_RERUN", "0").lower() in {"1", "true", "yes"},
            reuse=args.reuse,
            progress=args.progress,
            run_name=args.run_name,
            trace_level="full" if args.include_extra_info else args.trace_level,
            tool_metadata_path=args.tool_metadata_path,
            config_path=args.config_path,
            results_dir=args.results_dir if args.results_dir is not None else BENCHMARK_RESULTS_DIR if full else None,
            attack=selected_attacks,
            use_security_checker=not args.no_checker, audit_retries=args.audit_retries,
            completion_prompt=args.completion_prompt, task_manifest_path=args.task_manifest_path,
            audit_router_mode=args.audit_router_mode,audit_router_artifact=args.audit_router_artifact, audit_router_threshold=args.audit_router_threshold,
            planning_tool_view=not args.no_tool_view and not args.baseline,
            delegated_tasks=not args.no_delegated_tasks and not args.baseline,
            prompt_profile=args.prompt_profile,
            l1_projection_mode='off' if args.baseline else args.l1_projection_mode,
            **dispatch_options,
        )
    except ModelConfigurationError as exc:
        print(f"模型配置错误: {exc}")
        print("请设置 DSCG_MAIN_* 环境变量，或复制 config/models.example.toml 为 config/models.local.toml 后填写。")
        return 1
    except ToolMetadataError as exc:
        print(f"工具元数据错误: {exc}", flush=True)
        return 1
    except ValueError as exc:
        print(f"测量配置或证据校验失败: {exc}", flush=True)
        return 1
    return status if status in (1, 130) else 0


if __name__ == "__main__":
    raise SystemExit(cli())
