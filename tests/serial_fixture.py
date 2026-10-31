"""Native sequential-loop fixture. No remote clients or credentials."""
from types import SimpleNamespace
from contextlib import contextmanager
from unittest.mock import patch
from pathlib import Path
from dscg.benchmark_catalog import get_suites, get_suite
from dscg.model_config import ModelConfig

MAIN = ModelConfig('offline-model', 'fixture-key', 'https://example.invalid', 'custom')
AUDIT = ModelConfig('offline-audit', 'fixture-key', 'https://example.invalid', 'custom')

def resolve(*args, **kwargs):
    return AUDIT if kwargs.get('prefix') == 'DSCG_SEC' else MAIN

class Tracker:
    def __init__(self): self.total_prompt_tokens=0; self.total_completion_tokens=0
    def get_total_tokens(self): return self.total_prompt_tokens+self.total_completion_tokens
    def snapshot(self): return {'fixture':{'api_calls':self.total_prompt_tokens//11,'total_tokens':self.get_total_tokens(), 'prompt_tokens':self.total_prompt_tokens,'completion_tokens':0}}

def baseline(*args, **kwargs):
    tracker=Tracker()
    pipe=SimpleNamespace(name='offline-model',dscg_model_config=MAIN.public_dict(),main_tracker=tracker)
    return pipe,tracker

def defended(*args, **kwargs):
    pipe,main=baseline(); audit=Tracker()
    pipe.dscg_security_model_config=AUDIT.public_dict()
    pipe.sec_tracker=audit
    from experiments import run_partial_benchmark as runner
    description = runner._describe_pipeline(args[0] if args else None, args[1] if len(args)>1 else None,
        origin=False, defense=None, **{**dict(use_sandbox=True, use_security_checker=True,
            l1_projection_mode='projected', planning_tool_view=True, delegated_tasks=True,
            audit_router_mode='off', audit_router_artifact=None, audit_retries=0, completion_prompt=False), **kwargs})
    pipe.name = description.name
    pipe.dscg_optimization_config = description.dscg_optimization_config
    return pipe,main,audit

def attack(name,*args):
    from agentdojo.attacks.attack_registry import ATTACKS
    return SimpleNamespace(name=name,is_dos_attack=ATTACKS[name].is_dos_attack,attack=lambda *_:{})

def execute(suite,pipeline,task,injection_task=None,injections=None):
    from agentdojo import logging
    pipeline.main_tracker.total_prompt_tokens+=11
    if hasattr(pipeline,'sec_tracker'): pipeline.sec_tracker.total_prompt_tokens+=11
    logging.Logger.get().log([
        {'role':'user','content':[{'type':'text','content':getattr(task,'GOAL','fixture')}]},
        {'role':'assistant','content':[{'type':'text','content':'offline response'}],'tool_calls':None},
    ])
    return task.ID != 'user_task_0',False

@contextmanager
def patched(execute_fn=execute):
    from experiments import run_partial_benchmark as runner
    from experiments.common.attack_execution import iter_serial_results
    with patch.object(runner,'iter_attack_results',side_effect=iter_serial_results), \
         patch.object(runner,'make_openai_compatible_pipeline',side_effect=baseline), \
         patch.object(runner,'make_defended_pipeline',side_effect=defended), \
         patch.object(runner,'resolve_model_config',side_effect=resolve), \
         patch.object(runner.attacks,'load_attack',side_effect=attack), \
         patch.object(type(get_suite('v1.2',get_suites()[0])),'run_task_with_pipeline',new=execute_fn):
        yield
