"""Importable spawned-process fixture. No remote clients or credentials."""
from types import SimpleNamespace
from contextlib import contextmanager
from unittest.mock import patch
from pathlib import Path
import os,time
from dscg.benchmark_catalog import get_suites, get_suite
from dscg.model_config import ModelConfig
from experiments.run_partial_benchmark import _execute_group as execute_real_group

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
    return pipe,main,audit

def attack(name,*args):
    return SimpleNamespace(name=name,is_dos_attack=False,attack=lambda *_:{})

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
    with patch.object(runner,'make_openai_compatible_pipeline',side_effect=baseline), \
         patch.object(runner,'make_defended_pipeline',side_effect=defended), \
         patch.object(runner,'resolve_model_config',side_effect=resolve), \
         patch.object(runner.attacks,'load_attack',side_effect=attack), \
         patch.object(type(get_suite('v1.2',get_suites()[0])),'run_task_with_pipeline',autospec=True,side_effect=execute_fn):
        yield

def group(job):
    start=time.monotonic()
    if job.get('resources') is not None:
        result=execute_real_group(job)
    else:
        with patched():
            result=execute_real_group(job)
    result.update(pid=os.getpid(),started=start,ended=time.monotonic())
    return result
