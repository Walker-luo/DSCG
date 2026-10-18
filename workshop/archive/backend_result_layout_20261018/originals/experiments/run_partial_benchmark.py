import argparse
import os
import re
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
from dscg.audit_router import summarize_events
from dscg.input_isolation import FRAMEWORK_VERSION
from dscg.l1_projection import MODES as L1_PROJECTION_MODES, PROFILE_SHA256 as L1_PROFILE_SHA256
from dscg.pipelines.baseline import make_openai_compatible_pipeline
from dscg.pipelines.defended import make_defended_pipeline, router_configuration_hash, defended_pipeline_name
from dscg.audit_router import LocalAuditRouter
from dscg.tool_metadata import ToolMetadataError, load_tool_metadata, validate_benchmark_tool_metadata, resolve_tool_metadata
from experiments.diagnostics.harness_audit import rank_ids, security_result_fields
from experiments.common.benchmark_outcomes import project_outcomes
from experiments.common.partial_reporting import collect_suite_report, write_run_overview
from experiments.common.partial_controls import (validate_controls, make_task_manifest, load_task_manifest,
                                          select_tasks, guard_run, source_revision, preserve_cached_cost,
                                          RunConfigurationError)
from experiments.common.benchmark_reuse import ReusePlan, execution_plan
from experiments.common.benchmark_execution import (
    PreparedBindings, ApprovedBindings, run_lock,
)


TYPICAL_ATTACKS = (
    "ignore_previous", "important_instructions", "tool_knowledge",
)


def _safe_result_component(value: str | None, fallback: str) -> str:
    """Return a path-safe component for a user-provided experiment name."""

    component = str(value or "").strip()
    # Model IDs such as ``Qwen/Qwen3-...`` are valid API identifiers but must
    # not create nested result directories. Keep common readable characters
    # and replace everything else with a single dash.
    component = re.sub(r"[^\w.-]+", "-", component, flags=re.UNICODE)
    component = component.strip(" .-_")
    return component or fallback


def _apply_run_name(pipeline, resolved_model_id: str | None, run_name: str | None) -> str:
    """Namespace benchmark runs while retaining the model/run directory layout."""
    backend = get_backend()
    if run_name is None or not str(run_name).strip():
        pipeline.name = f"{pipeline.name}_{backend.id}"
    else:
        model_component = _safe_result_component(resolved_model_id, "model")
        name_component = _safe_result_component(run_name, "run")
        pipeline.name = f"{model_component}_{backend.id}_{name_component}"
    return pipeline.name


def _write_combined_report(output_dir: Path, report_sources: list[tuple[str, Path]]) -> Path:
    """Concatenate each suite report into one easy-to-scan text report."""

    combined_report_path = output_dir / "all_report.txt"
    with combined_report_path.open("w", encoding="utf-8") as combined:
        combined.write("DSCG 评测总报告\n")
        combined.write("=" * 70 + "\n")
        combined.write("本文件按攻击或场景合并报告，具体任务结果见对应标题下的内容。\n")

        for suite_name, report_path in report_sources:
            combined.write("\n\n")
            combined.write("[" + suite_name + "]\n")
            combined.write("-" * 70 + "\n")
            if report_path.exists():
                content = report_path.read_text(encoding="utf-8").strip()
                if content:
                    combined.write(content)
                    combined.write("\n")
            else:
                combined.write(f"报告文件不存在：{report_path}\n")

    return combined_report_path


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


def _router_trace_summary(suite_dir, task_keys, attack_name, run_attack):
    events=[];recorded=0
    for key in task_keys:
        injection=key[1] if len(key)>1 and run_attack else "none"
        path=suite_dir/str(key[0])/attack_name/f"{injection}.json"
        try:
            if not path.resolve().is_relative_to(suite_dir.resolve()):continue
            trace=json.loads(path.read_text())
            value=trace.get("dscg_router_events")
            if isinstance(value,list) and all(isinstance(e,dict) for e in value):
                recorded+=1;events.extend(value)
        except (OSError,ValueError,AttributeError):continue
    return {**summarize_events(events),"expected_task_traces":len(task_keys),"recorded_task_traces":recorded,
            "scope":"recorded scored traces only; missing routing traces are unknown"}


def _describe_pipeline(model_id, sec_model_id, *, origin, defense, **options):
    """Resolve public identity without clients, pipelines, attacks or model requests."""
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
            security = audit.public_dict()
            config_hash = router_configuration_hash(main, audit, input_isolation=isolation,
                authorization_precheck=sandbox, l1_projection_mode=projection,
                planning_tool_view=view, delegated_tasks=delegated,
                audit_retries=options['audit_retries'], completion_prompt=options['completion_prompt'])
            if options['audit_router_mode'] != 'off':
                router = LocalAuditRouter(options['audit_router_mode'], options['audit_router_artifact'], config_hash)
        optimization = {'audit_router_config_sha256': config_hash,
                        'audit_router_artifact_sha256': router.artifact_sha256 if router else None}
        name = defended_pipeline_name(main.model_id, use_sandbox=sandbox, use_security_checker=checker,
            input_isolation=isolation, authorization_precheck=sandbox, l1_projection_mode=projection,
            planning_tool_view=view, delegated_tasks=delegated, audit_router_mode=options['audit_router_mode'],
            audit_router=router, router_config_hash=config_hash)
    return SimpleNamespace(name=name, dscg_model_config=main.public_dict(),
                           dscg_security_model_config=security, dscg_optimization_config=optimization)


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
    planning_tool_view: bool = True,
    delegated_tasks: bool = True,
    l1_projection_mode: str = 'projected',
    task_scope: str = 'partial',
    use_sandbox: bool = True,
    cohort_sha256: str | None = None,
    cohort_path: str | Path | None = None,
    _reuse_plan=None,
) -> int:
    backend = get_backend()
    if task_scope not in {'partial', 'full', 'screened', 'partial_screened'}:
        raise ValueError('unknown task scope')
    if reuse and (force_rerun or not run_name):
        raise ValueError('--reuse requires --name and cannot combine with force_rerun')
    if suites is None and not reuse:
        suites = list(backend.suites)
    if cohort_path is not None:
        if task_scope != 'partial' or not run_attack or task_manifest_path or cohort_sha256:
            raise ValueError('partial --cohort requires attacks and cannot use another manifest or scope')
        from experiments.common.injection_cohort import run_screened
        return run_screened(
            cohort_path, task_scope='partial_screened', suites=suites, model_id=model_id,
            sec_model_id=sec_model_id, origin=origin, defense=defense, config_path=config_path,
            run_name=run_name, results_dir=results_dir, attack=attack, force_rerun=force_rerun, reuse=reuse,
            api_key=api_key, base_url=base_url, provider=provider, api_key_env=api_key_env,
            sec_api_key=sec_api_key, sec_base_url=sec_base_url, sec_provider=sec_provider,
            sec_api_key_env=sec_api_key_env, trace_level=trace_level, tool_metadata_path=tool_metadata_path,
            use_security_checker=use_security_checker, use_sandbox=use_sandbox,
            audit_retries=audit_retries, completion_prompt=completion_prompt,
            audit_router_mode=audit_router_mode, audit_router_artifact=audit_router_artifact,
            planning_tool_view=planning_tool_view, delegated_tasks=delegated_tasks,
            l1_projection_mode=l1_projection_mode,
        )
    logdir = Path(results_dir) if results_dir is not None else BENCHMARK_RESULTS_DIR if task_scope in {'full', 'screened'} else RESULTS_DIR / "partial_benchmark"
    resume = _reuse_plan
    if reuse and resume is None:
        config = resolve_model_config(model_id, api_key=api_key, base_url=base_url, provider=provider,
                                      api_key_env=api_key_env, config_path=config_path)
        base = logdir / (_safe_result_component(config.model_id, 'model') + '_' + backend.id + '_' + _safe_result_component(run_name, 'run'))
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
    _validate_router_controls(origin,use_security_checker,audit_router_mode,use_sandbox)
    validate_controls(origin=origin, use_security_checker=use_security_checker,
                      audit_retries=audit_retries, completion_prompt=completion_prompt)
    frozen_tasks = load_task_manifest(task_manifest_path)
    if task_scope in {'screened', 'partial_screened'}:
        from experiments.common.injection_cohort import _digest
        if (not frozen_tasks or not cohort_sha256 or frozen_tasks.get('cohort_sha256') != cohort_sha256
                or _digest({k: v for k, v in frozen_tasks.items() if k != 'cohort_sha256'}) != cohort_sha256):
            raise ValueError('screened measurement requires the validated frozen cohort identity')
    if task_scope in {'full', 'screened', 'partial_screened'} and frozen_tasks is not None:
        # Validate the full catalogue before model/client construction. DoS later
        # projects this complete catalogue to its native first-injection rule.
        for suite_name in suites:
            suite = get_suite('v1.2', suite_name)
            select_tasks(frozen_tasks, suite_name, list(suite.user_tasks), list(suite.injection_tasks),
                         run_attack, False, task_scope=task_scope)
    attack_names = resolve_attack_names(attack if attack is not None else 'typical') if run_attack else ["none"]
    if task_scope in {'screened', 'partial_screened'} and any(ATTACKS[name].is_dos_attack for name in attack_names):
        raise ValueError('screened measurements do not support DoS')
    logdir = Path(results_dir) if results_dir is not None else BENCHMARK_RESULTS_DIR if task_scope in {'full', 'screened'} else RESULTS_DIR / "partial_benchmark"
    multiple = len(attack_names) > 1
    context = {'execution_plan': execution_plan(task_scope, suites, attack_names, cohort_sha256)}
    run_records = []
    report_sources = []
    print(f"本次攻击 ({len(attack_names) if run_attack else 0}): {', '.join(attack_names) if run_attack else '无（clean）'}", flush=True)
    print(f"本次场景 ({len(suites)}): {', '.join(suites)}", flush=True)

    prepared = resume if resume is not None else PreparedBindings()
    resources = {}
    def group_options(attack_name):
        return dict(
                model_id=model_id, sec_model_id=sec_model_id, suites=suites, run_attack=run_attack, origin=origin, defense=defense,
                api_key=api_key, base_url=base_url, provider=provider, api_key_env=api_key_env,
                sec_api_key=sec_api_key, sec_base_url=sec_base_url, sec_provider=sec_provider,
                sec_api_key_env=sec_api_key_env, config_path=config_path, force_rerun=force_rerun,
                run_name=run_name, trace_level=trace_level, tool_metadata_path=tool_metadata_path,
                results_dir=logdir, attack_name=attack_name,
                use_security_checker=use_security_checker,
                audit_retries=audit_retries, completion_prompt=completion_prompt,
                task_manifest_path=task_manifest_path,
                audit_router_mode=audit_router_mode,audit_router_artifact=audit_router_artifact,
                planning_tool_view=planning_tool_view and not origin and use_sandbox,
                delegated_tasks=delegated_tasks and not origin and use_sandbox,
                l1_projection_mode='off' if origin or not (use_sandbox or use_security_checker) else l1_projection_mode,
                task_scope=task_scope, use_sandbox=use_sandbox, cohort_sha256=cohort_sha256,

        )
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
        approved = ApprovedBindings(prepared)
        jobs = [{'attack': name, 'suite': suite,
                 'options': group_options(name), 'bindings': approved,
                 'execution_plan': context['execution_plan'],
                 'resources': resources}
                for name in attack_names for suite in suites]
        invocation = uuid4().hex
        execution_dir = base / 'execution' / invocation
        execution_dir.mkdir(parents=True, exist_ok=True)
        execution = {'mode': 'serial', 'unit': 'attack_suite',
                     'planned_groups': len(jobs), 'invocation_id': invocation}
        print(f"结果目录: {base}；顺序执行 {len(jobs)} 组。", flush=True)
        started = monotonic()
        try:
            group_results = []
            for index, job in enumerate(jobs, 1):
                print(f"[{index}/{len(jobs)}] {job['attack']}/{job['suite']} 开始", flush=True)
                try:
                    result = {'status': 'completed', 'result': _execute_group(job)}
                except (RunConfigurationError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    result = {'status': 'error', 'error_type': type(exc).__name__}
                group_results.append(result)
                print(f"[{index}/{len(jobs)}] {job['attack']}/{job['suite']} {result['status']}"
                      + (f" ({result['error_type']})" if result['status'] == 'error' else ''), flush=True)
        except KeyboardInterrupt:
            execution.update(status='interrupted', wall_seconds=monotonic() - started)
            (execution_dir / 'execution.json').write_text(json.dumps(execution, indent=2) + '\n')
            print('已中断；保留原参数、运行名并加 --reuse 续跑。', flush=True)
            return 130
        execution.update(status='error' if any(r['status'] == 'error' for r in group_results) else 'completed',
                         wall_seconds=monotonic() - started,
                         groups=[{'attack': j['attack'], 'suite': j['suite'],
                                  **{k: v for k, v in r.items() if k != 'result'}}
                                 for j, r in zip(jobs, group_results)])
        (execution_dir / 'execution.json').write_text(json.dumps(execution, indent=2) + '\n')
        for name in attack_names:
            entries = [(j, r) for j, r in zip(jobs, group_results) if j['attack'] == name]
            errors = [(j, r) for j, r in entries if r['status'] == 'error']
            report_sources_for_attack = []
            for job, result in entries:
                if result['status'] == 'completed':
                    context.setdefault('suite_reports', []).extend(result['result']['suite_reports'])
                    report_sources_for_attack.append((job['suite'], base / name / job['suite'] / 'report.txt'))
            if errors:
                for job, result in errors:
                    run_records.append({'attack': name, 'status': 'error', 'failed_suite': job['suite'],
                                        'error_type': result['error_type']})
            else:
                run_records.append({'attack': name, 'status': 'completed', 'output_dir': str(base / name)})
            if report_sources_for_attack:
                _write_combined_report(base / name, report_sources_for_attack)
                report_sources.append((name, base / name / 'all_report.txt'))

        fallback = logdir / (backend.id + "_" + _safe_result_component(run_name, "attack-run"))
        batch_dir = context.get("base_output_dir", fallback)
        batch_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": "dscg.attack-manifest.v2", "benchmark": benchmark_identity(),
            "task_scope": task_scope,
            "result_layout": "model_run/attack/suite",
            "pipeline_name": context.get("pipeline_name"),
            "model_id": context.get("model_id"),
            "attacks": attack_names if run_attack else [],
            "suites": suites,
            "suite_scope": "all_registered" if set(suites) == set(backend.suites) else "selected",
            "excluded_from_all": {"manual": "requires interactive input"},
            "runs": run_records, "execution": execution,
        }
        if cohort_sha256 is not None:
            manifest['cohort_sha256'] = cohort_sha256
        manifest_path = batch_dir / "attack_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        if multiple:
            for record in run_records:
                if record["status"] == "error":
                    error_path = batch_dir / f"{_safe_result_component(record['attack'], 'attack')}_error.txt"
                    error_path.write_text(f"运行失败: {record['error_type']}；未生成完整指标，已有逐任务结果可能不完整。\n", encoding="utf-8")
                    report_sources.append((record["attack"], error_path))
        if report_sources:
            _write_combined_report(batch_dir, report_sources)
        overview_path, failures_path = write_run_overview(
            batch_dir, attack_names, suites, run_records, context.get("suite_reports", []),
            model_id=context.get("model_id", model_id), task_scope=task_scope,
        )
        print(f"📝 紧凑摘要: {overview_path}")
        print(f"🔎 失败片段: {failures_path}")
        print(f"📋 攻击执行清单: {manifest_path}")
        return 1 if (any(record["status"] == "error" for record in run_records) or
                     any(report.get("task_errors") for report in context.get("suite_reports", []))) else 0


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
    planning_tool_view: bool = True,
    delegated_tasks: bool = True,
    l1_projection_mode: str = 'projected',
    task_scope: str = 'partial',
    use_sandbox: bool = True,
    cohort_sha256: str | None = None,
    reuse_plan=None,
    prepare_only=False,
    only_suite=None,
    group_mode=False,
    resource_cache=None,
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
    _validate_router_controls(origin,use_security_checker,audit_router_mode,use_sandbox)
    validate_controls(origin=origin, use_security_checker=use_security_checker,
                      audit_retries=audit_retries, completion_prompt=completion_prompt)
    frozen_tasks = load_task_manifest(task_manifest_path)
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
    report_sources: list[tuple[str, Path]] = []
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
                    audit_router_artifact=audit_router_artifact, audit_retries=audit_retries,
                    completion_prompt=completion_prompt)
            pipeline = copy(resource_cache['descriptor'])
        else:
            sec_tracker = None
            if origin:
                pipeline, main_tracker = make_openai_compatible_pipeline(
                    model_id,
                    ad_defense=defense,
                    api_key=api_key,
                    base_url=base_url,
                    provider=provider,
                    api_key_env=api_key_env,
                    config_path=config_path,
                )

            else:
                pipeline, main_tracker, sec_tracker = make_defended_pipeline(
                    model_id,
                    sec_model_id,
                    api_key=api_key,
                    base_url=base_url,
                    provider=provider,
                    api_key_env=api_key_env,
                    sec_api_key=sec_api_key,
                    sec_base_url=sec_base_url,
                    sec_provider=sec_provider,
                    sec_api_key_env=sec_api_key_env,
                    config_path=config_path,
                    trace_level=trace_level,
                    tool_metadata=tool_metadata,
                    use_security_checker=use_security_checker,
                    use_sandbox=use_sandbox,
                    audit_retries=audit_retries, completion_prompt=completion_prompt,
                    audit_router_mode=audit_router_mode,audit_router_artifact=audit_router_artifact,
                    planning_tool_view=planning_tool_view, delegated_tasks=delegated_tasks,
                    l1_projection_mode=l1_projection_mode,
                )


        main_model_config = getattr(pipeline, "dscg_model_config", {})
        sec_model_config = getattr(pipeline, "dscg_security_model_config", {})
        resolved_model_id = main_model_config.get("model_id", model_id)
        resolved_sec_model_id = None if origin or not use_security_checker else sec_model_config.get("model_id", sec_model_id)
        result_dir_name = _apply_run_name(pipeline, resolved_model_id, run_name)
        base_output_dir = logdir / result_dir_name
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
        run_binding = {
            "schema_version": f"dscg.{task_scope}-run.v2",
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
            "defense_version": None if origin else FRAMEWORK_VERSION,
            "input_isolation": bool(not origin and (use_sandbox or use_security_checker)),
            'l1_projection_mode': 'off' if origin else l1_projection_mode,
            'l1_projection_profile_sha256': None if origin else L1_PROFILE_SHA256,
            "authorization_precheck": bool(not origin and use_sandbox),
            'planning_tool_view': bool(planning_tool_view and not origin),
            'delegated_tasks': bool(delegated_tasks and not origin),
            "audit_router_mode": audit_router_mode,
            "audit_router_artifact_sha256": getattr(pipeline,"dscg_optimization_config",{}).get("audit_router_artifact_sha256"),
            "audit_router_config_sha256": getattr(pipeline,"dscg_optimization_config",{}).get("audit_router_config_sha256"),
        }
        if cohort_sha256 is not None:
            run_binding['cohort_sha256'] = cohort_sha256
        recorded_binding = bind(output_dir / suite_name / "run_manifest.json", run_binding)

        planned_task_count = (
            len(selected_users) * len(selected_injections)
            if run_attack
            else len(selected_users)
        )
        if prepare_only:
            continue
        print(f"用户任务={len(selected_users)}；注入目标={len(selected_injections)}；计划组合={planned_task_count}", flush=True)
        if report_context is not None:
            report_context['pipeline_name'] = result_dir_name
        pipeline.name = attack_component
        try:
            with logging.OutputLogger(str(base_output_dir)):
                if run_attack:
                    results = benchmark.benchmark_suite_with_injections(
                        pipeline,
                        suite,
                        attack,
                        base_output_dir,
                        force_rerun=force_rerun,
                        user_tasks = selected_users,
                        injection_tasks = selected_injections,
                        verbose= True,
                        benchmark_version=SUITE_VERSION,
                    )
                else:
                    results = benchmark.benchmark_suite_without_injections(
                        pipeline,
                        suite,
                        base_output_dir,
                        force_rerun=force_rerun,
                        user_tasks = selected_users,
                        benchmark_version=SUITE_VERSION,
                    )
        finally:
            pipeline.name = result_dir_name

        # 结果分析
        utility_results = results["utility_results"]
        security_results = results.get("security_results", {})
        print(f"实际完成评测任务数量: {len(utility_results)}")

        # 1. 确保目录存在 (避免 FileNotFoundError)
        suite_output_dir = output_dir / suite_name
        suite_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 定义各类文件保存路径
        # report_file_path = output_dir / f"{suite_name}_report.txt"
        # csv_file_path = output_dir / f"{suite_name}_detailed_results.csv"
        # summary_file_path = output_dir / f"{suite_name}_summary.json"
        report_file_path = suite_output_dir / "report.txt"
        csv_file_path = suite_output_dir / "detailed_results.csv"
        summary_file_path = suite_output_dir / "summary.json"

        #

        # ==========================================
        # 2. 构造结构化数据列表 (用于画图)
        # ==========================================
        outcomes = project_outcomes(utility_results, security_results, suite_output_dir,
                                    attack_name if run_attack else "none", run_attack=run_attack)
        structured_records = []
        for task_key, util_status in utility_results.items():
            user_task_id = task_key[0]
            injection_task_id = task_key[1] if len(task_key) > 1 else "None"
            
            # AgentDojo 原生定义: True 代表执行了恶意指令(攻击成功)，False 代表安全
            outcome = outcomes[task_key]

            structured_records.append({
                "suite_name": suite_name,
                "model_id": resolved_model_id,
                "attack_type": attack_name if run_attack else "None",
                "user_task_id": user_task_id,
                "injection_task_id": injection_task_id,
                **outcome,
            })

        # 3. 计算聚合得分 (Summary)
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
            "run_manifest": recorded_binding,
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
        if cohort_sha256 is not None:
            summary_data['cohort_sha256'] = cohort_sha256

        if sec_tracker:
            summary_data["sec_overhead"] = {
                "prompt_tokens": sec_prompt_tokens,
                "completion_tokens": sec_completion_tokens,
                "total_tokens": sec_total_tokens
            }

        preserve_cached_cost(summary_data, summary_file_path, force_rerun)
        prompt_tokens = summary_data["overhead"]["prompt_tokens"]
        completion_tokens = summary_data["overhead"]["completion_tokens"]
        total_tokens = summary_data["overhead"]["total_tokens"]
        if sec_tracker and "sec_overhead" in summary_data:
            sec_prompt_tokens = summary_data["sec_overhead"]["prompt_tokens"]
            sec_completion_tokens = summary_data["sec_overhead"]["completion_tokens"]
            sec_total_tokens = summary_data["sec_overhead"]["total_tokens"]

        # 4. 写入文件 (TXT, CSV, JSON)
        # 4.1 保存供人类阅读的 TXT 报告
        with open(report_file_path, "w", encoding="utf-8") as f:
            f.write("\n" + "="*50 + "\n")
            f.write(f"Pipeline: {summary_data['pipeline_name']} | Model: {resolved_model_id}, Sec Model:{resolved_sec_model_id}\n")
            f.write(f"Attack: {attack_name if run_attack else 'none'} | Kind: {summary_data['attack_kind']}\n")
            if is_dos_attack:
                f.write("DoS ASR 使用 AgentDojo 的任务失败口径（not utility），不等于目标工具攻击成功率。\n")
            f.write(f"📊 [{suite_name}] 任务详细执行报告\n")
            f.write("="*50 + "\n")

            for record in structured_records:
                util_str = "⚪ 无效/错误" if record["utility_success"] is None else "✅ 成功 (True)" if record["utility_success"] else "❌ 失败 (False)"
                
                if run_attack:
                    if record["sample_status"] != "valid":
                        sec_str = f"⚪ 无效样本 ({record['sample_status']})"
                    else:
                        sec_str = "🛡️ 防御成功 (True)" if record["defense_success"] else "⚠️ 被攻破 (False)"
                    f.write(f"📌 [用户任务]: {record['user_task_id']:<25} | [注入攻击]: {record['injection_task_id']:<25}\n")
                    f.write(f"   -> 功能性 (Utility): {util_str:<15} | 安全性 (Security): {sec_str}\n")
                else:
                    f.write(f"📌 [用户任务]: {record['user_task_id']:<25}\n")
                    f.write(f"   -> 功能性 (Utility): {util_str}\n")
                f.write("-" * 50 + "\n")

            f.write("\n🏆 总体评测得分汇总:\n")
            f.write(f"👉 实际评测任务数量: {len(utility_results)}\n")
            f.write(f"👉 User Tasks: {len(selected_users)}/{len(user_task_ids)}\n")
            f.write(f"👉 Injection Tasks: {len(selected_injections)}/{len(injection_task_ids)}\n")
            f.write(f"👉 [{suite_name}] 整体可用性 (Utility): " + (f"{utility_score:.2%}" if utility_score is not None else "N/A") + "\n")
            if run_attack and security_score is not None:
                f.write(f"👉 [{suite_name}] 攻击成功率 (ASR): {security_score:.2%}\n")
                f.write(f"👉 [{suite_name}] 整体安全性 (Defense Rate): {defense_score:.2%}\n")


            f.write("\n💰 系统开销评估 (Overhead):\n")
            f.write(f"统计范围: {summary_data['cost_scope']}；本次新增调用 Token: {summary_data['invocation_cost']['overhead']['total_tokens']}\n")
            f.write(f"👉 任务 Input Tokens: {prompt_tokens:.1f}\n")
            f.write(f"👉 任务 Output Tokens: {completion_tokens:.1f}\n")
            f.write(f"👉 任务总计 Tokens: {total_tokens:.1f}\n")
            if sec_tracker:            
                f.write("\n💰 安全模型开销评估 (Overhead):\n")
                f.write(f"👉 Sec Input Tokens: {sec_prompt_tokens:.1f}\n")
                f.write(f"👉 Sec Output Tokens: {sec_completion_tokens:.1f}\n")
                f.write(f"👉 Sec Tokens: {sec_total_tokens:.1f}\n")

            f.write("="*50 + "\n\n")

        # 4.2 保存用于画图和数据分析的 CSV 详细表格
        if structured_records:
            with open(csv_file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=structured_records[0].keys())
                writer.writeheader()
                writer.writerows(structured_records)

        # 4.3 保存聚合数据的 JSON (方便后续写脚本对比多模型的表现)
        with open(summary_file_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=4, ensure_ascii=False)

        if report_context is not None:
            report_context.setdefault("suite_reports", []).append(collect_suite_report(
                base_output_dir, suite_output_dir, summary_data, structured_records, suite,
            ))

        report_sources.append((suite_name, report_file_path))

        # 写完文件后，在控制台给个提示
        print(f"✅ [{suite_name}] 测试完成！")
        print(f"📄 文本报告: {report_file_path}")
        print(f"📊 数据表格(用于画图): {csv_file_path}")
        print(f"📈 得分汇总: {summary_file_path}\n")

    if output_dir is not None and report_sources and not group_mode:
        combined_report_path = _write_combined_report(output_dir, report_sources)
        print("✅ 所选场景的报告已合并")
        print(f"📚 总报告: {combined_report_path}\n")
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
        help="本次运行名称；结果保存于 --results-dir 指定目录下的 <model_id>_<backend>_<NAME>/。",
    )
    parser.add_argument(
        "--trace-level",
        choices=("summary", "standard", "full"),
        default=os.getenv("DSCG_TRACE_LEVEL", "summary"),
        help="任务 JSON 中 DSCG 记录级别；默认 summary，full 会额外保存压缩审计侧车。",
    )
    parser.add_argument(
        "--include-extra-info",
        action="store_true",
        help="兼容快捷开关，等同于 --trace-level full，将完整审计/动作记录写入 JSON。",
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
    parser.add_argument('--l1-projection-mode', choices=('off','shadow','projected'), default='projected',
                        help='L1有限交易投影，默认projected；off保留旧来源封装，shadow只观察。')
    # None selects the profile default below: DSCG shadow, baseline/NoChecker off.
    parser.add_argument("--audit-router-mode", choices=("off", "shadow", "selective"), default=None,
                        help="L3纯算法路由；DSCG CLI默认shadow，baseline/NoChecker默认off；可显式选择。")
    parser.add_argument("--audit-router-artifact",help="冻结的独立分组校准JSON；缺失/无效时保留完整审计。")
    parser.add_argument("--audit-retries", type=int, choices=(0, 1), default=0, help="语义 abstain 有界重审次数；默认 0。")
    parser.add_argument("--completion-prompt", action="store_true", help="启用通用任务完成提示；默认关闭。")
    parser.add_argument("--clean", action="store_true", help="用相同用户任务运行无攻击效用控制。")
    parser.add_argument("--task-manifest", dest="task_manifest_path", help="读取冻结 v1.2 全量任务清单；拒绝缩小实际执行集合。" if full else "读取冻结 v1.2 任务 ID 清单。")
    parser.add_argument("--write-task-manifest", metavar="PATH", help="离线导出当前任务 ID 清单并退出，不调用模型。")
    parser.add_argument('--cohort', dest='cohort_path', help=(
        '冻结的 injection 预检名单；显式标为 screened，保留全部用户任务。' if full else
        '冻结的 injection 预检名单；保留每场景前3个用户，仅过滤原来前3个注入目标，不补位。'))
    args = parser.parse_args(argv)
    if args.audit_router_mode is None:
        args.audit_router_mode = 'off' if args.baseline or args.no_checker else 'shadow'
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
    cohort_path = getattr(args, 'cohort_path', None)
    if (require_cohort or cohort_path is not None) and not cohort_path:
        parser.error('screened benchmark requires a nonempty --cohort PATH')
    if cohort_path and (args.clean or args.task_manifest_path or args.write_task_manifest):
        parser.error('--cohort cannot be combined with --clean, --task-manifest, or --write-task-manifest')
    if cohort_path and not args.run_name:
        parser.error('--cohort requires a new --name')
    try:
        validate_controls(origin=args.baseline, use_security_checker=not args.no_checker,
                          audit_retries=args.audit_retries, completion_prompt=args.completion_prompt)
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
        if cohort_path is not None:
            if full and entrypoint is None:
                from experiments.run_benchmark import main as execution
                dispatch_options.pop('task_scope', None)
            dispatch_options['cohort_path'] = cohort_path
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
            run_name=args.run_name,
            trace_level="full" if args.include_extra_info else args.trace_level,
            tool_metadata_path=args.tool_metadata_path,
            config_path=args.config_path,
            results_dir=args.results_dir if args.results_dir is not None else BENCHMARK_RESULTS_DIR if full else None,
            attack=selected_attacks,
            use_security_checker=not args.no_checker, audit_retries=args.audit_retries,
            completion_prompt=args.completion_prompt, task_manifest_path=args.task_manifest_path,
            audit_router_mode=args.audit_router_mode,audit_router_artifact=args.audit_router_artifact,
            planning_tool_view=not args.no_tool_view and not args.baseline,
            delegated_tasks=not args.no_delegated_tasks and not args.baseline,
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
