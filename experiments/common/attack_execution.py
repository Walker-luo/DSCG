"""Spawn one isolated process per attack; keep suites sequential inside it."""
from contextlib import redirect_stderr, redirect_stdout
import logging
import multiprocessing
from multiprocessing.connection import wait
import os
import signal
import sys

from experiments.common.error_diagnostics import execution_error_diagnostics


def group_result(job, execute=None):
    if job.get('compatibility') is not None:
        return job['compatibility']
    if execute is None:
        from experiments.run_partial_benchmark import _execute_group
        execute = _execute_group
    try:
        result = execute(job)
        errors = sum(r.get('task_errors', 0) + r.get('goal_preflight_errors', 0)
                     for r in result.get('suite_reports', []))
        return {'status': 'completed', 'result': result, **({'task_errors': errors} if errors else {})}
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        from dscg.request_compatibility import api_error_diagnostics
        result = {'status': 'error', 'error_type': type(exc).__name__,
                  'execution_error': execution_error_diagnostics(exc)}
        diagnostic = api_error_diagnostics(exc)
        if diagnostic is not None:
            result['api_error'] = diagnostic
        return result


def iter_serial_results(jobs, *, on_event, execute=None):
    for index, job in enumerate(jobs):
        on_event({'kind': 'group_start', 'index': index, 'attack': job['attack'], 'suite': job['suite']})
        yield index, group_result(job, execute)


class _EventStream:
    """Forward native text without terminal control or a child Rich renderer."""
    encoding = 'utf-8'
    def __init__(self, send):
        self.send = send
        self.pending = ''

    def isatty(self):
        return False

    def write(self, text):
        self.pending += text
        while '\n' in self.pending:
            line, self.pending = self.pending.split('\n', 1)
            self.send({'kind': 'log', 'text': line})
        # Bound buffering for native writes which have no newline.
        if len(self.pending) >= 4096:
            self.flush()
        return len(text)

    def flush(self):
        if self.pending:
            self.send({'kind': 'log', 'text': self.pending})
            self.pending = ''


def _attack_worker(connection, indexed_jobs, execute):
    # Only the parent handles terminal Ctrl-C and coordinates shutdown.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    current = {'attack': indexed_jobs[0][1]['attack'], 'suite': None}
    def send(event):
        connection.send(('event', {**current, **event}))
    stream = _EventStream(send)
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    root.handlers = [logging.StreamHandler(stream)]
    from experiments.common.benchmark_progress import progress_events
    try:
        with redirect_stdout(stream), redirect_stderr(stream), progress_events(send):
            send({'kind': 'worker_start', 'pid': os.getpid()})
            for index, job in indexed_jobs:
                current['suite'] = job['suite']
                send({'kind': 'group_start', 'index': index})
                result = group_result(job, execute)
                stream.flush()
                connection.send(('result', index, result))
    finally:
        root.handlers = previous_handlers
        stream.flush()
        connection.close()


def iter_attack_results(jobs, *, on_event, execute=None):
    """Yield indexed results as ready; callers retain registration-order reports."""
    attacks = list(dict.fromkeys(job['attack'] for job in jobs))
    runnable = [a for a in attacks if any(j['attack'] == a and j.get('compatibility') is None for j in jobs)]
    if len(runnable) <= 1:
        yield from iter_serial_results(jobs, on_event=on_event, execute=execute)
        return
    context = multiprocessing.get_context('spawn')
    workers = {}
    delivered, started = set(), set()
    try:
        for attack in attacks:
            indexed = [(i, j) for i, j in enumerate(jobs) if j['attack'] == attack]
            if attack not in runnable:
                for index, job in indexed:
                    on_event({'kind': 'group_start', 'index': index, 'attack': attack, 'suite': job['suite']})
                    delivered.add(index)
                    yield index, job['compatibility']
                continue
            # Do not serialize descriptors, clients or live native suite objects.
            indexed = [(i, {**j, 'resources': {k: v for k, v in j.get('resources', {}).items()
                                             if k in {'task_manifest', 'metadata'}}}) for i, j in indexed]
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(target=_attack_worker, args=(sender, indexed, execute), name=f'dscg-{attack}')
            try:
                process.start()
                workers[receiver] = (process, indexed)
                sender.close()
            except BaseException as exc:
                # Ctrl-C can arrive after OS creation but before registration.
                workers.pop(receiver, None)
                if process.pid is not None:
                    if process.is_alive(): process.terminate()
                    process.join()
                receiver.close(); sender.close(); process.close()
                if not isinstance(exc, Exception):
                    raise
                for index, _job in indexed:
                    delivered.add(index)
                    yield index, {'status': 'error', 'error_type': 'WorkerStartError',
                                  'not_started': True, 'execution_error': execution_error_diagnostics(exc)}
        active = set(workers)
        while active:
            for receiver in wait(list(active), timeout=.2):
                try:
                    message = receiver.recv()
                except (EOFError, OSError):
                    process, indexed = workers[receiver]
                    process.join(timeout=1)
                    active.remove(receiver)
                    for index, _job in indexed:
                        if index not in delivered:
                            delivered.add(index)
                            yield index, {'status': 'error', 'error_type': 'WorkerProcessError',
                                          'exit_code': process.exitcode, 'not_started': index not in started}
                    continue
                if message[0] == 'event':
                    event = message[1]
                    if event['kind'] == 'group_start': started.add(event['index'])
                    on_event(event)
                else:
                    _, index, result = message
                    delivered.add(index)
                    yield index, result
    finally:
        for receiver, (process, _indexed) in workers.items():
            if process.is_alive(): process.terminate()
        for receiver, (process, _indexed) in workers.items():
            process.join(timeout=5)
            if process.is_alive():
                process.kill(); process.join()
            receiver.close()
            process.close()


class AttackOutput:
    """The parent owns the only terminal renderer and all forwarded native text."""
    def __init__(self, jobs, progress):
        self.jobs, self.progress = jobs, progress
        self.bars = {}
        self.rich = None
        self.workers = []

    def __enter__(self):
        return self

    def line(self, text):
        if self.rich is not None:
            self.rich.console.print(text, markup=False, highlight=False)
        else:
            print(text, flush=True)

    def event(self, event):
        kind = event['kind']
        if kind == 'worker_start':
            self.workers.append({'attack': event['attack'], 'pid': event['pid']})
        elif kind == 'group_start':
            if not self.progress:
                self.line(f"[{event['index']+1}/{len(self.jobs)}] {event['attack']}/{event['suite']} 开始")
        elif kind == 'log':
            self.line(f"[{event['attack']}/{event['suite'] or '-'}] {event['text']}")
        elif kind.startswith('progress_'):
            from experiments.common.benchmark_progress import GroupProgress
            label = event['label']
            if kind == 'progress_start':
                if sys.stdout.isatty() and self.rich is None:
                    from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
                    self.rich = Progress(TextColumn('{task.description}'), BarColumn(), TaskProgressColumn(), TimeElapsedColumn())
                    self.rich.start()
                bar = GroupProgress(label, goal_total=event['goal_total'], score_total=event['score_total'],
                                    shared_progress=self.rich)
                self.bars[label] = bar
                bar.__enter__()
            elif kind == 'progress_step':
                self.bars[label].advance(event['phase'])
            elif kind == 'progress_end':
                status = event['status']
                self.bars.pop(label).__exit__(None if status == 'completed' else
                                             KeyboardInterrupt if status == 'interrupted' else RuntimeError, None, None)

    def result(self, index, result):
        job = self.jobs[index]
        if result['status'] != 'completed' and f"{job['attack']}/{job['suite']}" in self.bars:
            self.event({'kind': 'progress_end', 'label': f"{job['attack']}/{job['suite']}", 'status': 'error'})
        if result.get('api_error'):
            import json
            self.line(f"[{job['attack']}/{job['suite']}] API诊断: {json.dumps(result['api_error'], ensure_ascii=False)}")
        if result.get('execution_error'):
            location = result['execution_error']
            frame = location['frames'][-1] if location['frames'] else None
            self.line(f"执行异常定位: {location['stage']} {location['task_id'] or '-'} {frame or '-'}")
        if not self.progress or result['status'] != 'completed' or result.get('task_errors'):
            suffix = (f" ({result['error_type']})" if result['status'] == 'error' else
                      f" ({result['reason_code']}; 0/{result['planned_pairs']})" if result['status'] == 'unsupported' else '')
            if result.get('task_errors'):
                suffix += f" (task_errors={result['task_errors']})"
            self.line(f"[{index+1}/{len(self.jobs)}] {job['attack']}/{job['suite']} {result['status']}{suffix}")

    def __exit__(self, exc_type, exc, tb):
        for bar in self.bars.values():
            bar.__exit__(exc_type or RuntimeError, exc, tb)
        if self.rich is not None: self.rich.stop()
