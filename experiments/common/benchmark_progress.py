"""Optional display for native benchmark task execution.

The adapter calls AgentDojo's single-task functions in the same order as its
suite functions, so each completed task (including a cache hit) can advance
the display without changing the native task loop or scorer.
"""
from __future__ import annotations

from math import ceil
import sys
from time import monotonic
import warnings

from agentdojo import benchmark


def run_suite_with_progress(pipeline, suite, attack, logdir, force_rerun, *,
                            user_tasks, injection_tasks, benchmark_version, on_step):
    """Run one suite using native single-task functions and report completions."""
    users = [suite.get_user_task_by_id(task_id) for task_id in user_tasks]
    def completed(stage, task_id, native, progress_phase):
        try:
            result = native()
            on_step(progress_phase)
            return result
        except Exception as exc:
            try:
                exc._dscg_execution_stage = stage
                exc._dscg_task_id = task_id
            except (AttributeError, TypeError):
                pass
            raise

    if attack is None:
        utility_results, security_results = {}, {}
        for user in users:
            utility, security = completed('clean_task', user.ID,
                lambda: benchmark.run_task_without_injection_tasks(
                    suite, pipeline, user, logdir, force_rerun, benchmark_version), 'score')
            utility_results[(user.ID, "")] = utility
            security_results[(user.ID, "")] = security
        return {"utility_results": utility_results, "security_results": security_results,
                "injection_tasks_utility_results": {}}

    target_tasks = (suite.injection_tasks if injection_tasks is None else {
        task_id: suite.get_injection_task_by_id(task_id) for task_id in injection_tasks})
    # Native DoS always runs the first registered target once per user.
    targets = ([next(iter(suite.injection_tasks))] if attack.is_dos_attack
               else list(target_tasks))
    goal_results = {}
    if not attack.is_dos_attack:
        for task_id, task in target_tasks.items():
            goal_results[task_id], _ = completed('goal_preflight', task_id,
                lambda: benchmark.run_task_without_injection_tasks(
                    suite, pipeline, task, logdir, force_rerun, benchmark_version), 'goal')
        if not all(goal_results.values()):
            warnings.warn("Not all injection tasks were solved as user tasks.")

    utility_results, security_results = {}, {}
    for user in users:
        for task_id in targets:
            utility, security = completed('scored_task', f'{user.ID}/{task_id}',
                lambda: benchmark.run_task_with_injection_tasks(
                    suite, pipeline, user, attack, logdir, force_rerun, [task_id], benchmark_version), 'score')
            utility_results.update(utility)
            security_results.update(security)
    return {"utility_results": utility_results, "security_results": security_results,
            "injection_tasks_utility_results": goal_results}


class GroupProgress:
    """One attack/suite bar; redirected output uses bounded plain milestones."""

    def __init__(self, label, *, goal_total, score_total, stream=None, is_tty=None):
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
        if self.is_tty:
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
        if self._progress is not None:
            self._progress.update(self._task_id, description=self._description(status),
                                  completed=self.goal_done + self.score_done)
            self._progress.stop()
        else:
            self._line(status)
        return False
