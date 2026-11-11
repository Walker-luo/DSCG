"""Bounded execution-error locations without prompts, responses or exception text."""
from pathlib import Path
import re
import traceback

_ROOT = Path(__file__).resolve().parents[2]
_IDENTIFIER = re.compile(r"[A-Za-z0-9_./:-]{1,128}\Z")


def _module_name(filename: str) -> str:
    path = Path(filename)
    try:
        return path.resolve().relative_to(_ROOT).as_posix()
    except ValueError:
        parts = path.parts
        if 'site-packages' in parts:
            return '/'.join(parts[parts.index('site-packages') + 1:])
        return path.name


def execution_error_diagnostics(exc: BaseException) -> dict:
    """Describe where an exception arose without serializing its value or locals."""
    frames = traceback.extract_tb(exc.__traceback__)[-8:]
    stage = getattr(exc, '_dscg_execution_stage', None)
    task_id = getattr(exc, '_dscg_task_id', None)
    return {
        'stage': stage if stage in {'goal_preflight', 'scored_task', 'clean_task', 'attack_compatibility'} else 'group',
        'task_id': task_id if isinstance(task_id, str) and _IDENTIFIER.fullmatch(task_id) else None,
        'frames': [
            {'module': _module_name(frame.filename), 'function': frame.name,
             'line': frame.lineno}
            for frame in frames
        ],
    }
