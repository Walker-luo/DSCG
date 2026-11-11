"""Importable child fixture: real backend loops, synthetic pipeline, no network."""
import json
import os
from pathlib import Path
import time

import serial_fixture


def execute_interruptible(job):
    """Pause between suites so interruption never tears a fixture JSON write."""
    from dscg.benchmark_catalog import get_suites
    if job['suite'] != get_suites()[0]:
        while True:
            time.sleep(0.05)
    return execute(job)


def execute(job):
    from experiments import run_partial_benchmark as runner
    folder = next(p.parent for p in job['bindings'].checked
                  if p.name == 'run_manifest.json' and p.parent.name == job['suite']
                  and p.parent.parent.name == job['attack'])
    folder.mkdir(parents=True, exist_ok=True)
    def append(value):
        with (folder/'fixture_events.jsonl').open('a') as out:
            out.write(json.dumps({'pid': os.getpid(), 'time': time.monotonic(), **value})+'\n')
    def task(*args, **kwargs):
        injection = args[3] if len(args)>3 else kwargs.get('injection_task')
        append({'kind':'task', 'user':args[2].ID,'injection':getattr(injection,'ID',None)})
        return serial_fixture.execute(*args, **kwargs)
    append({'kind':'start'})
    from unittest.mock import patch
    original_open = Path.open
    frozen_path = job['options'].get('task_manifest_path')
    def checked_open(path, *args, **kwargs):
        if frozen_path and path.resolve().is_relative_to(Path(frozen_path).resolve().parent):
            raise AssertionError('worker reopened frozen cohort or original evidence')
        return original_open(path, *args, **kwargs)
    with serial_fixture.patched(execute_fn=task), patch.object(Path, 'open', checked_open):
        result = runner._execute_group(job)
    append({'kind':'end'})
    return result
