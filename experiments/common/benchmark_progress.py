"""Optional display for native benchmark task execution.

The adapter calls AgentDojo's single-task functions in the same order as its
suite functions, so each completed task (including a cache hit) can advance
the display without changing the native task loop or scorer.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from math import ceil
import sys
from time import monotonic

from experiments.common.benchmark_tasks import run_native_suite as run_suite_with_progress


_EVENT_SINK = ContextVar('benchmark_progress_events', default=None)


@contextmanager
def progress_events(send):
    token = _EVENT_SINK.set(send)
    try:
        yield
    finally:
        _EVENT_SINK.reset(token)



class GroupProgress:
    """One attack/suite bar; redirected output uses bounded plain milestones."""

    def __init__(self, label, *, goal_total, score_total, stream=None, is_tty=None, shared_progress=None):
        self.send = _EVENT_SINK.get()
        self.shared_progress = shared_progress
        self.label = label
        self.goal_total = goal_total
        self.score_total = score_total
        self.goal_done = 0
        self.score_done = 0
        self.stream = stream if stream is not None else sys.stdout
        self.is_tty = self.stream.isatty() if is_tty is None else is_tty
        self.total = goal_total + score_total
        self.started = None
        self._progress = None
        self._task_id = None
        self._last_milestone = -1
        self._stride = max(1, ceil(max(1, self.total) / 20))

    def _description(self, status="running"):
        parts = [self.label]
        if self.goal_total:
            parts.append(f"GOAL {self.goal_done}/{self.goal_total}")
        parts.append(f"任务 {self.score_done}/{self.score_total}")
        if status != "running":
            parts.append(status)
        return " | ".join(parts)

    def _line(self, status="running"):
        elapsed = monotonic() - self.started
        self.stream.write(f"{self._description(status)} | {elapsed:.0f}s\n")
        self.stream.flush()

    def __enter__(self):
        self.started = monotonic()
        if self.send is not None:
            self.send({'kind': 'progress_start', 'label': self.label,
                       'goal_total': self.goal_total, 'score_total': self.score_total})
            return self
        if self.shared_progress is not None:
            self._progress = self.shared_progress
            self._task_id = self._progress.add_task(self._description(), total=max(1, self.total))
        elif self.is_tty:
            from rich.console import Console
            from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn
            self._progress = Progress(TextColumn("{task.description}"), BarColumn(),
                                      TaskProgressColumn(), TimeElapsedColumn(),
                                      console=Console(file=self.stream), transient=False)
            self._progress.start()
            self._task_id = self._progress.add_task(self._description(), total=max(1, self.total))
        else:
            self._line()
        return self

    def advance(self, phase):
        if phase == "goal":
            self.goal_done += 1
            if self.goal_done > self.goal_total:
                raise ValueError("GOAL progress exceeded planned tasks")
        elif phase == "score":
            self.score_done += 1
            if self.score_done > self.score_total:
                raise ValueError("scored progress exceeded planned tasks")
        else:
            raise ValueError(f"unknown benchmark progress phase: {phase}")
        if self.send is not None:
            self.send({'kind': 'progress_step', 'label': self.label, 'phase': phase})
            return
        completed = self.goal_done + self.score_done
        if self._progress is not None:
            self._progress.update(self._task_id, completed=completed,
                                  description=self._description())
        else:
            milestone = completed // self._stride
            phase_finished = phase == "goal" and self.goal_done == self.goal_total
            if milestone > self._last_milestone or phase_finished or completed == self.total:
                self._last_milestone = milestone
                self._line()

    def __exit__(self, exc_type, _exc, _tb):
        status = "interrupted" if exc_type is KeyboardInterrupt else "error" if exc_type else "completed"
        if self.send is not None:
            self.send({'kind': 'progress_end', 'label': self.label, 'status': status})
            return False
        if self._progress is not None:
            self._progress.update(self._task_id, description=self._description(status),
                                  completed=self.goal_done + self.score_done)
            self._progress.stop_task(self._task_id)
            if self.shared_progress is None:
                self._progress.stop()
        else:
            self._line(status)
        return False
