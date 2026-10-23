"""Prepared bindings and bounded attack/suite processes; no model or scoring loop."""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import fcntl
import hashlib
import json
import multiprocessing
import signal
from multiprocessing.connection import wait
from pathlib import Path

from experiments.common.partial_controls import RunConfigurationError, guard_run


def validate_workers(value):
    if type(value) is not int or value < 1:
        raise ValueError('workers must be a positive integer')
    return value


@contextmanager
def run_lock(base):
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    with (base / '.benchmark.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RunConfigurationError('another benchmark invocation is using this run directory') from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class PreparedBindings:
    """Validate a complete fresh/cache plan without partially writing bindings."""
    def __init__(self):
        self.checked, self.pending, self.hashes = {}, {}, {}
        self.committed = False

    def check(self, path, expected):
        path = Path(path)
        if path in self.checked and self.checked[path] != expected:
            raise RunConfigurationError('inconsistent prepared run identity')
        if path.exists():
            if json.loads(path.read_text()) != expected:
                raise RunConfigurationError(f'run configuration changed: {path}; use a new --name')
            self.hashes[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            if path.parent.exists() and ((path.parent / 'summary.json').exists()
                    or any(path.parent.rglob('injection_task_*.json')) or any(path.parent.rglob('none.json'))):
                raise RunConfigurationError('unbound historical cache; use a new --name')
            self.pending[path] = expected
        self.checked[path] = expected
        return expected

    def commit(self):
        if any(hashlib.sha256(p.read_bytes()).hexdigest() != h for p, h in self.hashes.items()):
            raise RunConfigurationError('run evidence changed during preparation')
        for path, value in self.pending.items():
            guard_run(path, value)
        self.committed = True

    def guard(self, path, expected):
        path = Path(path)
        if not self.committed or self.checked.get(path) != expected:
            raise RunConfigurationError('execution differs from validated plan')
        recorded = json.loads(path.read_text())
        if recorded != expected:
            raise RunConfigurationError('run evidence changed after preparation')
        return recorded


class ApprovedBindings:
    """Small read-only capability passed to workers, never the mutable reuse plan."""
    def __init__(self, plan):
        self.checked = plan.checked
        self.recorded = {p: json.loads(p.read_text()) for p in self.checked}

    def guard(self, path, expected):
        path = Path(path)
        if (self.checked.get(path) != expected or
                json.loads(path.read_text()) != self.recorded[path]):
            raise RunConfigurationError('worker configuration/evidence differs from approved plan')
        return self.recorded[path]


def _child(worker, job, connection, log_path, signal_mask=None):
    try:
        if signal_mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, signal_mask)
        with Path(log_path).open('w', buffering=1) as stream, redirect_stdout(stream), redirect_stderr(stream):
            try:
                value = {'status': 'completed', 'result': worker(job)}
            except BaseException as exc:
                # Provider exception text can contain credentials. Persist only its type.
                value = {'status': 'error', 'error_type': type(exc).__name__}
        connection.send(value)
    finally:
        connection.close()


def execute_groups(jobs, workers, worker, logdir):
    """One isolated spawn per group, bounded running count, stable result order."""
    validate_workers(workers)
    if not jobs:
        return []
    results = [None] * len(jobs)
    effective = min(workers, len(jobs))
    ctx = multiprocessing.get_context('spawn')
    running = {}
    next_job = 0
    Path(logdir).mkdir(parents=True, exist_ok=True)
    try:
        while next_job < len(jobs) or running:
            while next_job < len(jobs) and len(running) < effective:
                index = next_job; next_job += 1
                job = jobs[index]
                print(f"[{job['attack']}/{job['suite']}] 开始 ({index + 1}/{len(jobs)})", flush=True)
                if workers == 1:
                    try:
                        results[index] = {'status': 'completed', 'result': worker(job)}
                    except (RunConfigurationError, KeyboardInterrupt):
                        raise
                    except Exception as exc:
                        results[index] = {'status': 'error', 'error_type': type(exc).__name__}
                    print(f"[{job['attack']}/{job['suite']}] {results[index]['status']}；完成 {sum(v is not None for v in results)}/{len(jobs)}", flush=True)
                    continue
                receive, send = ctx.Pipe(duplex=False)
                log = Path(logdir) / f'group_{index + 1:04d}.log'
                # Defer SIGINT through spawn+registration; otherwise a child can
                # exist before the parent has a PID/registry entry to reap it.
                previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
                try:
                    process = ctx.Process(target=_child, args=(worker, job, send, log, previous_mask))
                    running[receive] = (index, process, log)
                    process.start()
                except BaseException:
                    if receive not in running:
                        receive.close()
                    raise
                finally:
                    send.close()
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            if not running:
                continue
            for connection in wait(list(running), timeout=.2):
                index, process, log = running[connection]
                try:
                    results[index] = connection.recv()
                except EOFError:
                    results[index] = {'status': 'error', 'error_type': 'WorkerExit'}
                finally:
                    connection.close()
                process.join()
                del running[connection]
                results[index]['log_path'] = str(log)
                job = jobs[index]
                print(f"[{job['attack']}/{job['suite']}] {results[index]['status']}；完成 {sum(v is not None for v in results)}/{len(jobs)}", flush=True)
    finally:
        for connection, (_, process, _) in running.items():
            if process.pid is not None and process.is_alive():
                process.terminate()
        for connection, (_, process, _) in running.items():
            if process.pid is not None:
                process.join(timeout=5)
                if process.is_alive():
                    process.kill(); process.join()
            connection.close()
    return results
